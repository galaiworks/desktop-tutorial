"""L2 Maker-Checker の LLM 呼び出し層。

- Maker: editor / telop_writer / music_selector(Sonnet系)
- Checker: checker(Opus系、Maker とは別エージェント)
- 各エージェントのシステムプロンプトは agents/<name>.md から読み込む
- 応答は structured outputs(JSON Schema)で受け取り、コストを予算ガードに計上する
"""
from __future__ import annotations

import json
from pathlib import Path

import anthropic

from . import config
from .budget import Budget, token_cost_jpy
from .errors import StageError

AGENTS_DIR = Path(__file__).resolve().parent.parent / "agents"

MAKER_AGENTS = {"editor", "telop_writer", "music_selector"}
CHECKER_AGENTS = {"checker"}


class LLMClient:
    def __init__(self, budget: Budget):
        self.budget = budget
        self._client = anthropic.Anthropic()

    @staticmethod
    def _model_for(agent: str) -> str:
        if agent in CHECKER_AGENTS:
            return config.CHECKER_MODEL
        if agent in MAKER_AGENTS:
            return config.MAKER_MODEL
        raise StageError(f"未定義のエージェントです: {agent}")

    @staticmethod
    def _system_prompt(agent: str) -> str:
        path = AGENTS_DIR / f"{agent}.md"
        if not path.exists():
            raise StageError(f"エージェント定義がありません: {path}")
        return path.read_text(encoding="utf-8")

    def call(self, agent: str, user_content: str, schema: dict) -> dict:
        """エージェントを1回呼び出し、スキーマ準拠のJSONを返す。コストは即時計上。"""
        model = self._model_for(agent)
        try:
            response = self._client.messages.create(
                model=model,
                max_tokens=config.MAX_TOKENS,
                thinking={"type": "adaptive"},
                system=self._system_prompt(agent),
                messages=[{"role": "user", "content": user_content}],
                output_config={"format": {"type": "json_schema", "schema": schema}},
            )
        except anthropic.APIConnectionError as e:
            raise StageError(f"APIへの接続に失敗しました({agent}): {e}") from e
        except anthropic.APIStatusError as e:
            raise StageError(f"API呼び出しに失敗しました({agent}, {e.status_code}): {e.message}") from e

        # コスト計上(予算超過なら BudgetExceededError で即停止)
        usage = response.usage
        cached = getattr(usage, "cache_read_input_tokens", 0) or 0
        created = getattr(usage, "cache_creation_input_tokens", 0) or 0
        jpy = token_cost_jpy(model, usage.input_tokens + cached + created, usage.output_tokens)
        self.budget.charge(jpy)

        if response.stop_reason == "refusal":
            raise StageError(f"エージェント {agent} が応答を拒否しました")
        if response.stop_reason == "max_tokens":
            raise StageError(f"エージェント {agent} の出力がトークン上限で途切れました")

        text = next((b.text for b in response.content if b.type == "text"), None)
        if text is None:
            raise StageError(f"エージェント {agent} からテキスト応答が得られませんでした")
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            raise StageError(f"エージェント {agent} の応答がJSONとして不正です: {e}") from e
