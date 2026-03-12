"""
LINE Bot サーバー エントリポイント

APScheduler による定期通知 + Flask Webhook サーバーを起動する。

使い方:
  # .env ファイルに環境変数を設定してから:
  python -m tax_advisor_agent.line_server

  # ngrok でローカル開発（別ターミナルで）:
  ngrok http 5000
  # 表示された URL + /webhook を LINE Developers の Webhook URL に設定
"""
import os
import logging
import signal
import sys
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from .config import DATA_DIR
from .line_bot.webhook_server import app
from .line_bot.notifier import LineNotifier
from .scheduler import ResearchScheduler


def _check_env() -> bool:
    """必要な環境変数が設定されているか確認する"""
    required = ["LINE_CHANNEL_ACCESS_TOKEN", "LINE_CHANNEL_SECRET", "ANTHROPIC_API_KEY"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        logger.error(f"必要な環境変数が未設定です: {', '.join(missing)}")
        logger.error(".env ファイルを確認してください。.env.example を参考にしてください。")
        return False
    return True


def create_scheduler() -> BackgroundScheduler:
    """定期通知スケジューラーを構築して返す"""
    notifier = LineNotifier()
    research_scheduler = ResearchScheduler()

    sched = BackgroundScheduler(timezone="Asia/Tokyo")

    # ── 毎日の通知 ──
    # 毎時 0分に通知時刻チェック（ユーザーごとの通知時刻に対応）
    sched.add_job(
        notifier.broadcast_daily_reminder,
        CronTrigger(minute=0, timezone="Asia/Tokyo"),
        id="daily_reminder",
        name="毎日のリマインダー",
        replace_existing=True,
    )

    # 毎日 18時に予算アラートチェック
    sched.add_job(
        notifier.broadcast_budget_alerts,
        CronTrigger(hour=18, minute=0, timezone="Asia/Tokyo"),
        id="budget_alert",
        name="予算アラート",
        replace_existing=True,
    )

    # ── 週次の通知 ──
    # 毎週月曜 8時に週次サマリー
    sched.add_job(
        notifier.broadcast_weekly_summary,
        CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="Asia/Tokyo"),
        id="weekly_summary",
        name="週次サマリー",
        replace_existing=True,
    )

    # 毎週月曜 9時に補助金リサーチ（新規募集重点）
    sched.add_job(
        research_scheduler._run_new_openings_research,
        CronTrigger(day_of_week="mon", hour=9, minute=0, timezone="Asia/Tokyo"),
        id="weekly_subsidy_research",
        name="週次補助金リサーチ",
        replace_existing=True,
    )

    # ── 月次の通知 ──
    # 毎月1日 7時に月次レポート（前月分）
    sched.add_job(
        notifier.broadcast_monthly_report,
        CronTrigger(day=1, hour=7, minute=0, timezone="Asia/Tokyo"),
        id="monthly_report",
        name="月次レポート",
        replace_existing=True,
    )

    # 毎月1日 9時に確定申告期限チェック
    sched.add_job(
        notifier.send_tax_deadline_reminder,
        CronTrigger(day=1, hour=9, minute=0, timezone="Asia/Tokyo"),
        id="tax_deadline",
        name="確定申告期限リマインダー",
        replace_existing=True,
    )

    # 毎月15日 9時に締切間近の補助金チェック
    sched.add_job(
        research_scheduler._run_deadline_research,
        CronTrigger(day=15, hour=9, minute=0, timezone="Asia/Tokyo"),
        id="deadline_check",
        name="補助金締切チェック",
        replace_existing=True,
    )

    return sched


def main() -> None:
    """メインエントリポイント"""
    if not _check_env():
        sys.exit(1)

    logger.info("=" * 60)
    logger.info("青色申告確定申告エージェント - LINE Bot サーバー起動")
    logger.info("=" * 60)
    logger.info(f"データディレクトリ: {DATA_DIR}")

    # スケジューラー起動
    sched = create_scheduler()
    sched.start()
    logger.info("スケジューラー起動完了")
    for job in sched.get_jobs():
        logger.info(f"  [{job.id}] {job.name} - 次回: {job.next_run_time}")

    # グレースフルシャットダウン
    def shutdown(sig, frame):
        logger.info("シャットダウン中...")
        sched.shutdown(wait=False)
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Flask サーバー起動
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() == "true"
    logger.info(f"Webhook サーバー起動: http://0.0.0.0:{port}/webhook")
    logger.info("LINE Developers の Webhook URL: https://<your-domain>/webhook")

    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
        use_reloader=False,  # APScheduler との二重起動を防ぐ
    )


if __name__ == "__main__":
    main()
