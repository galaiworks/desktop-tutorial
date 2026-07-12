"""S5: 人間ゲート(自律度 L1.5 — LOOP.md §自律度)。

3ゲートすべて人間必須:
  1. プレビュー承認   `--approve preview`
  2. モザイク承認     `--approve mosaic`(候補がある場合のみ。恒久的に人間ゲート、昇格対象外)
  3. サムネ選択       `--select-thumbnail <1-3>`

未承認のゲートがあれば通知して停止する(exit code 2 の待機状態)。
"""
from __future__ import annotations

from ..context import JobContext
from ..errors import ApprovalPendingError
from ..notify import notify


def run(ctx: JobContext) -> None:
    approvals = ctx.state.data["approvals"]
    mosaic_candidates = ctx.state.data.get("mosaic", {}).get("candidates", [])

    pending: list[str] = []
    if not approvals.get("preview"):
        pending.append(
            f"プレビュー承認: {ctx.job_dir / 'work' / 'final_draft.mp4'} を確認し "
            f"`--approve preview` を実行"
        )
    if mosaic_candidates and not approvals.get("mosaic"):
        pending.append(
            f"モザイク承認: 候補{len(mosaic_candidates)}件"
            f"(logs/mosaic_candidates.json)を確認し `--approve mosaic` を実行"
        )
    if not approvals.get("thumbnail"):
        pending.append(
            f"サムネ選択: {ctx.preview_dir} の候補3枚から "
            f"`--select-thumbnail <1-3>` で選択"
        )

    if pending:
        ctx.state.data["status"] = "pending_approval"
        ctx.state.save()
        body = "\n".join(f"- {p}" for p in pending)
        notify(
            f"[{ctx.job_id}] S5 承認待ち",
            f"以下のゲートの人間承認が必要です:\n{body}\n"
            f"承認後、再度 `python pipeline/run.py jobs/{ctx.job_id}` を実行してください。",
        )
        raise ApprovalPendingError(pending, "S5 人間ゲート待ちです")
