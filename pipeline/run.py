"""動画編集パイプライン Caesura-Coconala Edition — オーケストレーター。

使い方(LOOP.md §2: 手動トリガーのみ。cron/自動起動は行わない):
    python pipeline/run.py jobs/<job_id>                 # 実行 / state.json から再開
    python pipeline/run.py jobs/<job_id> --status        # 進捗確認
    python pipeline/run.py jobs/<job_id> --approve preview
    python pipeline/run.py jobs/<job_id> --approve mosaic
    python pipeline/run.py jobs/<job_id> --select-thumbnail 2
    python pipeline/run.py --check-env                   # 実行環境の確認

終了コード: 0=完了/正常終了  1=停止(エスカレーション等)  2=S5承認待ち
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

# `python pipeline/run.py` での直接実行を可能にする
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import config  # noqa: E402
from pipeline.context import JobContext  # noqa: E402
from pipeline.errors import (  # noqa: E402
    ApprovalPendingError,
    BudgetExceededError,
    EscalationError,
    PermissionViolation,
    PipelineError,
)
from pipeline.guards import with_retry  # noqa: E402
from pipeline.notify import notify  # noqa: E402
from pipeline.stages import s1_ingest, s2_cut, s3_telop, s4_audio, s5_gates, s6_qa  # noqa: E402

STAGES = [
    ("S1", "素材取り込み・文字起こし", s1_ingest.run),
    ("S2", "カット編集", s2_cut.run),
    ("S3", "テロップ生成", s3_telop.run),
    ("S4", "BGM・ミックス・正規化", s4_audio.run),
    ("S5", "人間ゲート(プレビュー/モザイク/サムネ)", s5_gates.run),
    ("S6", "QA・納品パッケージ", s6_qa.run),
]


def check_env() -> int:
    """実行環境(外部ツール・APIキー)を確認する。"""
    ok = True
    for tool in sorted(config.ALLOWED_TOOLS):
        path = shutil.which(tool)
        print(f"  {tool:12s} {'OK: ' + path if path else 'NG: 未インストール'}")
        ok = ok and bool(path)
    has_key = bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))
    print(f"  {'APIキー':12s} {'OK' if has_key else 'NG: ANTHROPIC_API_KEY が未設定'}")
    slack = bool(os.environ.get(config.SLACK_WEBHOOK_ENV))
    print(f"  {'Slack通知':12s} {'OK' if slack else '未設定(ローカル通知のみ)'}")
    return 0 if (ok and has_key) else 1


def show_status(ctx: JobContext) -> int:
    d = ctx.state.data
    print(json.dumps({
        "job_id": ctx.job_id,
        "status": d["status"],
        "current_stage": d["current_stage"],
        "completed_stages": d["completed_stages"],
        "artifacts": d["artifacts"],
        "cost_total_jpy": d["cost_total_jpy"],
        "budget_jpy": config.BUDGET_JPY,
        "approvals": d["approvals"],
        "last_error": d["last_error"],
    }, ensure_ascii=False, indent=2))
    return 0


def apply_approval(ctx: JobContext, gate: str) -> int:
    """S5 人間ゲートの承認を記録する(人間による手動実行が前提)。"""
    ctx.state.data["approvals"][gate] = True
    ctx.state.save()
    print(f"[{ctx.job_id}] {gate} を承認しました。再実行で続行します。")
    return 0


def select_thumbnail(ctx: JobContext, index: int) -> int:
    if index not in (1, 2, 3):
        print("サムネイル番号は 1〜3 で指定してください", file=sys.stderr)
        return 1
    ctx.state.data["approvals"]["thumbnail"] = index
    ctx.state.save()
    print(f"[{ctx.job_id}] サムネイル {index} を選択しました。再実行で続行します。")
    return 0


def run_pipeline(ctx: JobContext) -> int:
    """S1→S6 を state.json から続行実行する(タスク内ループ本体)。"""
    print(f"[{ctx.job_id}] 開始(累計コスト ¥{ctx.state.data['cost_total_jpy']:.0f} / "
          f"上限 ¥{config.BUDGET_JPY:.0f})")
    ctx.state.data["status"] = "running"
    ctx.state.save()

    try:
        for i, (stage, label, fn) in enumerate(STAGES):
            if ctx.state.is_completed(stage):
                continue
            print(f"\n--- {stage}: {label} ---")
            next_stage = STAGES[i + 1][0] if i + 1 < len(STAGES) else None
            with_retry(ctx.state, stage, lambda f=fn: f(ctx))
            ctx.state.mark_completed(stage, next_stage)

        ctx.state.data["status"] = "done"
        ctx.state.save()
        print(f"\n[{ctx.job_id}] 完了。納品パッケージ: {ctx.output_dir}"
              f"(累計コスト ¥{ctx.state.data['cost_total_jpy']:.0f})")
        return 0

    except ApprovalPendingError as e:
        # S5 待機は正常状態(通知は s5_gates 内で送信済み)
        print(f"\n[{ctx.job_id}] {e}", file=sys.stderr)
        return 2
    except BudgetExceededError as e:
        ctx.state.data["status"] = "stopped"
        ctx.state.save()
        notify(f"[{ctx.job_id}] 予算上限で停止", str(e))
        return 1
    except EscalationError as e:
        ctx.state.data["status"] = "stopped"
        ctx.state.save()
        notify(f"[{ctx.job_id}] エスカレーション({e.reason})", str(e))
        return 1
    except PermissionViolation as e:
        ctx.state.data["status"] = "stopped"
        ctx.state.save()
        notify(f"[{ctx.job_id}] パーミッション違反で停止", str(e))
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="動画編集パイプライン(LOOP.md 準拠)")
    parser.add_argument("job_dir", nargs="?", help="jobs/<job_id> のパス")
    parser.add_argument("--status", action="store_true", help="進捗を表示")
    parser.add_argument("--approve", choices=["preview", "mosaic"], help="S5ゲートを承認")
    parser.add_argument("--select-thumbnail", type=int, metavar="N", help="サムネイル選択(1-3)")
    parser.add_argument("--check-env", action="store_true", help="実行環境を確認")
    args = parser.parse_args(argv)

    if args.check_env:
        return check_env()
    if not args.job_dir:
        parser.error("jobs/<job_id> を指定してください")

    try:
        ctx = JobContext(Path(args.job_dir))
    except PipelineError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    if args.status:
        return show_status(ctx)
    if args.approve:
        return apply_approval(ctx, args.approve)
    if args.select_thumbnail is not None:
        return select_thumbnail(ctx, args.select_thumbnail)
    return run_pipeline(ctx)


if __name__ == "__main__":
    sys.exit(main())
