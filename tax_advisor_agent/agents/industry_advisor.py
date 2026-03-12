"""
業種別アドバイザーエージェント

業種ごとの特有の税務・経費・補助金ポイントをアドバイスする。
"""
import anthropic
from ..config import MODEL
from ..models import BusinessProfile, AgentResponse

SYSTEM_PROMPTS = {
    "IT・ソフトウェア": """あなたはIT・ソフトウェア業界の税務・経営アドバイザーです。
主な専門領域:
- ソフトウェア開発費の資産計上 vs 費用計上の判断
- クラウドサービス・SaaSの費用処理
- 在宅勤務・リモートワーク関連経費（通信費・機器代）
- IT導入補助金の活用
- フリーランスエンジニアの所得区分（事業所得 vs 雑所得）
- 特許・知的財産権の取り扱い
- 海外取引（外貨建て収益）の処理""",

    "製造業": """あなたは製造業の税務・経営アドバイザーです。
主な専門領域:
- 製造原価の計算と在庫評価
- 設備投資の減価償却（製造業特有の機械装置）
- ものづくり補助金・設備投資補助金
- 研究開発税制（試験研究費の特別控除）
- カーボンニュートラル・DX関連補助金
- 原材料費の棚卸資産管理
- 下請けとの取引・下請代金支払遅延防止法""",

    "小売・飲食": """あなたは小売・飲食業の税務・経営アドバイザーです。
主な専門領域:
- 棚卸資産（商品在庫）の管理と評価
- 食材費・仕入れ費用の処理
- 軽減税率（飲食料品8%）とインボイス対応
- 店舗改装費・内装費の取り扱い
- 小規模事業者持続化補助金
- テイクアウト・デリバリーの消費税扱い
- 廃棄ロスの損金処理
- アルバイト・パートの労務管理と社会保険""",

    "農業・水産": """あなたは農業・水産業の税務・経営アドバイザーです。
主な専門領域:
- 農業所得の計算（農産物の家事消費を含む）
- 農機具・農業用施設の減価償却
- 農業経営基盤強化準備金（農業版リザーブ制度）
- 農地の取得・貸借と税務処理
- 農業補助金（農林水産省・県・市町村）
- 農業者向け融資制度（日本政策金融公庫）
- 6次産業化・農商工連携の支援制度
- 有機農業・GAP認証の取得支援""",

    "建設・不動産": """あなたは建設・不動産業の税務・経営アドバイザーです。
主な専門領域:
- 完成工事高の計上基準（工事進行基準・工事完成基準）
- 建設業許可と経営事項審査
- 不動産所得と事業所得の区分
- 建物・構築物の減価償却
- 建設業向け助成金（安全衛生・技能向上）
- 宅建業・建設業の登録・更新費用
- 外注費と給与の区分（一人親方問題）
- 電子帳簿保存法への対応""",

    "医療・福祉": """あなたは医療・福祉業の税務・経営アドバイザーです。
主な専門領域:
- 社会保険診療報酬の非課税取り扱い
- 医療機器の特別償却
- 介護・障害福祉サービスの消費税処理
- 医療・福祉向け助成金（処遇改善加算など）
- 社会福祉法人・医療法人の税制優遇
- 職員の採用・定着支援補助金
- 診療所・クリニックの開業費用
- 訪問看護・在宅医療の費用処理""",

    "教育・学習支援": """あなたは教育・学習支援業の税務・経営アドバイザーです。
主な専門領域:
- 塾・スクールの消費税（非課税判断）
- 教材費・テキスト代の処理
- オンライン教育の消費税（デジタルサービス）
- 文部科学省・自治体の教育支援補助金
- フリーランス講師への外注費処理
- eラーニング・EdTech導入支援
- 学習塾の広告宣伝費・集客費用
- 幼児教育・保育の無償化対応""",

    "サービス業": """あなたはサービス業全般の税務・経営アドバイザーです。
主な専門領域:
- 役務提供の売上計上タイミング
- 前受金・売掛金の処理
- 人件費と外注費の区分
- 事務所・店舗の賃借料処理
- 小規模事業者持続化補助金
- サービス業向けDX・IT化支援
- 接客・サービス提供に伴う経費
- フランチャイズ加盟金の処理""",

    "運輸・物流": """あなたは運輸・物流業の税務・経営アドバイザーです。
主な専門領域:
- 車両の取得・減価償却（トラック・バンなど）
- 燃料費・高速道路料金の処理
- 運送業向け補助金（電動車両・脱炭素）
- 一人親方ドライバーの労務・税務処理
- 物流DX・自動化投資の補助金
- 運賃収入のインボイス対応
- ドライバーの労働時間管理と法対応
- 貨物保険・自賠責保険の経費処理""",

    "その他": """あなたは中小企業・個人事業主の税務・経営アドバイザーです。
幅広い業種に対応できる一般的な税務知識を持ち、
事業者の状況に合わせた実用的なアドバイスを提供します。""",
}

DEFAULT_SYSTEM_PROMPT = """あなたは中小企業・個人事業主の業種別専門アドバイザーです。
事業者の業種・規模・課題に合わせた、実用的なアドバイスを提供します。"""


class IndustryAdvisorAgent:
    """業種別アドバイザー"""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.name = "業種別アドバイザー"

    def advise(
        self,
        question: str,
        profile: BusinessProfile,
    ) -> AgentResponse:
        """業種に特化したアドバイスを提供する"""
        system_prompt = SYSTEM_PROMPTS.get(
            profile.business_type, DEFAULT_SYSTEM_PROMPT
        )

        # 業種別のシステムプロンプトに共通指示を追加
        full_system = system_prompt + """

## 回答のルール
- 業種の特性を踏まえた具体的なアドバイスをする
- 活用できる補助金・助成金があれば積極的に紹介する
- 節税・コスト削減の具体的な方法を提示する
- 法改正・新制度があれば最新情報を伝える
- 必ず日本語で回答する"""

        context = self._build_context(profile)
        full_question = f"{context}\n\n{question}" if context else question

        try:
            thinking_content = None
            response_text = ""

            with self.client.messages.stream(
                model=MODEL,
                max_tokens=4096,
                thinking={"type": "adaptive"},
                system=full_system,
                messages=[{"role": "user", "content": full_question}],
            ) as stream:
                final = stream.get_final_message()

            for block in final.content:
                if block.type == "thinking":
                    thinking_content = block.thinking
                elif block.type == "text":
                    response_text += block.text

            return AgentResponse(
                agent_name=f"{self.name}（{profile.business_type}）",
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

    def get_industry_tax_tips(self, profile: BusinessProfile) -> AgentResponse:
        """業種特有の税務ポイントを提示する"""
        question = f"""
{profile.business_type}の事業を行っている事業者向けに、
以下の観点から業種特有の重要ポイントを教えてください:

1. この業種特有の経費・売上の処理で見落としがちなポイント
2. 業種ならではの節税方法・特例制度
3. よく見られる申告ミスと対策
4. 業種に適した帳簿・会計ソフトの使い方のヒント
5. インボイス制度・電子帳簿保存法への対応で特に注意すべき点

具体的で実践的な内容でお願いします。
"""
        return self.advise(question, profile)

    def analyze_business_risks(self, profile: BusinessProfile) -> AgentResponse:
        """事業の税務リスクを分析する"""
        question = f"""
以下の事業者の税務リスクを分析してください:

業種: {profile.business_type}
年間売上: {profile.annual_revenue:,}円 (概算)
従業員: {profile.employees}名
事業内容: {profile.description or '未記入'}

【分析してほしい点】
1. 税務調査で指摘されやすいポイント
2. 消費税の課税・非課税の判断が難しい取引
3. 給与 vs 外注費の区分判定リスク
4. 在庫・資産評価の留意点（業種に応じて）
5. 改善すべき経理・記帳方法

リスクの高いものから優先的に教えてください。
"""
        return self.advise(question, profile)

    def _build_context(self, profile: BusinessProfile) -> str:
        """プロフィールからコンテキスト文字列を生成"""
        if not profile.business_type:
            return ""
        parts = [f"【事業者情報】"]
        if profile.business_name:
            parts.append(f"事業者名: {profile.business_name}")
        parts.append(f"業種: {profile.business_type}")
        if profile.annual_revenue:
            parts.append(f"年間売上: 約{profile.annual_revenue:,}円")
        if profile.employees > 0:
            parts.append(f"従業員数: {profile.employees}名")
        if profile.prefecture:
            parts.append(f"所在地: {profile.prefecture}")
        if profile.description:
            parts.append(f"事業内容: {profile.description}")
        return "\n".join(parts)
