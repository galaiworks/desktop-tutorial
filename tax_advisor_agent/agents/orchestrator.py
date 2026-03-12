"""
オーケストレーターエージェント

ユーザーの質問・要求を分析し、適切なサブエージェントを呼び出して
回答を統合するメインエージェント。
Claude のツールユースを使ってサブエージェントを協調させる。
"""
import json
import anthropic
from ..config import MODEL
from ..models import BusinessProfile, AgentResponse, ResearchReport
from .tax_advisor import TaxAdvisorAgent
from .subsidy_researcher import SubsidyResearcherAgent
from .industry_advisor import IndustryAdvisorAgent

SYSTEM_PROMPT = """あなたは青色申告・確定申告の総合アドバイザーチームのオーケストレーターです。
ユーザーの質問を分析して、適切な専門エージェントに依頼し、総合的なアドバイスをまとめます。

## 担当エージェント

1. **税務アドバイザー** (`call_tax_advisor`)
   - 青色申告の手続き・記帳・控除に関する質問
   - 経費の処理・確定申告の具体的な方法
   - 消費税・インボイス制度の対応

2. **業種別アドバイザー** (`call_industry_advisor`)
   - 業種特有の税務・経営上の注意点
   - 業種特有の経費・売上の処理方法
   - 業種ごとのリスク・改善ポイント

3. **補助金リサーチャー** (`call_subsidy_researcher`)
   - 最新の補助金・助成金情報の調査
   - 事業者に適した支援制度の提案
   - 申請期限・金額の確認

## 判断ロジック
- 税務・確定申告の質問 → 税務アドバイザー
- 業種特有の経営課題・節税 → 業種別アドバイザー
- 補助金・助成金・支援制度 → 補助金リサーチャー
- 複合的な質問 → 複数のエージェントを順次呼び出す

## 最終回答のルール
1. 各エージェントの回答を総合してわかりやすくまとめる
2. 優先度の高い情報（期限が近い補助金など）を先に伝える
3. 次のアクションを具体的に提示する
4. 必要に応じて税理士・専門家への相談を促す
5. 日本語で丁寧に回答する"""


class OrchestratorAgent:
    """オーケストレーターエージェント - マルチエージェント協調の中核"""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.name = "オーケストレーター"
        self.tax_advisor = TaxAdvisorAgent()
        self.subsidy_researcher = SubsidyResearcherAgent()
        self.industry_advisor = IndustryAdvisorAgent()

        # サブエージェント呼び出し用ツール定義
        self.tools = [
            {
                "name": "call_tax_advisor",
                "description": "青色申告・税務に関する専門的なアドバイスを取得する。記帳方法、控除、経費処理、消費税、インボイスなど",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "税務アドバイザーへの具体的な質問"
                        },
                        "focus_area": {
                            "type": "string",
                            "description": "重点的に確認したい領域（例：経費計上、青色申告控除、消費税）",
                        }
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "call_industry_advisor",
                "description": "業種特有の税務・経営アドバイスを取得する。業種ならではの節税・リスク・改善点",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "業種別アドバイザーへの質問"
                        },
                        "analysis_type": {
                            "type": "string",
                            "enum": ["general", "tax_tips", "risk_analysis"],
                            "description": "分析タイプ: general=一般, tax_tips=節税ポイント, risk_analysis=リスク分析"
                        }
                    },
                    "required": ["question"]
                }
            },
            {
                "name": "call_subsidy_researcher",
                "description": "最新の補助金・助成金情報をWebリサーチして取得する",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "research_focus": {
                            "type": "string",
                            "enum": ["general", "new_openings", "deadline_approaching"],
                            "description": "リサーチ対象: general=全般, new_openings=新規募集, deadline_approaching=締切間近"
                        },
                        "keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "重点的に調べたいキーワード（例：DX補助金、設備投資、採用支援）"
                        }
                    },
                    "required": ["research_focus"]
                }
            },
        ]

    def process(
        self,
        user_message: str,
        profile: BusinessProfile,
        conversation_history: list[dict] | None = None,
    ) -> AgentResponse:
        """ユーザーメッセージを処理してマルチエージェントで回答する"""
        history = conversation_history or []

        # プロフィール情報をシステムプロンプトに組み込む
        profile_context = self._build_profile_context(profile)
        full_system = SYSTEM_PROMPT + f"\n\n## 現在の事業者情報\n{profile_context}"

        messages = history + [{"role": "user", "content": user_message}]

        try:
            final_response = self._run_agent_loop(full_system, messages, profile)
            return final_response
        except anthropic.APIError as e:
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                error=str(e),
            )

    def _run_agent_loop(
        self,
        system: str,
        messages: list[dict],
        profile: BusinessProfile,
    ) -> AgentResponse:
        """ツールユースのエージェントループを実行する"""
        collected_responses = []

        while True:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=8192,
                thinking={"type": "adaptive"},
                system=system,
                tools=self.tools,
                messages=messages,
            )

            # アシスタントメッセージを追加
            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                # 最終回答を収集
                for block in response.content:
                    if block.type == "text":
                        collected_responses.append(block.text)
                break

            elif response.stop_reason == "tool_use":
                # ツール（サブエージェント）を呼び出す
                tool_results = []
                for block in response.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(
                            block.name, block.input, profile
                        )
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result,
                        })

                # ツール結果を messages に追加
                messages.append({"role": "user", "content": tool_results})

            else:
                # その他の停止理由
                for block in response.content:
                    if block.type == "text":
                        collected_responses.append(block.text)
                break

        return AgentResponse(
            agent_name=self.name,
            content="\n\n".join(collected_responses),
            success=True,
        )

    def _execute_tool(
        self, tool_name: str, tool_input: dict, profile: BusinessProfile
    ) -> str:
        """ツール（サブエージェント）を実行して結果を返す"""
        if tool_name == "call_tax_advisor":
            question = tool_input.get("question", "")
            response = self.tax_advisor.advise(question, profile)
            if response.success:
                return f"【税務アドバイザーの回答】\n{response.content}"
            return f"税務アドバイザーへの問い合わせに失敗しました: {response.error}"

        elif tool_name == "call_industry_advisor":
            question = tool_input.get("question", "")
            analysis_type = tool_input.get("analysis_type", "general")

            if analysis_type == "tax_tips":
                response = self.industry_advisor.get_industry_tax_tips(profile)
            elif analysis_type == "risk_analysis":
                response = self.industry_advisor.analyze_business_risks(profile)
            else:
                response = self.industry_advisor.advise(question, profile)

            if response.success:
                return f"【業種別アドバイザーの回答】\n{response.content}"
            return f"業種別アドバイザーへの問い合わせに失敗しました: {response.error}"

        elif tool_name == "call_subsidy_researcher":
            research_focus = tool_input.get("research_focus", "general")
            keywords = tool_input.get("keywords", [])

            if research_focus == "new_openings":
                response = self.subsidy_researcher.research_new_openings(profile)
            elif research_focus == "deadline_approaching":
                response = self.subsidy_researcher.research_deadline_approaching(profile)
            else:
                response = self.subsidy_researcher.research(profile, keywords)

            if response.success:
                return f"【補助金リサーチ結果】\n{response.content}"
            return f"補助金リサーチに失敗しました: {response.error}"

        return f"不明なツール: {tool_name}"

    def generate_comprehensive_report(self, profile: BusinessProfile) -> AgentResponse:
        """事業者向けの総合レポートを生成する"""
        message = f"""
以下の事業者向けに、青色申告・税務・補助金に関する総合的なアドバイスレポートを作成してください。

1. 青色申告の現状確認と改善ポイント（税務アドバイザーに確認）
2. 業種特有の節税・リスク分析（業種別アドバイザーに確認）
3. 現在利用できる補助金・助成金の最新情報（補助金リサーチャーで調査）

上記3点を各エージェントに依頼して、総合的なレポートにまとめてください。
特に、今すぐ取り組むべき優先事項と、期限が近い補助金申請を強調してください。
"""
        return self.process(message, profile)

    def _build_profile_context(self, profile: BusinessProfile) -> str:
        """プロフィール情報をテキスト化"""
        if not profile.business_name and not profile.business_type:
            return "（事業者情報未設定）"
        parts = []
        if profile.business_name:
            parts.append(f"事業者名: {profile.business_name}")
        if profile.business_type:
            parts.append(f"業種: {profile.business_type}")
        if profile.annual_revenue:
            parts.append(f"年間売上: 約{profile.annual_revenue:,}円")
        if profile.employees >= 0:
            parts.append(f"従業員数: {profile.employees}名")
        if profile.prefecture:
            parts.append(f"所在地: {profile.prefecture}")
        if profile.description:
            parts.append(f"事業内容: {profile.description}")
        parts.append(f"青色申告: {'申請済み' if profile.blue_return else '未申請'}")
        return "\n".join(parts)
