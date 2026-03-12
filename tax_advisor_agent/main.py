"""
青色申告確定申告エージェント - メインエントリポイント

使い方:
  python -m tax_advisor_agent.main             # 対話モード
  python -m tax_advisor_agent.main --setup     # 事業者プロフィール設定
  python -m tax_advisor_agent.main --report    # 総合レポート生成
  python -m tax_advisor_agent.main --research  # 即時補助金リサーチ
  python -m tax_advisor_agent.main --schedule  # スケジューラー起動
"""
import sys
import argparse
import signal
import time
import logging
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner

from .config import BUSINESS_TYPES, BUSINESS_PROFILE_FILE
from .models import BusinessProfile
from .agents import OrchestratorAgent
from .scheduler import ResearchScheduler

# ロギング設定
logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

console = Console()


def print_banner() -> None:
    """バナーを表示する"""
    console.print(Panel(
        "[bold blue]青色申告確定申告エージェント[/bold blue]\n"
        "[dim]AI マルチエージェントによる税務・補助金アドバイスシステム[/dim]\n\n"
        "• 青色申告アドバイザー\n"
        "• 業種別税務エージェント\n"
        "• 補助金リサーチエージェント（定期Webリサーチ）",
        title="[bold]Tax Advisor Agent Team[/bold]",
        border_style="blue",
    ))


def setup_profile() -> BusinessProfile:
    """事業者プロフィールを設定する"""
    console.print("\n[bold yellow]事業者プロフィールを設定します[/bold yellow]")
    console.print("（後で変更できます）\n")

    profile = BusinessProfile.load(BUSINESS_PROFILE_FILE) or BusinessProfile()

    profile.business_name = Prompt.ask(
        "事業者名・屋号",
        default=profile.business_name or ""
    )

    # 業種選択
    console.print("\n[bold]業種を選んでください:[/bold]")
    for i, bt in enumerate(BUSINESS_TYPES, 1):
        console.print(f"  {i:2}. {bt}")

    while True:
        choice = Prompt.ask("番号を入力", default="10")
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(BUSINESS_TYPES):
                profile.business_type = BUSINESS_TYPES[idx]
                break
        except ValueError:
            pass
        console.print("[red]1〜10の番号を入力してください[/red]")

    # 年間売上
    revenue_str = Prompt.ask(
        "年間売上（円・概算）",
        default=str(profile.annual_revenue) if profile.annual_revenue else "0"
    )
    try:
        profile.annual_revenue = int(revenue_str.replace(",", ""))
    except ValueError:
        profile.annual_revenue = 0

    # 従業員数
    emp_str = Prompt.ask(
        "従業員数（代表者本人のみは0）",
        default=str(profile.employees)
    )
    try:
        profile.employees = int(emp_str)
    except ValueError:
        profile.employees = 0

    # 都道府県
    profile.prefecture = Prompt.ask(
        "所在地（都道府県）",
        default=profile.prefecture or "東京都"
    )

    # 事業内容
    profile.description = Prompt.ask(
        "事業内容（簡単に）",
        default=profile.description or ""
    )

    # 青色申告
    profile.blue_return = Confirm.ask(
        "青色申告を行っていますか？",
        default=profile.blue_return
    )

    # 保存
    profile.save(BUSINESS_PROFILE_FILE)
    console.print("\n[green]✓ プロフィールを保存しました[/green]")
    return profile


def load_or_setup_profile() -> BusinessProfile:
    """プロフィールを読み込む、なければ設定する"""
    profile = BusinessProfile.load(BUSINESS_PROFILE_FILE)
    if not profile or not profile.business_type:
        console.print("[yellow]事業者プロフィールが未設定です。設定します。[/yellow]")
        profile = setup_profile()
    return profile


def run_interactive_mode(profile: BusinessProfile) -> None:
    """対話モードでエージェントと会話する"""
    orchestrator = OrchestratorAgent()
    history: list[dict] = []

    console.print(f"\n[bold green]対話モードを開始しました[/bold green]")
    console.print(f"事業者: [bold]{profile.business_name or '（未設定）'}[/bold] | "
                  f"業種: [bold]{profile.business_type}[/bold]")
    console.print("[dim]終了: 'exit' または Ctrl+C[/dim]\n")

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]あなた[/bold cyan]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]終了します[/yellow]")
            break

        if user_input.lower() in ("exit", "quit", "終了", "q"):
            console.print("[yellow]終了します[/yellow]")
            break

        if not user_input.strip():
            continue

        # コマンド処理
        if user_input.startswith("/"):
            _handle_command(user_input, profile, orchestrator)
            continue

        # エージェントに問い合わせ
        with console.status("[bold blue]エージェントチームが考えています...[/bold blue]"):
            response = orchestrator.process(user_input, profile, history)

        if response.success:
            console.print(f"\n[bold magenta]アドバイザーチーム[/bold magenta]")
            console.print(Panel(
                Markdown(response.content),
                border_style="magenta",
            ))
            # 会話履歴に追加
            history.append({"role": "user", "content": user_input})
            history.append({"role": "assistant", "content": response.content})
            # 履歴は最新10往復まで保持
            if len(history) > 20:
                history = history[-20:]
        else:
            console.print(f"[red]エラー: {response.error}[/red]")

        console.print()


def _handle_command(command: str, profile: BusinessProfile, orchestrator: OrchestratorAgent) -> None:
    """スラッシュコマンドを処理する"""
    cmd = command.strip().lower()

    if cmd == "/help":
        console.print(Panel(
            "/help       - このヘルプを表示\n"
            "/profile    - 事業者プロフィールを表示\n"
            "/setup      - プロフィールを再設定\n"
            "/report     - 総合アドバイスレポートを生成\n"
            "/research   - 補助金リサーチを即時実行\n"
            "/history    - 最新リサーチ結果を表示\n"
            "/schedule   - スケジューラー情報を表示",
            title="コマンド一覧",
            border_style="cyan",
        ))

    elif cmd == "/profile":
        _display_profile(profile)

    elif cmd == "/setup":
        new_profile = setup_profile()
        profile.__dict__.update(new_profile.__dict__)

    elif cmd == "/report":
        console.print("[bold]総合レポートを生成中...[/bold]")
        with console.status("[bold blue]各エージェントが分析中...[/bold blue]"):
            response = orchestrator.generate_comprehensive_report(profile)
        if response.success:
            console.print(Panel(Markdown(response.content), title="総合アドバイスレポート", border_style="green"))
        else:
            console.print(f"[red]エラー: {response.error}[/red]")

    elif cmd == "/research":
        scheduler = ResearchScheduler(console=console)
        with console.status("[bold blue]補助金リサーチ実行中...[/bold blue]"):
            report = scheduler.run_now()
        if report:
            _display_research_report(report)

    elif cmd == "/history":
        scheduler = ResearchScheduler()
        reports = scheduler.get_latest_reports(3)
        if not reports:
            console.print("[yellow]リサーチ履歴がありません。/research で実行してください。[/yellow]")
        else:
            for r in reversed(reports):
                console.print(f"\n[bold]{r.get('created_at', '')}[/bold] - "
                               f"{len(r.get('subsidies', []))}件")
                if r.get("summary"):
                    console.print(f"  {r['summary'][:100]}...")

    else:
        console.print(f"[red]不明なコマンド: {command} (/help でコマンド一覧)[/red]")


def run_report_mode(profile: BusinessProfile) -> None:
    """総合レポートを生成して表示する"""
    orchestrator = OrchestratorAgent()
    console.print("\n[bold]総合アドバイスレポートを生成しています...[/bold]")
    console.print("[dim]税務アドバイザー・業種別アドバイザー・補助金リサーチャーが分析中[/dim]\n")

    with console.status("[bold blue]エージェントチームが分析中...[/bold blue]"):
        response = orchestrator.generate_comprehensive_report(profile)

    if response.success:
        console.print(Panel(
            Markdown(response.content),
            title=f"[bold]{profile.business_type} 総合アドバイスレポート[/bold]",
            border_style="green",
        ))
    else:
        console.print(f"[red]レポート生成に失敗しました: {response.error}[/red]")


def run_research_mode(profile: BusinessProfile, research_type: str = "general") -> None:
    """補助金リサーチを実行する"""
    scheduler = ResearchScheduler(console=console)

    console.print(f"\n[bold]補助金リサーチを開始します[/bold] ({research_type})")
    with console.status("[bold blue]Webリサーチ実行中...[/bold blue]"):
        report = scheduler.run_now(research_type)

    if report:
        _display_research_report(report)
    else:
        console.print("[red]リサーチに失敗しました[/red]")


def run_scheduler_mode(profile: BusinessProfile) -> None:
    """スケジューラーを起動して定期リサーチを開始する"""
    scheduler = ResearchScheduler(console=console)

    console.print("\n[bold]スケジューラーを起動します[/bold]")
    scheduler.start()

    # ジョブ一覧表示
    jobs = scheduler.get_job_list()
    table = Table(title="スケジュール済みジョブ")
    table.add_column("ID", style="cyan")
    table.add_column("ジョブ名")
    table.add_column("次回実行時刻", style="green")
    for job in jobs:
        table.add_row(job["id"], job["name"], job["next_run"])
    console.print(table)

    console.print("\n[bold yellow]スケジューラーが実行中です。Ctrl+C で停止します。[/bold yellow]")

    def signal_handler(sig, frame):
        console.print("\n[yellow]スケジューラーを停止します...[/yellow]")
        scheduler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 起動時に即時リサーチを実行するか確認
    if Confirm.ask("今すぐリサーチを実行しますか？"):
        run_research_mode(profile)

    console.print("[dim]スケジューラーはバックグラウンドで実行中...[/dim]")
    while True:
        time.sleep(60)


def _display_profile(profile: BusinessProfile) -> None:
    """プロフィールを表示する"""
    table = Table(title="事業者プロフィール")
    table.add_column("項目", style="cyan")
    table.add_column("値")
    table.add_row("事業者名", profile.business_name or "（未設定）")
    table.add_row("業種", profile.business_type or "（未設定）")
    table.add_row("年間売上", f"{profile.annual_revenue:,}円" if profile.annual_revenue else "（未設定）")
    table.add_row("従業員数", f"{profile.employees}名")
    table.add_row("所在地", profile.prefecture or "（未設定）")
    table.add_row("青色申告", "申請済み" if profile.blue_return else "未申請")
    table.add_row("事業内容", profile.description or "（未設定）")
    console.print(table)


def _display_research_report(report) -> None:
    """リサーチレポートを表示する"""
    if report.summary:
        console.print(Panel(report.summary, title="リサーチサマリー", border_style="blue"))

    if not report.subsidies:
        console.print("[yellow]補助金情報が取得できませんでした[/yellow]")
        return

    table = Table(title=f"補助金・助成金情報 ({len(report.subsidies)}件)", show_lines=True)
    table.add_column("補助金名", style="bold cyan", max_width=25)
    table.add_column("実施機関", max_width=15)
    table.add_column("金額・補助率", max_width=15)
    table.add_column("申請期限", style="yellow", max_width=12)
    table.add_column("状況", max_width=8)

    for s in report.subsidies:
        status_color = "green" if s.status == "募集中" else "yellow" if s.status == "準備中" else "red"
        table.add_row(
            s.name,
            s.organization,
            s.amount,
            s.deadline,
            f"[{status_color}]{s.status}[/{status_color}]",
        )

    console.print(table)


def main() -> None:
    """メインエントリポイント"""
    parser = argparse.ArgumentParser(
        description="青色申告確定申告エージェント - AIマルチエージェント税務・補助金アドバイスシステム"
    )
    parser.add_argument("--setup", action="store_true", help="事業者プロフィールを設定")
    parser.add_argument("--report", action="store_true", help="総合アドバイスレポートを生成")
    parser.add_argument(
        "--research",
        nargs="?",
        const="general",
        choices=["general", "new_openings", "deadline"],
        help="補助金リサーチを実行 (general/new_openings/deadline)"
    )
    parser.add_argument("--schedule", action="store_true", help="定期リサーチスケジューラーを起動")

    args = parser.parse_args()

    print_banner()

    if args.setup:
        setup_profile()
        return

    profile = load_or_setup_profile()

    if args.report:
        run_report_mode(profile)
    elif args.research is not None:
        run_research_mode(profile, args.research)
    elif args.schedule:
        run_scheduler_mode(profile)
    else:
        # デフォルト: 対話モード
        run_interactive_mode(profile)


if __name__ == "__main__":
    main()
