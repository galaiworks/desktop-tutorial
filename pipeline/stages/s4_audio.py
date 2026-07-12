"""S4: BGM選定・ミックス・-14 LUFS 正規化(Maker: music_selector / Sonnet系)。

- music_selector がローカルBGMライブラリ(assets/ 配下)から選曲 → work/mix.json
  ※ 外部サイトからのBGM/SE取得は L3 で禁止。候補はローカルの一覧のみ提示する
- ffmpeg でミックス + loudnorm(-14 LUFS)→ work/mixed.mp4
- 字幕焼き込み → work/final_draft.mp4
- ラウドネスを実測して機械検証(±1 LU)
- サムネイル候補3枚を preview/ に抽出(S5 サムネ選択ゲート用)
"""
from __future__ import annotations

import json
from pathlib import Path

from .. import config, context, media
from ..context import JobContext
from ..errors import StageError

MIX_SCHEMA = {
    "type": "object",
    "properties": {
        "bgm_file": {"type": ["string", "null"]},
        "gain_db": {"type": "number"},
        "selection_reason": {"type": "string"},
    },
    "required": ["bgm_file", "gain_db", "selection_reason"],
    "additionalProperties": False,
}

AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"}


def _bgm_library(ctx: JobContext) -> list[str]:
    lib_rel = ctx.job.get("bgm", {}).get("library_dir", "assets/bgm")
    lib_dir = ctx.sandbox.readable(context.REPO_ROOT / lib_rel)
    if not lib_dir.is_dir():
        return []
    return sorted(
        str(p.relative_to(context.REPO_ROOT))
        for p in lib_dir.iterdir()
        if p.suffix.lower() in AUDIO_EXTS
    )


def run(ctx: JobContext) -> None:
    cut_video = ctx.artifact_path("cut_video")
    library = _bgm_library(ctx)

    if library:
        prompt = json.dumps({
            "task": "BGM選定",
            "mood": ctx.job.get("bgm", {}).get("mood", "指定なし"),
            "notes": ctx.job.get("notes", ""),
            "available_bgm_files": library,
            "rule": "available_bgm_files の中からのみ選ぶこと。合わない場合は bgm_file を null に。",
        }, ensure_ascii=False)
        mix = ctx.llm.call("music_selector", prompt, MIX_SCHEMA)
        if mix["bgm_file"] is not None and mix["bgm_file"] not in library:
            raise StageError(
                f"music_selector がライブラリ外のファイルを指定しました: {mix['bgm_file']}"
            )
    else:
        mix = {"bgm_file": None, "gain_db": 0.0,
               "selection_reason": "BGMライブラリが空のため未使用"}

    ctx.write_json("work/mix.json", mix)
    ctx.state.set_artifact("mix", "work/mix.json")

    # ミックス + -14 LUFS 正規化(機械処理)
    bgm_path: Path | None = None
    if mix["bgm_file"]:
        bgm_path = ctx.sandbox.readable(context.REPO_ROOT / mix["bgm_file"])
    mixed = ctx.sandbox.writable(ctx.work_dir / "mixed.mp4")
    media.mix_bgm_and_normalize(cut_video, bgm_path, float(mix["gain_db"]), mixed)

    # 機械検証: ラウドネス実測(LLM/レンダリング結果の自己申告は採用しない)
    lufs = media.measure_loudness(mixed)
    if abs(lufs - config.LOUDNESS_TARGET_LUFS) > config.LOUDNESS_TOLERANCE_LU:
        raise StageError(
            f"ラウドネスが基準外です: 実測 {lufs:.1f} LUFS "
            f"(基準 {config.LOUDNESS_TARGET_LUFS}±{config.LOUDNESS_TOLERANCE_LU})"
        )
    ctx.state.set_artifact("mixed_video", "work/mixed.mp4")

    # 字幕焼き込み
    srt = ctx.artifact_path("telop_srt")
    final_draft = ctx.sandbox.writable(ctx.work_dir / "final_draft.mp4")
    media.burn_subtitles(mixed, srt, final_draft)
    ctx.state.set_artifact("final_draft", "work/final_draft.mp4")

    # サムネイル候補(S5ゲート用)
    preview_dir = ctx.sandbox.writable(ctx.preview_dir)
    preview_dir.mkdir(parents=True, exist_ok=True)
    thumbs = media.extract_thumbnails(final_draft, preview_dir, count=3)
    ctx.state.set_artifact("thumbnails", "preview")
    print(f"[S4] サムネイル候補: {', '.join(str(t) for t in thumbs)}")
