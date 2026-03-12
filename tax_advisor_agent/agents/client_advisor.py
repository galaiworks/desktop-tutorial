"""
LINEクライアント向けアドバイザーエージェント

LINE ユーザーとの対話に特化した軽量なアドバイザー。
複雑な質問は OrchestratorAgent に委譲する。
"""
from datetime import datetime
import anthropic

from ..config import MODEL
from ..models import BusinessProfile, AgentResponse
from ..storage import ExpenseDB

SYSTEM_PROMPT = """あなたは個人事業主・フリーランスの強い味方、LINEアドバイザーです。
名前は「あおちゃん（青色申告ちゃん）」。

## キャラクター
- 親しみやすく、フレンドリーな口調
- でも税務・経費・補助金の知識は本物
- 難しい税務用語を使わず、わかりやすく説明
- LINEで会話するので、短く・要点を絞る
- 困ったことには必ず解決策を提示

## 得意なこと
1. 「これ経費になりますか？」への素早い回答
2. 青色申告の基本的な疑問解消
3. 「今月いくら使った？」などの家計チェック
4. 補助金・助成金のお知らせ
5. 「何をすればいい？」への次のアクション提示

## LINE対話のルール
- 1メッセージは5〜8行以内
- 箇条書きは最大3点
- 「はい・いいえ」で答えられる質問を最後に添えて会話を続ける
- 複雑な質問には「詳しく調べますね！少々お待ちを🔍」と前置き
- 絵文字を適度に（多すぎず）使う

必ず日本語で回答してください。"""

# よく使われる定型メッセージ
WELCOME_MESSAGE = """こんにちは！青色申告アシスタントの「あおちゃん」です🌱

私にできること：
📸 レシート写真→自動で家計簿に記録
💼 経費かどうかすぐ判定
📊 月次収支レポート
🔔 補助金・締切アラート
💬 税務の疑問を何でも相談

まずはレシートを送ってみてください！
または「メニュー」と送ると使い方が見られます。"""

MENU_MESSAGE = """📋 メニュー

【記録】
📸 レシート写真を送る→自動記録
✏️「手動入力 1500円 コンビニ」→手入力

【確認】
📊「今月のまとめ」→月次レポート
💰「予算は？」→予算vs実績
📝「最近の支出」→直近10件

【相談】
❓ 経費になる？→「〇〇は経費になりますか」
💡「節税したい」→節税アドバイス
🎁「補助金は？」→最新情報を検索

【設定】
⚙️「設定」→通知・予算の設定

何でも気軽に話しかけてね！"""

HELP_KEYWORDS = {
    "メニュー": MENU_MESSAGE,
    "ヘルプ": MENU_MESSAGE,
    "help": MENU_MESSAGE,
    "使い方": MENU_MESSAGE,
}


class ClientAdvisorAgent:
    """LINE クライアント向けアドバイザー"""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.db = ExpenseDB()
        self.name = "あおちゃん"

    def respond(
        self,
        user_message: str,
        user_id: str,
        profile: BusinessProfile | None = None,
        conversation_history: list[dict] | None = None,
    ) -> AgentResponse:
        """ユーザーメッセージへの応答を生成する"""
        # 定型メッセージチェック
        for keyword, response_text in HELP_KEYWORDS.items():
            if user_message.strip() == keyword:
                return AgentResponse(
                    agent_name=self.name,
                    content=response_text,
                    success=True,
                )

        # コンテキスト構築
        history = conversation_history or []
        system = self._build_system_with_context(user_id, profile)
        messages = history + [{"role": "user", "content": user_message}]

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=600,
                system=system,
                messages=messages,
            )
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return AgentResponse(
                agent_name=self.name, content=text, success=True
            )
        except anthropic.APIError as e:
            return AgentResponse(
                agent_name=self.name, content="", success=False, error=str(e)
            )

    def is_expense_query(self, message: str) -> bool:
        """支出記録の意図があるかチェック"""
        keywords = [
            "円", "¥", "￥", "支払", "買", "食べ", "乗", "使",
            "払", "購入", "レシート", "領収"
        ]
        return any(kw in message for kw in keywords)

    def is_subsidy_query(self, message: str) -> bool:
        """補助金の問い合わせかチェック"""
        keywords = [
            "補助金", "助成金", "給付金", "支援金", "申請",
            "もらえる", "受給", "制度"
        ]
        return any(kw in message for kw in keywords)

    def is_tax_query(self, message: str) -> bool:
        """税務の問い合わせかチェック"""
        keywords = [
            "経費", "控除", "税金", "確定申告", "青色", "インボイス",
            "消費税", "所得税", "節税", "帳簿"
        ]
        return any(kw in message for kw in keywords)

    def parse_manual_expense(self, message: str) -> dict | None:
        """
        「手動入力 1500円 コンビニ 昼食」のようなメッセージをパース。
        成功した場合は辞書、失敗した場合は None を返す。
        """
        import re
        # 金額を抽出（数字 + 円 の組み合わせ）
        amount_match = re.search(r"([0-9,]+)\s*円", message)
        if not amount_match:
            # 先頭の数字だけの場合も考慮
            amount_match = re.search(r"(\d{3,6})", message)
        if not amount_match:
            return None

        amount = int(amount_match.group(1).replace(",", ""))
        # 金額部分を除いた残りをメモにする
        memo = re.sub(r"手動入力|入力|記録|[\d,]+円?", "", message).strip()
        return {
            "amount": amount,
            "memo": memo or "",
            "date": datetime.now().strftime("%Y-%m-%d"),
        }

    def format_receipt_confirmation(self, receipt_data: dict) -> str:
        """レシート処理結果の確認メッセージを生成"""
        icon = "💼" if receipt_data.get("expense_type") == "business" else "🏠"
        lines = [
            f"📸 レシートを読み取りました！\n",
            f"🏪 {receipt_data.get('store_name', '店舗名不明')}",
            f"📅 {receipt_data.get('date', '日付不明')}",
            f"💰 {receipt_data.get('total_amount', 0):,}円",
            f"{icon} {'事業費' if receipt_data.get('expense_type')=='business' else '生活費'}",
        ]
        if receipt_data.get("business_ratio", 0) > 0 and receipt_data.get("expense_type") == "mixed":
            lines.append(f"  （事業費 {int(receipt_data['business_ratio']*100)}% / 生活費 {int((1-receipt_data['business_ratio'])*100)}%）")
        if receipt_data.get("classification_reason"):
            lines.append(f"📝 {receipt_data['classification_reason']}")
        lines.append("\nこの内容で記録しますか？（「はい」または修正内容を送ってください）")
        return "\n".join(lines)

    def _build_system_with_context(
        self, user_id: str, profile: BusinessProfile | None
    ) -> str:
        """コンテキストを含むシステムプロンプトを構築"""
        context_parts = []
        user = self.db.get_user(user_id)
        if user:
            if user.get("monthly_budget"):
                context_parts.append(f"月間生活費予算: {user['monthly_budget']:,}円")
            if user.get("business_budget"):
                context_parts.append(f"月間事業費予算: {user['business_budget']:,}円")
        if profile:
            if profile.business_type:
                context_parts.append(f"業種: {profile.business_type}")
            if profile.annual_revenue:
                context_parts.append(f"年間売上: 約{profile.annual_revenue:,}円")

        if context_parts:
            return SYSTEM_PROMPT + "\n\n## ユーザー情報\n" + "\n".join(f"- {c}" for c in context_parts)
        return SYSTEM_PROMPT
