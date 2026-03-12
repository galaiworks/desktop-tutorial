"""
定期リサーチスケジューラー

APSchedulerを使って定期的に補助金・助成金情報をリサーチし、
新しい情報を通知する。
"""
import json
import logging
from datetime import datetime
from pathlib import Path

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger

from .config import (
    RESEARCH_RESULTS_FILE,
    BUSINESS_PROFILE_FILE,
    RESEARCH_INTERVAL_HOURS,
)
from .models import BusinessProfile, ResearchReport
from .agents import SubsidyResearcherAgent, OrchestratorAgent

logger = logging.getLogger(__name__)


class ResearchScheduler:
    """定期リサーチスケジューラー"""

    def __init__(self, console=None):
        self.scheduler = BackgroundScheduler(timezone="Asia/Tokyo")
        self.researcher = SubsidyResearcherAgent()
        self.console = console  # Rich Console (オプション)
        self._is_running = False

    def start(self, interval_hours: int = RESEARCH_INTERVAL_HOURS) -> None:
        """スケジューラーを開始する"""
        if self._is_running:
            return

        # 毎日 朝9時にリサーチ実行
        self.scheduler.add_job(
            self._run_research,
            CronTrigger(hour=9, minute=0, timezone="Asia/Tokyo"),
            id="daily_research",
            name="毎日の補助金リサーチ",
            replace_existing=True,
        )

        # 毎週月曜 8時に「新規募集開始」重点リサーチ
        self.scheduler.add_job(
            self._run_new_openings_research,
            CronTrigger(day_of_week="mon", hour=8, minute=0, timezone="Asia/Tokyo"),
            id="weekly_new_openings",
            name="週次新規募集リサーチ",
            replace_existing=True,
        )

        # 毎月1日 7時に「締切間近」アラート
        self.scheduler.add_job(
            self._run_deadline_research,
            CronTrigger(day=1, hour=7, minute=0, timezone="Asia/Tokyo"),
            id="monthly_deadline_check",
            name="月次締切確認",
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True
        logger.info("スケジューラーを開始しました")
        self._log("スケジューラーを開始しました（毎日9時・毎週月曜8時・毎月1日7時）")

    def stop(self) -> None:
        """スケジューラーを停止する"""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("スケジューラーを停止しました")

    def run_now(self, research_type: str = "general") -> ResearchReport | None:
        """即時リサーチを実行する"""
        profile = self._load_profile()
        if not profile:
            self._log("事業者プロフィールが設定されていません", level="warning")
            return None

        self._log(f"リサーチ開始: {research_type} / 業種: {profile.business_type}")

        if research_type == "new_openings":
            response = self.researcher.research_new_openings(profile)
        elif research_type == "deadline":
            response = self.researcher.research_deadline_approaching(profile)
        else:
            response = self.researcher.research(profile)

        if not response.success:
            self._log(f"リサーチ失敗: {response.error}", level="error")
            return None

        # 結果を解析してレポートに保存
        subsidies = self.researcher.parse_subsidies_from_response(response.content)
        report = ResearchReport(
            business_type=profile.business_type,
            subsidies=subsidies,
            summary=self._extract_summary(response.content),
        )
        report.save(RESEARCH_RESULTS_FILE)

        self._log(
            f"リサーチ完了: {len(subsidies)}件の補助金情報を取得しました"
        )
        return report

    def get_latest_reports(self, n: int = 5) -> list[dict]:
        """最新のリサーチレポートを取得する"""
        return ResearchReport.load_latest(RESEARCH_RESULTS_FILE, n)

    def get_job_list(self) -> list[dict]:
        """スケジュールされたジョブ一覧を取得する"""
        jobs = []
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.strftime("%Y-%m-%d %H:%M") if next_run else "未定",
            })
        return jobs

    def _run_research(self) -> None:
        """定期リサーチの実行（内部用）"""
        logger.info("定期リサーチを実行中...")
        self.run_now("general")

    def _run_new_openings_research(self) -> None:
        """週次新規募集リサーチの実行（内部用）"""
        logger.info("新規募集リサーチを実行中...")
        self.run_now("new_openings")

    def _run_deadline_research(self) -> None:
        """月次締切確認の実行（内部用）"""
        logger.info("締切確認リサーチを実行中...")
        self.run_now("deadline")

    def _load_profile(self) -> BusinessProfile | None:
        """保存されたプロフィールを読み込む"""
        return BusinessProfile.load(BUSINESS_PROFILE_FILE)

    def _extract_summary(self, text: str) -> str:
        """レスポンステキストからサマリーを抽出"""
        import re
        # JSONブロック内のsummaryフィールドを探す
        json_match = re.search(r'"summary"\s*:\s*"([^"]+)"', text)
        if json_match:
            return json_match.group(1)
        # 最初の段落を使用
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        return lines[0][:200] if lines else "リサーチ完了"

    def _log(self, message: str, level: str = "info") -> None:
        """コンソールまたはロガーにメッセージを出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if self.console:
            color = {"info": "blue", "warning": "yellow", "error": "red"}.get(level, "white")
            self.console.print(f"[{color}][スケジューラー {timestamp}] {message}[/{color}]")
        else:
            getattr(logger, level)(message)
