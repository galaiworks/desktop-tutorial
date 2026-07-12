"""L1 予算ガード: 1案件あたり APIコスト ¥2,000 上限。超過で即停止。"""
from __future__ import annotations

from . import config
from .errors import BudgetExceededError
from .state import State


def token_cost_jpy(model: str, input_tokens: int, output_tokens: int) -> float:
    """API使用量(トークン)を円に換算する。未知モデルは最高単価で保守的に見積る。"""
    in_usd, out_usd = config.PRICES_USD_PER_MTOK.get(
        model, max(config.PRICES_USD_PER_MTOK.values())
    )
    usd = (input_tokens / 1_000_000) * in_usd + (output_tokens / 1_000_000) * out_usd
    return usd * config.USD_JPY


class Budget:
    """state.json のコスト累計と連動する予算トラッカー。"""

    def __init__(self, state: State, limit_jpy: float = config.BUDGET_JPY):
        self.state = state
        self.limit_jpy = limit_jpy

    @property
    def total_jpy(self) -> float:
        return self.state.data["cost_total_jpy"]

    def charge(self, jpy: float) -> None:
        total = self.state.add_cost(jpy)
        if total > self.limit_jpy:
            raise BudgetExceededError(
                f"APIコストが予算上限を超過しました: ¥{total:.0f} > ¥{self.limit_jpy:.0f}"
            )
