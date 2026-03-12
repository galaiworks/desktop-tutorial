"""
LINE プッシュ通知モジュール

APScheduler と連携して、定期的に LINE ユーザーへメッセージを送信する。
"""
import os
import logging
from datetime import datetime

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    TextMessage,
)

from ..storage import ExpenseDB
from ..agents.household_budget import HouseholdBudgetAgent

logger = logging.getLogger(__name__)


class LineNotifier:
    """LINE プッシュ通知クラス"""

    def __init__(self):
        channel_access_token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
        self._configuration = Configuration(access_token=channel_access_token)
        self.db = ExpenseDB()
        self.budget_agent = HouseholdBudgetAgent()

    # ── 個別通知 ─────────────────────────────────────────

    def send_text(self, user_id: str, text: str) -> bool:
        """テキストメッセージを送信する"""
        try:
            with ApiClient(self._configuration) as api_client:
                api = MessagingApi(api_client)
                api.push_message(
                    PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=text)],
                    )
                )
            return True
        except Exception as e:
            logger.error(f"LINE push failed for {user_id}: {e}")
            return False

    def send_budget_alert(self, user_id: str) -> bool:
        """予算アラートを送信する（超過時のみ）"""
        response = self.budget_agent.get_budget_alert(user_id)
        if not response:
            return False  # 超過なし
        return self.send_text(user_id, response.content)

    def send_monthly_report(self, user_id: str) -> bool:
        """月次レポートを送信する"""
        text = self.budget_agent.get_daily_summary_message(user_id)
        return self.send_text(user_id, text)

    def send_subsidy_alert(self, user_id: str, subsidy_text: str) -> bool:
        """補助金アラートを送信する"""
        msg = f"🎁 補助金・助成金の新情報です！\n\n{subsidy_text}"
        return self.send_text(user_id, msg)

    # ── 一斉通知（全ユーザー） ───────────────────────────

    def broadcast_daily_reminder(self) -> None:
        """毎日の家計簿入力リマインダーを全ユーザーに送信"""
        users = self.db.get_all_users_with_notifications()
        now_hour = datetime.now().hour
        count = 0
        for user in users:
            # ユーザーが設定した通知時刻に合わせる（デフォルト9時）
            if user.get("notification_hour", 9) != now_hour:
                continue
            try:
                ym = datetime.now().strftime("%Y-%m")
                day = datetime.now().day
                msg = (
                    f"おはようございます☀️\n"
                    f"今日も1日頑張りましょう！\n\n"
                    f"昨日の支出はありましたか？\n"
                    f"レシートを送ると自動で記録できます📸\n\n"
                    f"「今月のまとめ」で現在の支出状況も確認できます"
                )
                self.send_text(user["user_id"], msg)
                count += 1
            except Exception as e:
                logger.error(f"Daily reminder failed for {user['user_id']}: {e}")
        logger.info(f"Daily reminder sent to {count} users")

    def broadcast_weekly_summary(self) -> None:
        """週次サマリーを全ユーザーに送信（月曜朝）"""
        users = self.db.get_all_users_with_notifications()
        count = 0
        for user in users:
            try:
                text = self.budget_agent.get_daily_summary_message(user["user_id"])
                header = f"📅 週次サマリーをお届けします！\n\n"
                self.send_text(user["user_id"], header + text)
                count += 1
            except Exception as e:
                logger.error(f"Weekly summary failed for {user['user_id']}: {e}")
        logger.info(f"Weekly summary sent to {count} users")

    def broadcast_monthly_report(self) -> None:
        """月次レポートを全ユーザーに送信（毎月1日）"""
        from datetime import date
        from calendar import monthrange

        now = datetime.now()
        # 先月の年月を取得
        if now.month == 1:
            prev_ym = f"{now.year - 1}-12"
        else:
            prev_ym = f"{now.year}-{now.month - 1:02d}"

        users = self.db.get_all_users_with_notifications()
        count = 0
        for user in users:
            try:
                response = self.budget_agent.get_monthly_report(user["user_id"], prev_ym)
                if response.success:
                    header = f"📊 {prev_ym} の月次レポートです！\n\n"
                    self.send_text(user["user_id"], header + response.content)
                count += 1
            except Exception as e:
                logger.error(f"Monthly report failed for {user['user_id']}: {e}")
        logger.info(f"Monthly report sent to {count} users")

    def broadcast_budget_alerts(self) -> None:
        """予算超過アラートを全ユーザーに送信"""
        users = self.db.get_all_users_with_notifications()
        count = 0
        for user in users:
            if self.send_budget_alert(user["user_id"]):
                count += 1
        logger.info(f"Budget alert sent to {count} users")

    def broadcast_subsidy_news(self, research_text: str) -> None:
        """補助金の新着情報を全ユーザーに送信"""
        users = self.db.get_all_users_with_notifications()
        count = 0
        for user in users:
            if self.send_subsidy_alert(user["user_id"], research_text[:500]):
                count += 1
        logger.info(f"Subsidy news sent to {count} users")

    def send_tax_deadline_reminder(self) -> None:
        """確定申告の期限リマインダー（2月上旬・3月上旬に送信）"""
        now = datetime.now()
        if now.month not in (2, 3):
            return

        if now.month == 2 and now.day <= 10:
            msg = (
                "📅 確定申告の時期が近づいています！\n\n"
                "令和6年分の確定申告期間は\n"
                "2月17日〜3月17日です。\n\n"
                "準備リスト：\n"
                "✅ 収支の集計\n"
                "✅ 経費の領収書整理\n"
                "✅ 青色申告決算書の作成\n\n"
                "「確定申告の準備を手伝って」と送ってください！"
            )
        elif now.month == 3 and now.day <= 10:
            msg = (
                "⚠️ 確定申告の締切まであと約1週間！\n\n"
                "3月17日が締切です。\n"
                "まだの方はお急ぎください！\n\n"
                "延長申請が必要な場合は税務署へ相談を。\n"
                "「残りの作業を教えて」と送ってください📋"
            )
        else:
            return

        users = self.db.get_all_users_with_notifications()
        for user in users:
            self.send_text(user["user_id"], msg)
        logger.info(f"Tax deadline reminder sent to {len(users)} users")
