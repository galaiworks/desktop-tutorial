# VIRALIZE — AI SNS Growth Platform
## プロダクト設計書 v1.0

---

## 1. エグゼクティブサマリー

**VIRALIZE** は、中小企業・個人クリエイター・マーケティング代理店向けの **AI駆動SNS一元管理・自動成長SaaS** です。

| 指標 | 目標値 |
|:---|:---|
| 年商目標 | **¥500,000,000（5億円）** |
| ターゲット顧客数 | **約2,000社/アカウント** |
| 平均ARPU | **¥20,000/月** |
| 対応プラットフォーム | X(Twitter)・Instagram・TikTok・YouTube・LINE公式 |

---

## 2. 課題とソリューション

### 2.1 市場の課題

| 課題 | 詳細 |
|:---|:---|
| コンテンツ制作コスト | 月20〜30本の投稿を人力で作ると月30〜80万円のコスト |
| 運用担当者不足 | SNS専任担当を置けるのは大企業のみ |
| 効果測定の複雑さ | プラットフォームごとにバラバラな指標・UIを行き来 |
| バズ予測の困難さ | なぜバズったかのノウハウが属人化 |
| 返信・エンゲージメント工数 | DM・コメント対応に毎日数時間 |

### 2.2 VIRALIZEのソリューション

```
[SNSアカウント] ──→ [VIRALIZE AI Engine]
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
   コンテンツ自動生成  最適投稿時間     競合分析
   (文章+画像+動画)    予測・スケジュール  トレンド検知
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                  [統合ダッシュボード]
                   ROI・フォロワー成長
                   エンゲージメント分析
```

---

## 3. 機能仕様

### 3.1 AIコンテンツジェネレーター

#### 投稿文自動生成
- **入力**: 商品/サービスURL・キーワード・トーン指定
- **出力**: プラットフォームごとに最適化された投稿文（文字数・ハッシュタグ・絵文字込み）
- **モデル**: Claude API（claude-sonnet-4-6）+ Fine-tuningでブランドボイス学習

```python
# 利用イメージ
POST /api/v1/generate/post
{
  "brand_context": "オーガニックコーヒーの専門店",
  "platform": "instagram",
  "tone": "friendly",
  "campaign": "新商品発売",
  "keywords": ["エチオピア", "浅煎り", "スペシャルティ"]
}

# レスポンス
{
  "posts": [
    {
      "caption": "...",
      "hashtags": ["#スペシャルティコーヒー", ...],
      "best_post_time": "2026-03-16T07:30:00+09:00",
      "predicted_engagement_rate": 4.2
    }
  ]
}
```

#### AI画像生成連携
- テキストプロンプトから投稿用ビジュアルを自動生成（DALL-E 3 / Stable Diffusion連携）
- ブランドカラー・フォントのテンプレート適用
- A/Bテスト用に複数バリエーション生成

#### AIショート動画スクリプト
- TikTok/Reels用の15〜60秒スクリプト自動生成
- トレンドBGM提案（TikTok Creative Center API連携）
- 字幕テキスト自動生成

### 3.2 バズ予測エンジン

```
収集データ:
├── 過去投稿のエンゲージメント履歴
├── 競合アカウントのバズコンテンツパターン
├── リアルタイムトレンド（X API / Google Trends）
└── 時間帯・曜日別エンゲージメント統計

予測モデル:
└── XGBoost + Transformer (時系列) → エンゲージメント予測スコア
```

**出力**: 各投稿候補の予測インプレッション・エンゲージメント率・バズ確率

### 3.3 AIエンゲージメントアシスタント

- **自動コメント返信**: ポジティブ/ネガティブ判定 → 定型返信 or 下書き作成
- **DM自動対応**: FAQ対応・商品問い合わせへの一次回答自動化
- **炎上アラート**: ネガティブコメント急増を検知 → Slack/メール通知 + 対応文案提示

### 3.4 統合アナリティクスダッシュボード

| レポート | 内容 |
|:---|:---|
| ROIレポート | SNS流入 → コンバージョン追跡（UTMパラメータ自動付与） |
| 競合ベンチマーク | 同業他社のフォロワー増減・エンゲージメント比較 |
| コンテンツ診断 | 何のテーマ/形式が自社ブランドで効くかAI分析 |
| インフルエンサー分析 | コラボ候補の影響力・フォロワー質スコアリング |

### 3.5 マルチプラットフォーム対応

| プラットフォーム | 対応機能 |
|:---|:---|
| X (Twitter) | 投稿・スケジュール・リプライ・インプレッション分析 |
| Instagram | フィード/リール/ストーリー投稿・ハッシュタグ最適化 |
| TikTok | スクリプト生成・投稿スケジュール・トレンド分析 |
| YouTube | Shorts投稿・タイトル/説明文最適化・サムネイル生成 |
| LINE公式 | メッセージ配信・リッチメニュー管理・友だち分析 |

---

## 4. 収益モデル（年商5億円の根拠）

### 4.1 プライシング

| プラン | 月額 | 対象 | アカウント数上限 |
|:---|:---|:---|:---|
| **Starter** | ¥9,800 | 個人・スモールビジネス | 3アカウント |
| **Business** | ¥29,800 | 中小企業・ECサイト | 10アカウント |
| **Agency** | ¥98,000 | 代理店・マーケティング会社 | 50アカウント |
| **Enterprise** | ¥298,000〜 | 大手企業・グループ対応 | 無制限 + 専任CS |

### 4.2 年商5億円の積み上げ試算

```
Starter   (¥9,800/月)  × 500社  = ¥4,900,000/月
Business  (¥29,800/月) × 400社  = ¥11,920,000/月
Agency    (¥98,000/月) × 100社  = ¥9,800,000/月
Enterprise(¥200,000/月)×  30社  = ¥6,000,000/月
                                 ─────────────────
月次MRR合計                       ¥32,620,000/月
年間ARR (×12)                    ¥391,440,000/年

+ 初期設定費 (¥50,000〜¥500,000)  ¥80,000,000/年 (見込み)
+ AIコンテンツ生成従量課金          ¥30,000,000/年 (見込み)
                                 ─────────────────
                          合計   ¥501,440,000/年 ≒ 年商5億円
```

### 4.3 KPI目標（ローンチ〜24ヶ月）

| 月 | MRR目標 | 累計顧客数 | 施策 |
|:---|:---|:---|:---|
| M1-3 | ¥2M | 100社 | β版リリース・ProductHunt・SNS口コミ |
| M6 | ¥8M | 350社 | コンテンツSEO・代理店パートナー開拓 |
| M12 | ¥20M | 900社 | テレビCM・インフルエンサーマーケ |
| M18 | ¥28M | 1,400社 | エンタープライズ営業強化 |
| M24 | ¥33M | 2,030社 | **ARR5億円達成** |

---

## 5. 技術アーキテクチャ

### 5.1 システム全体構成

```
┌─────────────────────────────────────────────────────────┐
│                    VIRALIZE Platform                     │
│                                                          │
│  [Next.js 15 フロントエンド]                              │
│       │                                                  │
│  [API Gateway (FastAPI)]                                 │
│       │                                                  │
│  ┌────┴────────────────────────────────────┐             │
│  │  AI Engine Layer                        │             │
│  │  ├── Content Generator (Claude API)     │             │
│  │  ├── Buzz Predictor (XGBoost/ML)        │             │
│  │  ├── Image Generator (DALL-E 3)         │             │
│  │  └── Sentiment Analyzer (BERT)          │             │
│  └─────────────────────────────────────────┘             │
│       │                                                  │
│  ┌────┴────┐  ┌──────────┐  ┌───────────┐               │
│  │ PostgreSQL│  │  Redis   │  │ Pinecone  │               │
│  │(メイン DB)│  │(キャッシュ)│  │(ベクトルDB)│               │
│  └──────────┘  └──────────┘  └───────────┘               │
│                                                          │
│  [SNS API Connectors]                                    │
│  X API v2 / Meta Graph API / TikTok API / YouTube Data   │
└─────────────────────────────────────────────────────────┘
```

### 5.2 技術スタック

| レイヤー | 採用技術 | 理由 |
|:---|:---|:---|
| フロントエンド | Next.js 15 + TypeScript + Tailwind CSS | SSR対応・開発速度 |
| バックエンド API | Python FastAPI | 非同期処理・AI連携容易 |
| AI生成 | Anthropic Claude API (claude-sonnet-4-6) | 高品質な日本語コンテンツ生成 |
| 画像生成 | OpenAI DALL-E 3 | ビジュアルコンテンツ生成 |
| ML予測 | Python (scikit-learn, XGBoost, PyTorch) | バズ予測モデル |
| データベース | PostgreSQL + Redis + Pinecone | 永続化・キャッシュ・ベクトル検索 |
| インフラ | AWS (ECS Fargate + RDS + ElastiCache) | スケーラビリティ |
| 認証 | Auth0 | SSO・セキュリティ |
| 決済 | Stripe | サブスクリプション管理 |
| 監視 | Datadog + Sentry | APM・エラー監視 |

### 5.3 AIコンテンツ生成フロー

```python
# core/content_generator.py

from anthropic import Anthropic
from typing import Literal

client = Anthropic()

PLATFORM_SPECS = {
    "instagram": {"max_chars": 2200, "hashtag_limit": 30, "tone": "visual-first"},
    "x_twitter": {"max_chars": 280, "hashtag_limit": 3, "tone": "concise-punchy"},
    "tiktok":    {"max_chars": 300, "hashtag_limit": 10, "tone": "trend-driven"},
    "youtube":   {"max_chars": 5000, "hashtag_limit": 15, "tone": "seo-optimized"},
}

def generate_post(
    brand_context: str,
    campaign_brief: str,
    platform: Literal["instagram", "x_twitter", "tiktok", "youtube"],
    brand_voice_examples: list[str] | None = None,
) -> dict:
    """
    ブランドコンテキストとキャンペーン情報からSNS投稿文を生成する
    """
    spec = PLATFORM_SPECS[platform]
    examples_text = ""
    if brand_voice_examples:
        examples_text = "\n過去の人気投稿例:\n" + "\n---\n".join(brand_voice_examples)

    system_prompt = f"""あなたはSNSマーケティングの専門家です。
プラットフォーム: {platform}
文字数制限: {spec['max_chars']}文字以内
ハッシュタグ数: {spec['hashtag_limit']}個以内
トーン: {spec['tone']}

{examples_text}

以下のJSON形式で必ず返答してください:
{{
  "caption": "投稿本文",
  "hashtags": ["#タグ1", "#タグ2"],
  "alt_text": "画像の説明（アクセシビリティ用）",
  "predicted_emotion": "期待する読者の感情",
  "cta": "コール・トゥ・アクション"
}}"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""
ブランド: {brand_context}
キャンペーン: {campaign_brief}

このブランドの{platform}用投稿を3パターン生成してください。
"""
            }
        ]
    )

    return {
        "platform": platform,
        "generated_content": message.content[0].text,
        "tokens_used": message.usage.input_tokens + message.usage.output_tokens,
    }


def analyze_engagement_pattern(
    post_history: list[dict],
    competitor_data: list[dict],
) -> dict:
    """
    過去投稿と競合データからエンゲージメントパターンを分析
    """
    analysis_prompt = f"""
以下のSNSデータを分析し、エンゲージメントを最大化するための洞察を提供してください。

自社投稿履歴（上位10件）:
{post_history[:10]}

競合他社データ:
{competitor_data[:5]}

以下を分析してください:
1. 高エンゲージメント投稿の共通パターン
2. 最適な投稿時間帯と曜日
3. 効果的なコンテンツカテゴリ TOP5
4. 競合との差別化ポイント
5. 次の30日間のコンテンツ戦略提案
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        messages=[{"role": "user", "content": analysis_prompt}]
    )

    return {"analysis": message.content[0].text}
```

### 5.4 バズ予測モデル

```python
# ml/buzz_predictor.py

import numpy as np
from xgboost import XGBRegressor
from sklearn.preprocessing import StandardScaler

class BuzzPredictor:
    """
    投稿コンテンツのエンゲージメント予測モデル

    特徴量:
    - テキスト特徴: 文字数・ハッシュタグ数・絵文字数・感情スコア
    - 時間特徴: 曜日・時間帯・季節性
    - アカウント特徴: フォロワー数・過去平均エンゲージメント率
    - コンテンツ特徴: メディアタイプ・トレンドキーワード含有率
    """

    def __init__(self):
        self.model = XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
        )
        self.scaler = StandardScaler()

    def extract_features(self, post: dict) -> np.ndarray:
        return np.array([
            len(post.get("caption", "")),
            len(post.get("hashtags", [])),
            post.get("emoji_count", 0),
            post.get("sentiment_score", 0.0),   # -1.0 ~ 1.0
            post.get("hour_of_day", 12),
            post.get("day_of_week", 0),          # 0=月曜
            post.get("has_image", 0),
            post.get("has_video", 0),
            post.get("follower_count", 0),
            post.get("avg_engagement_rate", 0.0),
            post.get("trend_keyword_score", 0.0),
            post.get("brand_mention_count", 0),
        ])

    def predict_engagement(self, post: dict) -> dict:
        features = self.extract_features(post).reshape(1, -1)
        features_scaled = self.scaler.transform(features)
        predicted_engagement = float(self.model.predict(features_scaled)[0])

        # バズ確率: エンゲージメント予測値から算出
        buzz_threshold = 0.05  # 5%以上をバズと定義
        buzz_probability = min(predicted_engagement / buzz_threshold, 1.0)

        return {
            "predicted_engagement_rate": round(predicted_engagement * 100, 2),
            "buzz_probability": round(buzz_probability * 100, 1),
            "recommendation": self._get_recommendation(predicted_engagement),
        }

    def _get_recommendation(self, engagement_rate: float) -> str:
        if engagement_rate >= 0.05:
            return "バズ高確率 — 今すぐ投稿を推奨"
        elif engagement_rate >= 0.02:
            return "平均以上 — ハッシュタグを追加するとさらに改善可能"
        else:
            return "改善余地あり — AIで投稿文の書き直しを推奨"
```

---

## 6. UI/UX設計

### 6.1 画面構成

```
VIRALIZE Dashboard
├── ホーム（今日の投稿スケジュール・AI提案）
├── コンテンツ作成
│   ├── AI投稿文ジェネレーター
│   ├── AI画像生成
│   └── スケジュール管理
├── アナリティクス
│   ├── パフォーマンス概要
│   ├── バズ投稿分析
│   └── 競合比較
├── エンゲージメント
│   ├── コメント・DM管理
│   └── 炎上アラート
└── 設定
    ├── アカウント連携
    ├── ブランドボイス学習
    └── チームメンバー管理
```

### 6.2 主要画面ワイヤーフレーム（テキスト表現）

#### コンテンツ作成画面
```
┌─────────────────────────────────────────────────────────┐
│ ✨ AIコンテンツジェネレーター                             │
├─────────────────────────────────────────────────────────┤
│ [プラットフォーム選択: IG / X / TikTok / YT / LINE]      │
│                                                          │
│ キャンペーンの説明:                                       │
│ ┌──────────────────────────────────────────────────┐    │
│ │ 例: 新商品の夏限定アイスクリームを告知したい。    │    │
│ │ ターゲットは20〜30代女性。明るくポップなトーン。  │    │
│ └──────────────────────────────────────────────────┘    │
│                                                          │
│ [🎨 AI画像も生成する] [📅 最適時間に自動投稿]             │
│                                                          │
│              [✨ 生成する (残り47回/月)]                  │
├─────────────────────────────────────────────────────────┤
│ 生成結果 (3パターン)                          バズ予測    │
│                                                          │
│ ▶ パターンA ──────────────────────────── 🔥 4.2% 高確率  │
│   「夏がきた☀️ 待ってました！...」                        │
│   #アイスクリーム #夏限定 #スイーツ好き                   │
│   最適投稿時間: 明日 19:30                               │
│   [編集] [そのまま投稿] [スケジュール]                    │
│                                                          │
│ ▶ パターンB ──────────────────────────── ⚡ 3.1% 普通    │
│ ▶ パターンC ──────────────────────────── 📈 2.8% 普通    │
└─────────────────────────────────────────────────────────┘
```

---

## 7. 競合分析と差別化

| 競合サービス | 月額 | 弱点 | VIRALIZEの優位性 |
|:---|:---|:---|:---|
| Buffer | $6〜 | AI機能が限定的・日本語弱い | 日本語特化AIコンテンツ生成 |
| Hootsuite | $99〜 | 高価・UI複雑 | 直感的UI・手頃な価格 |
| Sprout Social | $249〜 | 中小企業には高すぎる | SMB向け価格帯 |
| SocialDog | ¥9,000〜 | X特化・AIコンテンツ生成なし | マルチプラットフォーム+AI生成 |
| Canva Pro | ¥1,500〜 | 投稿管理機能なし | 生成〜投稿まで一気通貫 |

**VIRALIZEの3大差別化ポイント:**
1. **日本語特化AI**: 日本のSNS文化・トレンド・絵文字使用に最適化されたClaudeモデル
2. **バズ予測の可視化**: 投稿前にエンゲージメントスコアを提示する機能（業界初）
3. **代理店向け機能**: 複数クライアント管理・ホワイトラベルレポートで代理店市場を攻略

---

## 8. GTM（市場投入戦略）

### Phase 1: ローンチ（M1〜M3）— 目標100社
- ProductHunt掲載（英語版）
- X/note でノウハウコンテンツ発信（SEO・SNS流入）
- SNS運用者コミュニティへの無料トライアル提供
- β版ユーザーのケーススタディ作成

### Phase 2: 成長（M4〜M12）— 目標900社
- Google/Meta広告（CPAターゲット ¥15,000以下）
- マーケティング代理店アライアンス（リセラー契約）
- 業界特化テンプレート集リリース（飲食・美容・EC等）
- 月次ウェビナー開催（SNS運用ノウハウ共有）

### Phase 3: スケール（M13〜M24）— 目標2,000社
- エンタープライズ直販営業チーム組成
- API連携パートナー拡充（CRM・ECプラットフォーム）
- 海外展開（台湾・東南アジア）
- 上場または大手SaaS企業へのM&A検討

---

## 9. チーム構成（フルローンチ時）

| 役割 | 人数 | 主な業務 |
|:---|:---|:---|
| CTO / バックエンドエンジニア | 1 | FastAPI・AI連携・インフラ |
| フロントエンドエンジニア | 2 | Next.js・ダッシュボード |
| MLエンジニア | 1 | バズ予測モデル・データパイプライン |
| プロダクトマネージャー | 1 | ロードマップ・顧客ヒアリング |
| セールス | 2 | エンタープライズ・代理店開拓 |
| カスタマーサクセス | 2 | オンボーディング・チャーン防止 |
| マーケター | 1 | コンテンツSEO・広告運用 |
| **合計** | **10名** | |

**初期コスト試算（年間）:**
- 人件費: ¥120,000,000（平均1,200万/人）
- AWS・APIコスト: ¥30,000,000
- 広告費: ¥50,000,000
- その他（法務・会計・ツール）: ¥10,000,000
- **合計コスト: ¥210,000,000**
- **営業利益（ARR5億円達成時）: ¥290,000,000（利益率58%）**

---

## 10. リスクと対策

| リスク | 影響度 | 対策 |
|:---|:---|:---|
| SNS API仕様変更 | 高 | 複数プラットフォーム分散・APIラッパー抽象化 |
| AI生成コスト増 | 中 | キャッシュ最適化・生成回数制限・モデル選択最適化 |
| 競合の類似機能実装 | 中 | バズ予測・日本語特化の技術的優位性を維持 |
| チャーン率上昇 | 高 | オンボーディング強化・CSチーム増員・NPS定期測定 |
| データプライバシー規制 | 中 | GDPR/個人情報保護法対応・SOC2認証取得 |

---

## 11. 開発ロードマップ

```
2026 Q1 (現在) ─── MVP開発
  ✅ アーキテクチャ設計
  🔄 AIコンテンツジェネレーター (Instagram・X対応)
  🔄 スケジュール投稿機能
  🔄 基本アナリティクス

2026 Q2 ─────────── β版リリース
  ☐ TikTok・YouTube・LINE対応追加
  ☐ バズ予測エンジン v1
  ☐ Stripe決済統合
  ☐ β版100社獲得

2026 Q3 ─────────── 正式リリース
  ☐ AI画像生成連携
  ☐ 競合分析ダッシュボード
  ☐ 代理店プラン・ホワイトラベル機能
  ☐ 正式版リリース・PRキャンペーン

2026 Q4 ─────────── スケール
  ☐ エンタープライズ機能（SSO・監査ログ）
  ☐ API公開（外部連携）
  ☐ 海外展開準備（英語・繁体字）
  ☐ MRR ¥20M 達成目標
```

---

*VIRALIZE Product Design Document v1.0 — 2026年3月作成*
