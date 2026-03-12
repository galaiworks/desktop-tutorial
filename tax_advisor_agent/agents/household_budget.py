"""
家計簿・予算管理アドバイザーエージェント

月次の支出データを分析し、予算オーバーや節約のアドバイスを提供する。
個人費と事業費の振り分けチェックも行う。
"""
from datetime import datetime
import anthropic

from ..config import MODEL
from ..models import BusinessProfile, AgentResponse
from ..storage import ExpenseDB

SYSTEM_PROMPT = """あなたは家計簿・予算管理の専門アドバイザーです。
個人事業主・フリーランスの方の家計と事業の両面から、わかりやすくアドバイスします。

## 役割
1. **月次支出の分析**: カテゴリ別・個人費/事業費別の集計を読み解く
2. **予算管理**: 予算に対する進捗を評価し、予算オーバーを警告
3. **節約提案**: 無駄な支出や見直しポイントを具体的に提案
4. **事業費チェック**: 事業費として計上した支出の妥当性を確認
5. **確定申告準備**: 月末・年末に向けた経費整理のアドバイス

## 回答スタイル
- LINEメッセージとして送られるため、**短く・わかりやすく**
- 数字は見やすいフォーマットで（円単位カンマ区切り）
- 絵文字を適度に使ってわかりやすく
- 優先度の高い情報を先に伝える
- 具体的なアクションを1〜3点に絞る

必ず日本語で回答してください。"""


class HouseholdBudgetAgent:
    """家計簿・予算管理アドバイザー"""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.db = ExpenseDB()
        self.name = "家計簿アドバイザー"

    def get_monthly_report(
        self,
        user_id: str,
        year_month: str | None = None,
        profile: BusinessProfile | None = None,
    ) -> AgentResponse:
        """月次レポートを生成してアドバイスする"""
        ym = year_month or datetime.now().strftime("%Y-%m")
        data = self.db.get_budget_vs_actual(user_id, ym)
        summary = self.db.get_monthly_summary(user_id, ym)

        prompt = self._build_monthly_report_prompt(data, summary, profile)

        return self._call_claude(prompt)

    def get_budget_alert(
        self,
        user_id: str,
        year_month: str | None = None,
    ) -> AgentResponse | None:
        """予算超過アラートを返す（超過していない場合はNone）"""
        ym = year_month or datetime.now().strftime("%Y-%m")
        data = self.db.get_budget_vs_actual(user_id, ym)

        alerts = []
        for expense_type in ("personal", "business"):
            info = data[expense_type]
            if info["budget"] > 0 and info["actual"] > info["budget"]:
                over = info["actual"] - info["budget"]
                alerts.append(
                    f"{'生活費' if expense_type=='personal' else '事業費'}が予算を"
                    f"{over:,}円オーバー（{info['ratio']}%使用）"
                )
            elif info["budget"] > 0 and info["ratio"] and info["ratio"] >= 80:
                alerts.append(
                    f"{'生活費' if expense_type=='personal' else '事業費'}が予算の"
                    f"{info['ratio']}%に達しています"
                )

        if not alerts:
            return None

        prompt = f"""
{ym} の予算アラートについてLINE通知文を作成してください。

アラート内容:
{chr(10).join(f'・{a}' for a in alerts)}

今月残り日数: {_remaining_days(ym)}日

短く（3〜5行）、具体的な改善アドバイスを1つ含めてください。
"""
        return self._call_claude(prompt)

    def analyze_expense_split(
        self,
        user_id: str,
        year_month: str | None = None,
    ) -> AgentResponse:
        """個人費・事業費の振り分けを確認してアドバイスする"""
        ym = year_month or datetime.now().strftime("%Y-%m")
        expenses = self.db.get_monthly_expenses(user_id, ym)

        mixed_expenses = [e for e in expenses if e["expense_type"] == "mixed"]
        business_expenses = [e for e in expenses if e["expense_type"] == "business"]

        prompt = f"""
{ym} の支出振り分けをチェックしてください。

【事業費計上済み: {len(business_expenses)}件】
{_format_expense_list(business_expenses[:5])}

【按分が必要な混在支出: {len(mixed_expenses)}件】
{_format_expense_list(mixed_expenses[:5])}

以下の点でアドバイスしてください:
1. 事業費として問題なさそうか（税務上の妥当性）
2. 按分が必要なものの按分方法の提案
3. 見落としている事業費がないか（業種に合わせて）
4. 確定申告に向けて今整理すべきこと

LINEメッセージとして読みやすい形式で。"""

        return self._call_claude(prompt)

    def get_daily_summary_message(self, user_id: str) -> str:
        """日次サマリーLINE通知テキストを生成する"""
        ym = datetime.now().strftime("%Y-%m")
        today = datetime.now().strftime("%Y-%m-%d")
        data = self.db.get_budget_vs_actual(user_id, ym)
        recent = self.db.get_recent_expenses(user_id, limit=3)

        lines = [f"📊 {ym} 家計簿サマリー\n"]

        # 支出合計
        lines.append(f"💰 今月合計: {data['grand_total']:,}円")
        p = data["personal"]
        b = data["business"]
        if p["budget"]:
            bar = _progress_bar(p["ratio"] or 0)
            lines.append(f"🏠 生活費: {p['actual']:,}円 / {p['budget']:,}円 {bar}")
        if b["budget"]:
            bar = _progress_bar(b["ratio"] or 0)
            lines.append(f"💼 事業費: {b['actual']:,}円 / {b['budget']:,}円 {bar}")

        # 最近の支出
        if recent:
            lines.append("\n📝 最近の記録:")
            for e in recent:
                icon = "💼" if e["expense_type"] == "business" else "🏠"
                lines.append(f"{icon} {e['store_name'] or e['description'] or 'その他'}: {e['total_amount']:,}円")

        lines.append("\nレシートを送ると自動で記録できます📸")
        return "\n".join(lines)

    def _build_monthly_report_prompt(
        self,
        data: dict,
        summary: dict,
        profile: BusinessProfile | None,
    ) -> str:
        business_type = profile.business_type if profile else ""
        ym = data["year_month"]

        # カテゴリ別集計テキスト
        cat_lines = []
        for cat_key, cat_data in sorted(
            data["by_category"].items(), key=lambda x: -x[1]["total"]
        )[:8]:
            cat_name = self.db.get_category_name(cat_key)
            b_amt = cat_data.get("business", 0)
            p_amt = cat_data.get("personal", 0)
            cat_lines.append(
                f"  {cat_name}: {cat_data['total']:,}円"
                + (f"（事業:{b_amt:,}円）" if b_amt else "")
            )

        return f"""
{ym} の家計簿レポートを分析して、LINEメッセージ形式でアドバイスしてください。

【月次集計】
・生活費合計: {data['personal']['actual']:,}円
  予算: {data['personal']['budget']:,}円（達成率: {data['personal']['ratio'] or 'N/A'}%）
・事業費合計: {data['business']['actual']:,}円
  予算: {data['business']['budget']:,}円（達成率: {data['business']['ratio'] or 'N/A'}%）
・総合計: {data['grand_total']:,}円

【カテゴリ別】
{chr(10).join(cat_lines) or '  （データなし）'}

業種: {business_type or '一般'}
残り日数: {_remaining_days(ym)}日

分析してほしいこと:
1. 支出傾向の評価（多い・少ない・注意すべきカテゴリ）
2. 予算管理の状況
3. 節約・最適化の提案（具体的に）
4. 事業費の見直しポイント（業種に応じて）
5. 今月残りの資金計画アドバイス

簡潔なLINEメッセージで。絵文字を適度に使って読みやすく。
"""

    def _call_claude(self, prompt: str) -> AgentResponse:
        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return AgentResponse(agent_name=self.name, content=text, success=True)
        except anthropic.APIError as e:
            return AgentResponse(
                agent_name=self.name, content="", success=False, error=str(e)
            )


# ── ヘルパー関数 ──────────────────────────────────────────

def _format_expense_list(expenses: list[dict]) -> str:
    if not expenses:
        return "  （なし）"
    lines = []
    for e in expenses:
        name = e.get("store_name") or e.get("description") or "その他"
        lines.append(f"  ・{e['date']} {name}: {e['total_amount']:,}円")
    return "\n".join(lines)


def _remaining_days(year_month: str) -> int:
    from calendar import monthrange
    now = datetime.now()
    try:
        y, m = map(int, year_month.split("-"))
        _, last_day = monthrange(y, m)
        end = datetime(y, m, last_day)
        remaining = (end - now).days
        return max(0, remaining)
    except (ValueError, AttributeError):
        return 0


def _progress_bar(ratio: float) -> str:
    filled = min(int(ratio / 10), 10)
    bar = "█" * filled + "░" * (10 - filled)
    color = "🔴" if ratio >= 100 else "🟡" if ratio >= 80 else "🟢"
    return f"{color} [{bar}] {ratio:.0f}%"
