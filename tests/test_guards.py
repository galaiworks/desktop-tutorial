"""L1 三重ガードのテスト。"""
import pytest

from pipeline import config
from pipeline.errors import BudgetExceededError, EscalationError, StageError
from pipeline.guards import check_convergence, cutlist_similarity, with_retry
from pipeline.state import State


def make_state(tmp_path):
    return State.load(tmp_path)


def cl(*segments):
    return {"segments": [{"start": s, "end": e} for s, e in segments]}


class TestRetry:
    def test_success_first_try(self, tmp_path):
        state = make_state(tmp_path)
        calls = []
        with_retry(state, "S2", lambda: calls.append(1))
        assert len(calls) == 1
        assert state.data["last_error"] is None

    def test_retries_then_succeeds(self, tmp_path):
        state = make_state(tmp_path)
        attempts = []

        def flaky():
            attempts.append(1)
            if len(attempts) < 3:
                raise StageError("一時的な失敗")

        with_retry(state, "S2", flaky)
        assert len(attempts) == 3

    def test_escalates_after_max_retries(self, tmp_path):
        state = make_state(tmp_path)

        def always_fail():
            raise StageError("恒常的な失敗")

        with pytest.raises(EscalationError) as exc:
            with_retry(state, "S3", always_fail)
        assert exc.value.reason == "retry_exhausted"
        assert state.data["last_error"]["retry_count"] == config.MAX_RETRIES

    def test_budget_error_not_retried(self, tmp_path):
        state = make_state(tmp_path)
        attempts = []

        def budget_fail():
            attempts.append(1)
            raise BudgetExceededError("予算超過")

        with pytest.raises(BudgetExceededError):
            with_retry(state, "S2", budget_fail)
        assert len(attempts) == 1  # 即停止、リトライしない

    def test_escalation_not_retried(self, tmp_path):
        state = make_state(tmp_path)
        attempts = []

        def escalate():
            attempts.append(1)
            raise EscalationError("mosaic_detected", "モザイク候補")

        with pytest.raises(EscalationError):
            with_retry(state, "S1", escalate)
        assert len(attempts) == 1


class TestConvergence:
    def test_similarity_identical(self):
        a = cl((0, 10), (20, 30))
        assert cutlist_similarity(a, a) == 1.0

    def test_similarity_disjoint(self):
        assert cutlist_similarity(cl((0, 10)), cl((50, 60))) == 0.0

    def test_similarity_none(self):
        assert cutlist_similarity(None, cl((0, 10))) == 0.0

    def test_converges_after_two_similar_regenerations(self, tmp_path):
        state = make_state(tmp_path)
        base = cl(*[(i * 10, i * 10 + 8) for i in range(20)])
        assert check_convergence(state, base) is False          # 初回(prev なし)
        assert check_convergence(state, base) is False          # 1回目の95%同一
        assert check_convergence(state, base) is True           # 2回目 → 収束

    def test_different_cutlist_resets_streak(self, tmp_path):
        state = make_state(tmp_path)
        a = cl(*[(i * 10, i * 10 + 8) for i in range(20)])
        b = cl(*[(i * 10 + 500, i * 10 + 508) for i in range(20)])
        check_convergence(state, a)
        check_convergence(state, a)                              # streak = 1
        assert check_convergence(state, b) is False              # リセット
        assert state.data["convergence"]["streak"] == 0
