"""
青色申告税務アドバイザーエージェント

青色申告の手続き、控除、経費計上などについて専門的なアドバイスを提供する。
"""
import anthropic
from ..config import MODEL, AOYIRO_FEATURES
from ..models import BusinessProfile, AgentResponse

SYSTEM_PROMPT = """あなたは青色申告・確定申告の専門家エージェントです。
日本の個人事業主・フリーランス・小規模事業者向けに、税務に関する正確で実用的なアドバイスを提供します。

## 専門知識エリア

### 青色申告の基本
- 青色申告特別控除（65万円・55万円・10万円）
- 記帳方法（複式簿記・簡易簿記）
- 必要な帳簿（仕訳帳・総勘定元帳・現金出納帳など）
- e-Tax・電子帳簿保存法

### 経費の取り扱い
- 必要経費として認められるもの・認められないもの
- 按分計算（家賃・光熱費・通信費など）
- 減価償却（30万円未満の特例含む）
- 接待交際費・会議費の扱い

### 所得計算
- 事業所得・雑所得の区分
- 青色申告特別控除の適用
- 純損失の繰越・繰戻し
- 青色事業専従者給与

### 各種控除
- 社会保険料控除
- 小規模企業共済等掛金控除（iDeCo・小規模企業共済）
- 医療費控除・セルフメディケーション税制
- 住宅ローン控除

### 消費税
- インボイス制度（適格請求書等保存方式）
- 簡易課税・本則課税の選択
- 免税事業者・課税事業者の判断

## 回答のルール
1. 正確な情報を提供し、不確かな場合は必ずその旨を伝える
2. 具体的な数字・期限・手続きを明示する
3. 複雑なケースは税理士への相談を推奨する
4. 最新の税制改正（令和6年度・7年度）に対応する
5. 実際の申告書の記入方法も説明できる

必ず日本語で回答してください。"""


class TaxAdvisorAgent:
    """青色申告税務アドバイザー"""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.name = "税務アドバイザー"

    def advise(
        self,
        question: str,
        profile: BusinessProfile,
        conversation_history: list[dict] | None = None,
    ) -> AgentResponse:
        """税務アドバイスを提供する"""
        messages = conversation_history or []

        # 事業者プロフィールをコンテキストとして追加
        context = self._build_context(profile)
        full_question = f"{context}\n\n質問: {question}" if context else question

        messages = messages + [{"role": "user", "content": full_question}]

        try:
            thinking_content = None
            response_text = ""

            with self.client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                final = stream.get_final_message()

            for block in final.content:
                if block.type == "thinking":
                    thinking_content = block.thinking
                elif block.type == "text":
                    response_text += block.text

            return AgentResponse(
                agent_name=self.name,
                content=response_text,
                thinking=thinking_content,
                success=True,
            )

        except anthropic.APIError as e:
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                error=str(e),
            )

    def get_aoyiro_overview(self, profile: BusinessProfile) -> AgentResponse:
        """青色申告の概要・メリットを説明する"""
        question = f"""
事業者情報:
- 業種: {profile.business_type}
- 従業員数: {profile.employees}名
- 青色申告: {'申請済み' if profile.blue_return else '未申請'}

この事業者に適した青色申告のポイントと、特に活用すべき控除・特典を教えてください。
確定申告の準備として今すぐ取り組むべきことも含めてください。
"""
        return self.advise(question, profile)

    def check_deductions(self, profile: BusinessProfile, expenses: dict) -> AgentResponse:
        """経費・控除の適切性をチェックする"""
        expenses_text = "\n".join(
            f"- {k}: {v:,}円" for k, v in expenses.items()
        )
        question = f"""
以下の経費について、{profile.business_type}の事業として青色申告で経費計上できるか、
注意点があればアドバイスしてください。

【経費リスト】
{expenses_text}

各経費について:
1. 経費計上の可否
2. 必要な証憑（領収書・契約書など）
3. 按分が必要な場合の計算方法
4. 注意点・節税ポイント
"""
        return self.advise(question, profile)

    def _build_context(self, profile: BusinessProfile) -> str:
        """プロフィールからコンテキスト文字列を生成"""
        if not profile.business_name and not profile.business_type:
            return ""
        parts = []
        if profile.business_name:
            parts.append(f"事業者名: {profile.business_name}")
        if profile.business_type:
            parts.append(f"業種: {profile.business_type}")
        if profile.annual_revenue:
            parts.append(f"年間売上: 約{profile.annual_revenue:,}円")
        if profile.employees > 0:
            parts.append(f"従業員数: {profile.employees}名")
        if profile.prefecture:
            parts.append(f"所在地: {profile.prefecture}")
        if profile.description:
            parts.append(f"事業内容: {profile.description}")
        return "【事業者情報】\n" + "\n".join(parts)
