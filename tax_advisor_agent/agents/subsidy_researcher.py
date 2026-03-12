"""
補助金・助成金リサーチャーエージェント

Web検索・Web取得ツールを使って最新の補助金・助成金情報をリサーチする。
claude-opus-4-6 の web_search_20260209 / web_fetch_20260209 サーバーサイドツールを活用。
"""
import json
import anthropic
from ..config import MODEL
from ..models import BusinessProfile, SubsidyInfo, AgentResponse

SYSTEM_PROMPT = """あなたは中小企業・個人事業主向けの補助金・助成金専門リサーチャーエージェントです。
Web検索とWebページ取得ツールを使って、最新の補助金・助成金情報を収集・整理します。

## リサーチ対象
1. **国の補助金・助成金**
   - 経済産業省・中小企業庁関連（IT導入補助金、ものづくり補助金、持続化補助金など）
   - 厚生労働省関連（雇用調整助成金、キャリアアップ助成金など）
   - 農林水産省関連（農業・食品業向け）

2. **地方自治体の補助金**
   - 都道府県・市区町村の独自補助金
   - 地域の特性に応じた支援制度

3. **民間・団体の助成金**
   - 商工会議所・商工会の支援
   - 業界団体の助成制度

## リサーチ手順
1. 対象業種・規模に合った補助金をWeb検索
2. 各補助金の公式ページを確認して詳細情報を取得
3. 申請期限・金額・対象条件を正確に整理
4. 新規募集開始・締切直前のものを優先的に報告

## 出力形式
JSON形式で補助金情報を構造化して返す:
```json
{
  "subsidies": [
    {
      "name": "補助金名",
      "organization": "実施機関",
      "description": "概要（100字程度）",
      "amount": "金額・補助率",
      "target": "対象者・条件",
      "deadline": "申請期限（不明な場合は「要確認」）",
      "url": "公式URL",
      "business_types": ["対象業種"],
      "status": "募集中|準備中|終了",
      "urgency": "high|medium|low"
    }
  ],
  "summary": "今回のリサーチサマリー（日本語）",
  "search_date": "検索日時"
}
```

**重要**: 情報の正確性を最優先とし、不確かな情報は「要確認」と明示してください。"""


class SubsidyResearcherAgent:
    """補助金・助成金リサーチャー"""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.name = "補助金リサーチャー"

        # サーバーサイドツール (web_search + web_fetch with dynamic filtering)
        self.tools = [
            {"type": "web_search_20260209", "name": "web_search"},
            {"type": "web_fetch_20260209", "name": "web_fetch"},
        ]

    def research(
        self,
        profile: BusinessProfile,
        focus_keywords: list[str] | None = None,
    ) -> AgentResponse:
        """業種に合った補助金・助成金をリサーチする"""
        keywords = focus_keywords or []
        query = self._build_research_query(profile, keywords)

        messages = [{"role": "user", "content": query}]

        try:
            content_text = ""
            stop_reason = "end_turn"

            # サーバーサイドツールのループ（pause_turnに対応）
            max_continuations = 5
            continuations = 0

            while True:
                response = self.client.messages.create(
                    model=MODEL,
                    max_tokens=8192,
                    system=SYSTEM_PROMPT,
                    tools=self.tools,
                    messages=messages,
                )
                stop_reason = response.stop_reason

                # アシスタントメッセージを履歴に追加
                messages.append({"role": "assistant", "content": response.content})

                if stop_reason == "end_turn":
                    for block in response.content:
                        if block.type == "text":
                            content_text += block.text
                    break

                elif stop_reason == "pause_turn":
                    # サーバーサイドツールの継続
                    if continuations >= max_continuations:
                        for block in response.content:
                            if block.type == "text":
                                content_text += block.text
                        break
                    continuations += 1
                    continue

                elif stop_reason == "tool_use":
                    # user-defined tool use (通常はサーバーサイドツールのため発生しない)
                    break

                else:
                    break

            return AgentResponse(
                agent_name=self.name,
                content=content_text,
                success=True,
            )

        except anthropic.APIError as e:
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                error=str(e),
            )

    def research_new_openings(self, profile: BusinessProfile) -> AgentResponse:
        """新規募集開始の補助金を重点的にリサーチ"""
        keywords = ["新規募集", "令和7年", "2025年", "申請受付開始"]
        return self.research(profile, keywords)

    def research_deadline_approaching(self, profile: BusinessProfile) -> AgentResponse:
        """締切が近い補助金を重点的にリサーチ"""
        keywords = ["締切間近", "申請期限", "受付終了"]
        return self.research(profile, keywords)

    def parse_subsidies_from_response(self, response_text: str) -> list[SubsidyInfo]:
        """レスポンステキストからSubsidyInfoのリストを抽出"""
        # JSONブロックを探す
        import re
        json_match = re.search(r'```json\s*(.*?)\s*```', response_text, re.DOTALL)
        if not json_match:
            # JSONブロックなしの場合、テキスト全体をJSONとして試みる
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)

        if not json_match:
            return []

        try:
            data = json.loads(json_match.group(1) if '```' in response_text else json_match.group(0))
            subsidies = []
            for s in data.get("subsidies", []):
                subsidies.append(SubsidyInfo(
                    name=s.get("name", ""),
                    organization=s.get("organization", ""),
                    description=s.get("description", ""),
                    amount=s.get("amount", ""),
                    target=s.get("target", ""),
                    deadline=s.get("deadline", "要確認"),
                    url=s.get("url", ""),
                    business_types=s.get("business_types", []),
                    status=s.get("status", "募集中"),
                ))
            return subsidies
        except (json.JSONDecodeError, KeyError):
            return []

    def _build_research_query(
        self, profile: BusinessProfile, keywords: list[str]
    ) -> str:
        """リサーチクエリを構築する"""
        parts = [
            f"以下の事業者向けの補助金・助成金を調査してください。",
            "",
            f"【対象事業者】",
            f"業種: {profile.business_type or '一般'}",
        ]

        if profile.prefecture:
            parts.append(f"所在地: {profile.prefecture}")
        if profile.annual_revenue:
            parts.append(f"年間売上: 約{profile.annual_revenue:,}円")
        if profile.employees is not None:
            parts.append(f"従業員数: {profile.employees}名")
        if profile.description:
            parts.append(f"事業内容: {profile.description}")

        parts += [
            "",
            "【調査してほしい内容】",
            "1. 現在募集中の補助金・助成金（国・都道府県・市区町村・民間）",
            "2. 近日中に募集開始予定のもの",
            "3. この業種に特化した支援制度",
            "4. 申請に際して注意すべきポイント",
            "",
            "【特に重視するキーワード】",
        ]

        if keywords:
            parts += [f"- {kw}" for kw in keywords]
        else:
            parts += [
                f"- {profile.business_type}向け補助金",
                "- 令和7年度 補助金",
                "- 中小企業 助成金",
                "- 個人事業主 支援",
            ]

        parts += [
            "",
            "最新情報をWeb検索して、公式サイトを確認の上、正確な情報をJSON形式でまとめてください。",
            "特に申請期限と金額を正確に記載してください。",
        ]

        return "\n".join(parts)
