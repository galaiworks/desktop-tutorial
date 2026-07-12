"""S3: テロップ生成(Maker: telop_writer / Sonnet系)。

- telop_writer がカット後の時間軸に沿ったテロップを生成 → work/telop.json
- 機械検証: 字幕はみ出し(文字数/行数)・時刻整合をスクリプトで検査
- 違反があればフィードバック付きで再生成(リトライは with_retry が管理)
- SRT を生成 → work/telop.srt
"""
from __future__ import annotations

import json

from .. import telop as telop_utils
from ..context import JobContext
from ..errors import StageError

TELOP_SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "text": {"type": "string"},
                },
                "required": ["start", "end", "text"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["entries"],
    "additionalProperties": False,
}


def run(ctx: JobContext) -> None:
    transcript = ctx.read_json("work/transcript.json")
    cutlist = ctx.read_json("work/cutlist.json")
    telop_cfg = ctx.job.get("telop", {})
    max_chars = int(telop_cfg.get("max_chars_per_line", 26))
    max_lines = int(telop_cfg.get("max_lines", 2))

    prompt = json.dumps({
        "task": "テロップ生成",
        "constraints": {
            "max_chars_per_line": max_chars,
            "max_lines": max_lines,
            "note": "時刻はカット後の動画の時間軸(秒)。前のテロップと重複しないこと。",
        },
        "ng_items": ctx.job.get("ng_items", []),
        "cutlist": cutlist.get("segments", []),
        "transcript_segments": transcript.get("segments", []),
    }, ensure_ascii=False)

    telop = ctx.llm.call("telop_writer", prompt, TELOP_SCHEMA)

    # 機械検証: はみ出し・時刻整合(LLMの自己申告は採用しない)
    violations = (
        telop_utils.check_overflow(telop, max_chars, max_lines)
        + telop_utils.check_timing(telop)
    )
    if violations:
        ctx.write_json("logs/telop_violations.json", violations)
        raise StageError(
            f"テロップ検査で {len(violations)} 件の違反があります"
            f"(例: {violations[0]['problem']})。再生成します。"
        )

    ctx.write_json("work/telop.json", telop)
    ctx.state.set_artifact("telop", "work/telop.json")

    srt_path = ctx.sandbox.writable(ctx.work_dir / "telop.srt")
    srt_path.write_text(telop_utils.to_srt(telop), encoding="utf-8")
    ctx.state.set_artifact("telop_srt", "work/telop.srt")
