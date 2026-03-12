"""
LINE メッセージハンドラー

LINE からのメッセージを解析して適切なエージェントにルーティングする。
テキスト・画像・各種インテントに対応。
"""
import os
import logging
from datetime import datetime

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    FollowEvent,
    UnfollowEvent,
)

from ..config import BUSINESS_PROFILE_FILE
from ..models import BusinessProfile
from ..storage import ExpenseDB
from ..agents.client_advisor import ClientAdvisorAgent, WELCOME_MESSAGE
from ..agents.receipt_agent import ReceiptAgent
from ..agents.household_budget import HouseholdBudgetAgent
from ..agents.orchestrator import OrchestratorAgent

logger = logging.getLogger(__name__)

# ユーザーごとの会話状態（メモリ内）
_user_states: dict[str, dict] = {}
# ユーザーごとの会話履歴
_user_histories: dict[str, list[dict]] = {}


class MessageHandler:
    """LINE メッセージハンドラー"""

    def __init__(self):
        token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
        self._configuration = Configuration(access_token=token)
        self.db = ExpenseDB()
        self.client_advisor = ClientAdvisorAgent()
        self.receipt_agent = ReceiptAgent()
        self.budget_agent = HouseholdBudgetAgent()
        self.orchestrator = OrchestratorAgent()

    # ── イベントハンドラー ────────────────────────────────

    def handle_follow(self, event: FollowEvent) -> None:
        """フォロー（友だち追加）イベント"""
        user_id = event.source.user_id
        self.db.upsert_user(user_id)
        self._reply(event.reply_token, WELCOME_MESSAGE)

    def handle_unfollow(self, event: UnfollowEvent) -> None:
        """ブロック・フォロー解除イベント"""
        user_id = event.source.user_id
        self.db.update_user_settings(user_id, notifications_enabled=0)
        logger.info(f"User {user_id} unfollowed")

    def handle_text(self, event: MessageEvent) -> None:
        """テキストメッセージイベント"""
        user_id = event.source.user_id
        text = event.message.text.strip()
        self.db.upsert_user(user_id)

        # 現在の状態を確認
        state = _user_states.get(user_id, {})

        # ── 状態に応じた処理 ──

        # レシート確認待ち状態
        if state.get("action") == "confirm_receipt":
            self._handle_receipt_confirmation(event, user_id, text, state)
            return

        # 手動入力確認待ち状態
        if state.get("action") == "confirm_manual":
            self._handle_manual_confirmation(event, user_id, text, state)
            return

        # 設定入力待ち状態
        if state.get("action") == "set_budget":
            self._handle_budget_setting(event, user_id, text, state)
            return

        # ── 通常のメッセージルーティング ──

        # 設定コマンド
        if text in ("設定", "⚙️設定"):
            self._handle_settings_menu(event, user_id)
            return

        if text.startswith("予算設定"):
            self._start_budget_setting(event, user_id)
            return

        # 月次レポート
        if text in ("今月のまとめ", "月次レポート", "📊今月のまとめ"):
            self._send_monthly_report(event, user_id)
            return

        # 最近の支出
        if text in ("最近の支出", "支出一覧", "📝最近の支出"):
            self._send_recent_expenses(event, user_id)
            return

        # 予算確認
        if text in ("予算は？", "予算確認", "💰予算は？"):
            self._send_budget_status(event, user_id)
            return

        # 手動入力
        if text.startswith("手動入力") or text.startswith("入力 "):
            self._handle_manual_input(event, user_id, text)
            return

        # 補助金・助成金クエリ → オーケストレーターで詳細調査
        if self.client_advisor.is_subsidy_query(text):
            self._handle_subsidy_query(event, user_id, text)
            return

        # 税務クエリ → オーケストレーターに委譲
        if self.client_advisor.is_tax_query(text) and len(text) > 10:
            self._handle_tax_query(event, user_id, text)
            return

        # デフォルト: クライアントアドバイザーで回答
        profile = self._load_profile()
        history = _user_histories.get(user_id, [])
        response = self.client_advisor.respond(text, user_id, profile, history)

        if response.success:
            self._reply(event.reply_token, response.content)
            # 会話履歴を更新（最大10往復）
            history = history + [
                {"role": "user", "content": text},
                {"role": "assistant", "content": response.content},
            ]
            _user_histories[user_id] = history[-20:]
        else:
            self._reply(event.reply_token, "申し訳ありません、エラーが発生しました。少し後でお試しください🙏")

    def handle_image(self, event: MessageEvent) -> None:
        """画像メッセージ（レシートスキャン）イベント"""
        user_id = event.source.user_id
        self.db.upsert_user(user_id)

        self._reply(event.reply_token, "📸 レシートを受け取りました！読み取り中です、少々お待ちください⏳")

        # 画像データを取得
        image_data = self._get_image_content(event.message.id)
        if not image_data:
            self._push(user_id, "画像の取得に失敗しました。もう一度試してください🙏")
            return

        # レシートを処理
        profile = self._load_profile()
        business_type = profile.business_type if profile else ""
        result = self.receipt_agent.process_receipt_image(
            image_data, business_type=business_type
        )

        if not result.get("success"):
            error_msg = result.get("error", "読み取りに失敗しました")
            self._push(
                user_id,
                f"⚠️ {error_msg}\n\n"
                "レシートが鮮明に写っているか確認して、もう一度送ってください📸",
            )
            return

        # 確認メッセージを表示して状態を保存
        confirm_msg = self.client_advisor.format_receipt_confirmation(result)
        _user_states[user_id] = {
            "action": "confirm_receipt",
            "receipt_data": result,
        }
        self._push(user_id, confirm_msg)

    # ── プライベートメソッド ──────────────────────────────

    def _handle_receipt_confirmation(
        self, event: MessageEvent, user_id: str, text: str, state: dict
    ) -> None:
        """レシート確認の応答を処理する"""
        receipt_data = state.get("receipt_data", {})

        if text in ("はい", "yes", "ok", "OK", "登録", "記録"):
            # DB に登録
            expense_id = self.db.add_expense(
                user_id=user_id,
                date=receipt_data.get("date", datetime.now().strftime("%Y-%m-%d")),
                total_amount=receipt_data.get("total_amount", 0),
                tax_amount=receipt_data.get("tax_amount", 0),
                category=receipt_data.get("category", "other"),
                expense_type=receipt_data.get("expense_type", "personal"),
                business_ratio=receipt_data.get("business_ratio", 0.0),
                store_name=receipt_data.get("store_name", ""),
                description=receipt_data.get("classification_reason", ""),
                source="receipt_scan",
                receipt_items=receipt_data.get("items", []),
            )
            _user_states.pop(user_id, None)
            self._reply(
                event.reply_token,
                f"✅ 記録しました！\n"
                f"（ID: {expense_id}）\n\n"
                f"「今月のまとめ」で支出状況を確認できます📊",
            )

        elif text in ("いいえ", "no", "キャンセル", "取消"):
            _user_states.pop(user_id, None)
            self._reply(event.reply_token, "キャンセルしました。別のレシートを送るか、手動で修正してください✏️")

        elif text.startswith("事業費") or text.startswith("経費"):
            receipt_data["expense_type"] = "business"
            receipt_data["business_ratio"] = 1.0
            _user_states[user_id]["receipt_data"] = receipt_data
            confirm_msg = self.client_advisor.format_receipt_confirmation(receipt_data)
            self._reply(event.reply_token, "✏️ 事業費に変更しました。\n\n" + confirm_msg)

        elif text.startswith("個人費") or text.startswith("生活費"):
            receipt_data["expense_type"] = "personal"
            receipt_data["business_ratio"] = 0.0
            _user_states[user_id]["receipt_data"] = receipt_data
            confirm_msg = self.client_advisor.format_receipt_confirmation(receipt_data)
            self._reply(event.reply_token, "✏️ 生活費に変更しました。\n\n" + confirm_msg)

        else:
            # 修正の意図があるか再度確認
            self._reply(
                event.reply_token,
                "「はい」で登録、「いいえ」でキャンセル、\n"
                "「事業費」「個人費」で変更できます。",
            )

    def _handle_manual_input(
        self, event: MessageEvent, user_id: str, text: str
    ) -> None:
        """手動支出入力を処理する"""
        parsed = self.client_advisor.parse_manual_expense(text)
        if not parsed:
            self._reply(
                event.reply_token,
                "💡 入力形式の例:\n「手動入力 1500円 セブンイレブン 昼食」\n「入力 3000 電車代 出張」",
            )
            return

        state = {
            "action": "confirm_manual",
            "expense_data": {
                "date": parsed["date"],
                "total_amount": parsed["amount"],
                "description": parsed["memo"],
                "store_name": "",
                "expense_type": "personal",
                "category": "other",
            },
        }
        _user_states[user_id] = state

        msg = (
            f"📝 以下の内容で登録しますか？\n\n"
            f"日付: {parsed['date']}\n"
            f"金額: {parsed['amount']:,}円\n"
            f"メモ: {parsed['memo'] or '（なし）'}\n"
            f"種別: 生活費\n\n"
            f"「はい」で登録 / 「事業費」に変更 / 「いいえ」でキャンセル"
        )
        self._reply(event.reply_token, msg)

    def _handle_manual_confirmation(
        self, event: MessageEvent, user_id: str, text: str, state: dict
    ) -> None:
        """手動入力の確認を処理する"""
        expense_data = state.get("expense_data", {})

        if text in ("はい", "yes", "登録"):
            expense_id = self.db.add_expense(
                user_id=user_id,
                date=expense_data["date"],
                total_amount=expense_data["total_amount"],
                category=expense_data["category"],
                expense_type=expense_data["expense_type"],
                store_name=expense_data["store_name"],
                description=expense_data["description"],
                source="line",
            )
            _user_states.pop(user_id, None)
            self._reply(
                event.reply_token,
                f"✅ {expense_data['total_amount']:,}円を記録しました！（ID: {expense_id}）",
            )
        elif text in ("事業費", "経費"):
            expense_data["expense_type"] = "business"
            _user_states[user_id]["expense_data"] = expense_data
            self._reply(
                event.reply_token,
                f"💼 事業費として登録します。\n金額: {expense_data['total_amount']:,}円\n「はい」で確定",
            )
        elif text in ("いいえ", "キャンセル"):
            _user_states.pop(user_id, None)
            self._reply(event.reply_token, "キャンセルしました✅")
        else:
            self._reply(event.reply_token, "「はい」で登録、「事業費」に変更、「いいえ」でキャンセル")

    def _start_budget_setting(self, event: MessageEvent, user_id: str) -> None:
        """予算設定フローを開始する"""
        _user_states[user_id] = {"action": "set_budget", "step": "personal"}
        self._reply(
            event.reply_token,
            "⚙️ 月間予算を設定します。\n\n生活費の月間予算を入力してください（例：200000）\n※円単位の数字のみ",
        )

    def _handle_budget_setting(
        self, event: MessageEvent, user_id: str, text: str, state: dict
    ) -> None:
        """予算設定フローを処理する"""
        import re
        amount_match = re.search(r"(\d+)", text.replace(",", ""))
        if not amount_match:
            self._reply(event.reply_token, "数字で入力してください（例：200000）")
            return

        amount = int(amount_match.group(1))
        step = state.get("step", "personal")

        if step == "personal":
            _user_states[user_id]["personal_budget"] = amount
            _user_states[user_id]["step"] = "business"
            self._reply(
                event.reply_token,
                f"生活費予算: {amount:,}円 ✅\n\n次に事業費の月間予算を入力してください",
            )
        elif step == "business":
            personal = state.get("personal_budget", 0)
            ym = datetime.now().strftime("%Y-%m")
            self.db.set_monthly_budget(user_id, ym, personal, amount)
            self.db.update_user_settings(
                user_id, monthly_budget=personal, business_budget=amount
            )
            _user_states.pop(user_id, None)
            self._reply(
                event.reply_token,
                f"✅ {ym} の予算を設定しました！\n"
                f"生活費: {personal:,}円\n"
                f"事業費: {amount:,}円\n\n"
                f"「今月のまとめ」で進捗を確認できます📊",
            )

    def _send_monthly_report(self, event: MessageEvent, user_id: str) -> None:
        """月次レポートを返信する"""
        self._reply(event.reply_token, "📊 月次レポートを作成中です...⏳")
        ym = datetime.now().strftime("%Y-%m")
        profile = self._load_profile()
        response = self.budget_agent.get_monthly_report(user_id, ym, profile)
        if response.success:
            self._push(user_id, response.content)
        else:
            self._push(user_id, "レポートの生成に失敗しました。少し後でお試しください🙏")

    def _send_recent_expenses(self, event: MessageEvent, user_id: str) -> None:
        """最近の支出一覧を返信する"""
        expenses = self.db.get_recent_expenses(user_id, limit=8)
        if not expenses:
            self._reply(event.reply_token, "まだ支出の記録がありません。\nレシートを送ると自動で記録できます📸")
            return
        lines = ["📝 最近の支出（最新8件）\n"]
        for e in expenses:
            icon = "💼" if e["expense_type"] == "business" else "🏠"
            name = e.get("store_name") or e.get("description") or "その他"
            lines.append(f"{icon} {e['date']} {name}: {e['total_amount']:,}円")
        self._reply(event.reply_token, "\n".join(lines))

    def _send_budget_status(self, event: MessageEvent, user_id: str) -> None:
        """予算状況を返信する"""
        ym = datetime.now().strftime("%Y-%m")
        data = self.db.get_budget_vs_actual(user_id, ym)
        p = data["personal"]
        b = data["business"]
        lines = [f"💰 {ym} 予算状況\n"]

        if p["budget"]:
            remaining = p["remaining"]
            emoji = "🔴" if remaining < 0 else "🟡" if remaining < p["budget"] * 0.2 else "🟢"
            lines.append(f"🏠 生活費: {p['actual']:,}円 / {p['budget']:,}円 {emoji}")
            lines.append(f"  残り: {remaining:,}円 ({p['ratio']}%使用)")
        else:
            lines.append(f"🏠 生活費: {p['actual']:,}円（予算未設定）")

        if b["budget"]:
            remaining = b["remaining"]
            emoji = "🔴" if remaining < 0 else "🟡" if remaining < b["budget"] * 0.2 else "🟢"
            lines.append(f"💼 事業費: {b['actual']:,}円 / {b['budget']:,}円 {emoji}")
            lines.append(f"  残り: {remaining:,}円 ({b['ratio']}%使用)")
        else:
            lines.append(f"💼 事業費: {b['actual']:,}円（予算未設定）")

        if not p["budget"] and not b["budget"]:
            lines.append("\n「予算設定」と送ると予算を設定できます⚙️")

        self._reply(event.reply_token, "\n".join(lines))

    def _handle_settings_menu(self, event: MessageEvent, user_id: str) -> None:
        """設定メニューを表示する"""
        user = self.db.get_user(user_id)
        notif_status = "ON" if user and user.get("notifications_enabled", 1) else "OFF"
        msg = (
            f"⚙️ 設定メニュー\n\n"
            f"通知: {notif_status}\n\n"
            f"【コマンド】\n"
            f"「予算設定」→ 月間予算を設定\n"
            f"「通知ON」「通知OFF」→ 通知の切り替え\n"
            f"「通知時刻 9」→ 通知時刻を変更（0〜23時）"
        )
        self._reply(event.reply_token, msg)

    def _handle_subsidy_query(
        self, event: MessageEvent, user_id: str, text: str
    ) -> None:
        """補助金クエリをオーケストレーターに委譲する"""
        self._reply(event.reply_token, "🔍 補助金情報を調べています、少々お待ちください...")
        profile = self._load_profile()
        response = self.orchestrator.process(text, profile or BusinessProfile())
        if response.success:
            # LINE 向けに要約（長すぎる場合は先頭部分）
            content = response.content[:1000] + ("..." if len(response.content) > 1000 else "")
            self._push(user_id, content)
        else:
            self._push(user_id, "情報の取得に失敗しました。少し後でお試しください🙏")

    def _handle_tax_query(
        self, event: MessageEvent, user_id: str, text: str
    ) -> None:
        """税務クエリをオーケストレーターに委譲する"""
        self._reply(event.reply_token, "💡 調べています、少々お待ちください...")
        profile = self._load_profile()
        response = self.orchestrator.process(text, profile or BusinessProfile())
        if response.success:
            content = response.content[:1200] + ("..." if len(response.content) > 1200 else "")
            self._push(user_id, content)
        else:
            self._push(user_id, "情報の取得に失敗しました🙏")

    def _get_image_content(self, message_id: str) -> bytes | None:
        """LINE から画像バイナリを取得する"""
        try:
            with ApiClient(self._configuration) as api_client:
                blob_api = MessagingApiBlob(api_client)
                content = blob_api.get_message_content(message_id)
            return content
        except Exception as e:
            logger.error(f"Failed to get image content: {e}")
            return None

    def _reply(self, reply_token: str, text: str) -> None:
        """リプライメッセージを送信する"""
        try:
            with ApiClient(self._configuration) as api_client:
                api = MessagingApi(api_client)
                api.reply_message(
                    ReplyMessageRequest(
                        reply_token=reply_token,
                        messages=[TextMessage(text=text[:5000])],  # LINE 文字数制限
                    )
                )
        except Exception as e:
            logger.error(f"Reply failed: {e}")

    def _push(self, user_id: str, text: str) -> None:
        """プッシュメッセージを送信する"""
        try:
            with ApiClient(self._configuration) as api_client:
                api = MessagingApi(api_client)
                from linebot.v3.messaging import PushMessageRequest
                api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=text[:5000])],
                    )
                )
        except Exception as e:
            logger.error(f"Push failed for {user_id}: {e}")

    def _load_profile(self) -> BusinessProfile | None:
        return BusinessProfile.load(BUSINESS_PROFILE_FILE)
