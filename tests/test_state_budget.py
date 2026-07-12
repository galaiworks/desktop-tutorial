"""L4 state.json と L1 予算ガードのテスト。"""
import json

import pytest

from pipeline.budget import Budget, token_cost_jpy
from pipeline.errors import BudgetExceededError
from pipeline.state import State


class TestState:
    def test_fresh_state(self, tmp_path):
        state = State.load(tmp_path)
        assert state.data["current_stage"] == "S1"
        assert state.data["completed_stages"] == []
        assert state.data["cost_total_jpy"] == 0.0

    def test_resume_from_disk(self, tmp_path):
        """セッションはまっさらで再起動し、state.json から続行する(L4)。"""
        s1 = State.load(tmp_path)
        s1.mark_completed("S1", "S2")
        s1.set_artifact("cutlist", "work/cutlist.json")
        s1.add_cost(123.4)
        s1.record_error("S2", "テスト失敗", 2)

        s2 = State.load(tmp_path)  # まっさらなセッションを想定した再読込
        assert s2.is_completed("S1")
        assert s2.data["current_stage"] == "S2"
        assert s2.data["artifacts"]["cutlist"] == "work/cutlist.json"
        assert s2.data["cost_total_jpy"] == 123.4
        assert s2.data["last_error"]["retry_count"] == 2

    def test_atomic_save_is_valid_json(self, tmp_path):
        state = State.load(tmp_path)
        state.save()
        data = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
        assert "current_stage" in data

    def test_mark_completed_idempotent(self, tmp_path):
        state = State.load(tmp_path)
        state.mark_completed("S1", "S2")
        state.mark_completed("S1", "S2")
        assert state.data["completed_stages"].count("S1") == 1


class TestBudget:
    def test_token_cost_conversion(self):
        # sonnet-5: $3/M 入力 + $15/M 出力、換算レートは config.USD_JPY
        from pipeline import config
        jpy = token_cost_jpy("claude-sonnet-5", 1_000_000, 0)
        assert jpy == pytest.approx(3.0 * config.USD_JPY)

    def test_unknown_model_uses_max_price(self):
        from pipeline import config
        jpy = token_cost_jpy("unknown-model", 1_000_000, 0)
        assert jpy == pytest.approx(5.0 * config.USD_JPY)  # opus 単価で保守的に見積る

    def test_budget_exceeded_stops_immediately(self, tmp_path):
        state = State.load(tmp_path)
        budget = Budget(state, limit_jpy=2000.0)
        budget.charge(1999.0)  # 上限内
        with pytest.raises(BudgetExceededError):
            budget.charge(2.0)  # 超過で即停止
        # 超過分もコストとして記録されている(実際に消費したため)
        assert state.data["cost_total_jpy"] == pytest.approx(2001.0)
