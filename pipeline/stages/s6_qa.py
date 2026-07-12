"""S6: QAチェック・納品パッケージ生成(Goal — LOOP.md §1)。

機械検証(スクリプト実行、LLM自己申告は不採用):
  - 尺: 目標±許容内(ffprobe 実測)
  - ラウドネス: -14 LUFS ±1(ffmpeg loudnorm 実測)
  - 黒フレーム: ゼロ(blackdetect 実測)
  - 字幕はみ出し: ゼロ(スクリプト検査)

Checker 校正(Opus系、Maker と別エージェント):
  - 誤字リスト・尺検証・ラウドネス実測値・NG事項照合 → logs/checker_report.json
  - 誤字は自動適用して再検査(1サイクル)。NG事項との矛盾は即エスカレーション(L6)

すべてグリーンで output/ に納品パッケージ(final.mp4 / telop.srt / thumbnail.png /
checker_report.json / qa_report.json)を揃えて完了。
"""
from __future__ import annotations

import json
import shutil

from .. import config, media
from .. import telop as telop_utils
from ..context import JobContext
from ..errors import EscalationError, StageError

CHECKER_SCHEMA = {
    "type": "object",
    "properties": {
        "typos": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "original": {"type": "string"},
                    "corrected": {"type": "string"},
                    "note": {"type": "string"},
                },
                "required": ["original", "corrected", "note"],
                "additionalProperties": False,
            },
        },
        "ng_conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "ng_item": {"type": "string"},
                    "found_in": {"type": "string"},
                    "detail": {"type": "string"},
                },
                "required": ["ng_item", "found_in", "detail"],
                "additionalProperties": False,
            },
        },
        "verdict": {"type": "string", "enum": ["pass", "fail"]},
        "comment": {"type": "string"},
    },
    "required": ["typos", "ng_conflicts", "verdict", "comment"],
    "additionalProperties": False,
}


def _machine_checks(ctx: JobContext, video) -> dict:
    """QA機械検証4項目を実測する。"""
    target = float(ctx.job["target_duration_sec"])
    tolerance = float(ctx.job.get("duration_tolerance_sec", 15))
    telop_cfg = ctx.job.get("telop", {})
    telop = ctx.read_json("work/telop.json")

    duration = media.probe_duration(video)
    lufs = media.measure_loudness(video)
    black = media.detect_black_frames(video)
    overflow = telop_utils.check_overflow(
        telop,
        int(telop_cfg.get("max_chars_per_line", 26)),
        int(telop_cfg.get("max_lines", 2)),
    )
    return {
        "duration": {
            "measured_sec": duration,
            "target_sec": target,
            "tolerance_sec": tolerance,
            "green": abs(duration - target) <= tolerance,
        },
        "loudness": {
            "measured_lufs": lufs,
            "target_lufs": config.LOUDNESS_TARGET_LUFS,
            "tolerance_lu": config.LOUDNESS_TOLERANCE_LU,
            "green": abs(lufs - config.LOUDNESS_TARGET_LUFS) <= config.LOUDNESS_TOLERANCE_LU,
        },
        "black_frames": {"found": black, "green": len(black) == 0},
        "subtitle_overflow": {"violations": overflow, "green": len(overflow) == 0},
    }


def _run_checker(ctx: JobContext, machine: dict) -> dict:
    """Checker(Opus系)による校正。機械実測値を渡して照合させる。"""
    telop = ctx.read_json("work/telop.json")
    prompt = json.dumps({
        "task": "納品前校正",
        "ng_items": ctx.job.get("ng_items", []),
        "machine_measurements": {
            "duration_sec": machine["duration"]["measured_sec"],
            "loudness_lufs": machine["loudness"]["measured_lufs"],
        },
        "telop_entries": telop.get("entries", []),
        "note": "誤字脱字・表記ゆれを typos に、NG事項に抵触する箇所を ng_conflicts に列挙。"
                "問題がなければ verdict を pass に。",
    }, ensure_ascii=False)
    return ctx.llm.call("checker", prompt, CHECKER_SCHEMA)


def run(ctx: JobContext) -> None:
    video = ctx.artifact_path("final_draft")

    # --- 機械検証 ---
    machine = _machine_checks(ctx, video)
    failed = [k for k, v in machine.items() if not v["green"]]
    if failed:
        ctx.write_json("logs/qa_machine_failures.json", machine)
        raise StageError(f"QA機械検証で不合格: {', '.join(failed)}")

    # --- Checker 校正(Opus系) ---
    report = _run_checker(ctx, machine)

    # NG事項との矛盾は人間の判断が必要(L6)
    if report["ng_conflicts"]:
        ctx.write_json("logs/checker_report.json", {"machine": machine, "checker": report})
        lines = "\n".join(
            f"- {c['ng_item']}: {c['detail']}" for c in report["ng_conflicts"][:10]
        )
        raise EscalationError(
            "ng_conflict",
            f"job.yaml のNG事項と矛盾する内容が見つかりました:\n{lines}",
            {"ng_conflicts": report["ng_conflicts"]},
        )

    # 誤字があれば自動適用 → SRT再生成 → 焼き込み直し → 再検査(1サイクル)
    if report["typos"]:
        telop = ctx.read_json("work/telop.json")
        applied = telop_utils.apply_corrections(telop, report["typos"])
        print(f"[S6] Checker の誤字指摘 {len(report['typos'])} 件中 {applied} 件を適用しました")
        ctx.write_json("work/telop.json", telop)
        srt_path = ctx.sandbox.writable(ctx.work_dir / "telop.srt")
        srt_path.write_text(telop_utils.to_srt(telop), encoding="utf-8")
        mixed = ctx.artifact_path("mixed_video")
        final_draft = ctx.sandbox.writable(ctx.work_dir / "final_draft.mp4")
        media.burn_subtitles(mixed, srt_path, final_draft)

        machine = _machine_checks(ctx, video)
        report = _run_checker(ctx, machine)
        if report["typos"] or report["verdict"] != "pass":
            ctx.write_json("logs/checker_report.json", {"machine": machine, "checker": report})
            raise StageError(
                f"Checker 再校正が不合格です(残り誤字 {len(report['typos'])} 件): {report['comment']}"
            )

    if report["verdict"] != "pass":
        ctx.write_json("logs/checker_report.json", {"machine": machine, "checker": report})
        raise StageError(f"Checker 校正が不合格です: {report['comment']}")

    # --- 証跡 & 納品パッケージ ---
    ctx.write_json("logs/checker_report.json", {"machine": machine, "checker": report})

    out_dir = ctx.sandbox.writable(ctx.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(video, out_dir / "final.mp4")
    shutil.copy2(ctx.artifact_path("telop_srt"), out_dir / "telop.srt")
    thumb_index = int(ctx.state.data["approvals"].get("thumbnail", 1))
    thumb = ctx.sandbox.readable(ctx.preview_dir / f"thumbnail_{thumb_index}.png")
    shutil.copy2(thumb, out_dir / "thumbnail.png")
    shutil.copy2(ctx.job_dir / "logs" / "checker_report.json", out_dir / "checker_report.json")
    ctx.write_json("output/qa_report.json", {
        "machine_checks": machine,
        "checker_verdict": report["verdict"],
        "cost_total_jpy": ctx.state.data["cost_total_jpy"],
    })
    ctx.state.set_artifact("deliverables", "output")
    print(f"[S6] QA 全項目グリーン。納品パッケージ: {out_dir}")
