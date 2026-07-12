"""S1: 素材取り込み・文字起こし・機械検品。

- 素材(assets/ 配下)を ffprobe で検品(尺・音声品質)
- whisper で文字起こし → work/transcript.json
- 音声品質が閾値以下なら即エスカレーション(L6)
- 文字起こしからモザイク候補(PII言及)を機械抽出し、検出時点で即エスカレーション(L6)
"""
from __future__ import annotations

from .. import config, media
from ..context import JobContext
from ..errors import EscalationError


def run(ctx: JobContext) -> None:
    source = ctx.source_path()

    # 機械検品: 尺と音声品質
    duration = media.probe_duration(source)
    mean_volume = media.measure_mean_volume(source)
    if mean_volume < config.MIN_MEAN_VOLUME_DB:
        raise EscalationError(
            "audio_quality",
            f"素材の音声品質が閾値以下です(平均音量 {mean_volume:.1f} dB)。"
            "自動補正の範囲を超えるため人間の判断が必要です。",
            {"mean_volume_db": mean_volume, "threshold_db": config.MIN_MEAN_VOLUME_DB},
        )

    # 文字起こし(再実行時は既存の transcript を再利用し whisper を省略)
    transcript_path = ctx.work_dir / "transcript.json"
    if transcript_path.exists():
        transcript = ctx.read_json("work/transcript.json")
    else:
        transcript_dir = ctx.sandbox.writable(ctx.work_dir / "whisper")
        transcript = media.transcribe(source, transcript_dir)
        ctx.write_json("work/transcript.json", transcript)
    ctx.state.set_artifact("transcript", "work/transcript.json")

    # 素材情報を記録
    ctx.write_json("work/source_info.json", {
        "source": str(source),
        "duration_sec": duration,
        "mean_volume_db": mean_volume,
    })
    ctx.state.set_artifact("source_info", "work/source_info.json")

    # モザイク候補の機械検出(検出時点で即リスト提示 — L6)
    # ※ 人間が `--approve mosaic` 済みなら通過する(承認自体は恒久的に人間ゲート)
    candidates = media.scan_mosaic_candidates(transcript)
    if candidates and not ctx.state.data["approvals"].get("mosaic"):
        ctx.write_json("logs/mosaic_candidates.json", candidates)
        ctx.state.data.setdefault("mosaic", {})["candidates"] = candidates
        ctx.state.save()
        lines = "\n".join(
            f"- {c['start']:.1f}s〜{c['end']:.1f}s: {c['reason']} 「{c['text'][:40]}」"
            for c in candidates[:10]
        )
        raise EscalationError(
            "mosaic_detected",
            f"モザイク候補を検出しました({len(candidates)}件)。承認が必要です:\n{lines}\n"
            f"確認後 `--approve mosaic` で続行してください。",
            {"candidates": candidates},
        )
