"""パイプライン例外定義。"""
from __future__ import annotations


class PipelineError(Exception):
    """パイプライン内の一般エラー基底クラス。"""


class StageError(PipelineError):
    """ステージ実行の失敗。リトライガードの対象。"""


class PermissionViolation(PipelineError):
    """L3 パーミッション違反。リトライせず即停止。"""


class BudgetExceededError(PipelineError):
    """L1 予算上限(¥2,000/案件)超過。即停止。"""


class EscalationError(PipelineError):
    """L6 エスカレーション事由。停止して人間へ通知する。

    reason には LOOP.md §7 の事由を示す短いコードを入れる:
    duration_overflow / mosaic_detected / audio_quality / ng_conflict /
    budget_exceeded / retry_exhausted
    """

    def __init__(self, reason: str, message: str, details: dict | None = None):
        super().__init__(message)
        self.reason = reason
        self.details = details or {}


class ApprovalPendingError(PipelineError):
    """S5 人間ゲート待ち。エラーではなく正常な待機状態(exit code 2)。"""

    def __init__(self, pending: list[str], message: str):
        super().__init__(message)
        self.pending = pending
