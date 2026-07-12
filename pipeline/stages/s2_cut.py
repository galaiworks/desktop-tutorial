"""S2: カット編集(Maker: editor / Sonnet系)。

- editor エージェントが文字起こしからカットリストを生成 → work/cutlist.json
- 機械検証: セグメント合計尺が job.yaml の目標尺±許容に収まるか(LLM自己申告は不採用)
- 収まらない場合は差分フィードバック付きで再生成。L1差分停止ガード(95%×2回で収束)適用
- リトライを使い切っても収まらなければ「目標尺に収まらない」としてエスカレーション(L6)
- editor がモザイク候補を追加検出した場合も即エスカレーション(L6)
- 確定したカットリストで ffmpeg レンダリング → work/cut.mp4
"""
from __future__ import annotations

import json

from .. import config, media
from ..context import JobContext
from ..errors import EscalationError
from ..guards import check_convergence

CUTLIST_SCHEMA = {
    "type": "object",
    "properties": {
        "segments": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["start", "end", "reason"],
                "additionalProperties": False,
            },
        },
        "mosaic_candidates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "start": {"type": "number"},
                    "end": {"type": "number"},
                    "reason": {"type": "string"},
                },
                "required": ["start", "end", "reason"],
                "additionalProperties": False,
            },
        },
        "editorial_note": {"type": "string"},
    },
    "required": ["segments", "mosaic_candidates", "editorial_note"],
    "additionalProperties": False,
}


def _total_duration(cutlist: dict) -> float:
    return sum(float(s["end"]) - float(s["start"]) for s in cutlist.get("segments", []))


def run(ctx: JobContext) -> None:
    transcript = ctx.read_json("work/transcript.json")
    source_info = ctx.read_json("work/source_info.json")
    target = float(ctx.job["target_duration_sec"])
    tolerance = float(ctx.job.get("duration_tolerance_sec", 15))

    feedback = ""
    cutlist: dict | None = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        prompt = json.dumps({
            "task": "カットリスト生成",
            "target_duration_sec": target,
            "tolerance_sec": tolerance,
            "source_duration_sec": source_info["duration_sec"],
            "ng_items": ctx.job.get("ng_items", []),
            "editorial_policy": ctx.job.get("editorial_policy", ""),
            "feedback": feedback,
            "transcript_segments": transcript.get("segments", []),
        }, ensure_ascii=False)
        cutlist = ctx.llm.call("editor", prompt, CUTLIST_SCHEMA)

        # editor 検出のモザイク候補は即エスカレーション(承認済みなら通過)
        mosaic = cutlist.get("mosaic_candidates", [])
        if mosaic and not ctx.state.data["approvals"].get("mosaic"):
            ctx.write_json("logs/mosaic_candidates_editor.json", mosaic)
            raise EscalationError(
                "mosaic_detected",
                f"editor がモザイク候補を検出しました({len(mosaic)}件)。"
                "logs/mosaic_candidates_editor.json を確認し `--approve mosaic` で続行してください。",
                {"candidates": mosaic},
            )

        # 機械検証: 合計尺(LLMの自己申告は採用しない)
        total = _total_duration(cutlist)
        if abs(total - target) <= tolerance:
            break

        # 差分停止ガード: 95%以上同一の再生成が2回続いたら収束とみなし先に進む
        if check_convergence(ctx.state, cutlist):
            print(f"[S2] カットリストが収束しました(合計 {total:.1f}s)。先に進みます。")
            break

        feedback = (
            f"前回のカットリストは合計 {total:.1f} 秒で、目標 {target:.0f}±{tolerance:.0f} 秒に"
            f"収まっていません。{'短く' if total > target else '長く'}調整してください。"
        )
        if attempt == config.MAX_RETRIES:
            raise EscalationError(
                "duration_overflow",
                f"目標尺にカットで収まりません(最終 {total:.1f}s / 目標 {target:.0f}±{tolerance:.0f}s)。"
                "素材の情報密度が高すぎる可能性があります。",
                {"total_sec": total, "target_sec": target, "tolerance_sec": tolerance},
            )

    ctx.write_json("work/cutlist.json", cutlist)
    ctx.state.set_artifact("cutlist", "work/cutlist.json")

    # レンダリング(機械処理)
    out = ctx.sandbox.writable(ctx.work_dir / "cut.mp4")
    media.render_cutlist(ctx.source_path(), cutlist, out)
    ctx.state.set_artifact("cut_video", "work/cut.mp4")
