# VIRALIZE — AI SNS Growth Platform

**SNS×AIで年商5億円を狙うSaaS。中小企業・個人クリエイター・代理店向けの AI駆動SNS一元管理・自動成長プラットフォーム。**

---

## プロダクト概要

| 指標 | 目標値 |
|:---|:---|
| 年商目標 | **¥500,000,000（5億円）** |
| ターゲット顧客 | **約2,000社** |
| 平均ARPU | **¥20,000/月** |
| 対応プラットフォーム | X・Instagram・TikTok・YouTube・LINE |

### コア機能

1. **AIコンテンツジェネレーター** — Claude APIでSNS投稿文・画像・動画スクリプトを自動生成
2. **バズ予測エンジン** — 投稿前にエンゲージメント率とバズ確率を予測（業界初）
3. **AIエンゲージメントアシスタント** — コメント返信・DM対応・炎上検知を自動化
4. **統合アナリティクス** — ROI・競合比較・コンテンツ診断を一画面で確認

---

## リポジトリ構成

```
.
├── docs/
│   └── VIRALIZE_Product_Design.md   # 詳細プロダクト設計書（収益モデル・技術仕様）
├── viralize/
│   ├── core/
│   │   └── content_generator.py     # AIコンテンツ生成 (Claude API)
│   ├── ml/
│   │   └── buzz_predictor.py        # バズ予測エンジン
│   ├── api/
│   │   └── main.py                  # FastAPI バックエンド
│   └── requirements.txt             # 依存パッケージ
└── README.md
```

---

## クイックスタート

### 必要要件
- Python 3.12+
- Anthropic APIキー

### セットアップ

```bash
# 1. 依存パッケージをインストール
pip install -r viralize/requirements.txt

# 2. 環境変数を設定
export ANTHROPIC_API_KEY="your-api-key-here"

# 3. APIサーバーを起動
uvicorn viralize.api.main:app --reload --port 8000

# 4. APIドキュメントを確認
open http://localhost:8000/docs
```

### AIコンテンツ生成を試す

```python
from viralize.core.content_generator import generate_posts

result = generate_posts(
    brand_context="オーガニックコーヒー専門店。健康意識高い20〜40代がターゲット。",
    campaign_brief="エチオピア産新作スペシャルティコーヒーの発売告知。",
    platform="instagram",
    num_variations=3,
)

for i, post in enumerate(result["posts"], 1):
    print(f"--- パターン{i} ---")
    print(post["caption"])
    print(post["hashtags"])
```

### バズ予測を試す

```python
from viralize.ml.buzz_predictor import BuzzPredictor, PostFeatures

predictor = BuzzPredictor()
features = PostFeatures(
    caption_length=200, hashtag_count=10, emoji_count=5,
    sentiment_score=0.8, hour_of_day=19, day_of_week=5,
    has_image=True, has_video=False, has_link=False,
    follower_count=5000, avg_engagement_rate=0.03,
    trend_keyword_score=0.7, question_mark_count=1, exclamation_count=3,
)

prediction = predictor.predict(features, platform="instagram")
print(f"予測エンゲージメント率: {prediction.predicted_engagement_rate}%")
print(f"バズ確率: {prediction.buzz_probability}%")
print(f"提案: {prediction.recommendation}")
```

---

## 収益モデル

| プラン | 月額 | 対象 |
|:---|:---|:---|
| Starter | ¥9,800 | 個人・スモールビジネス |
| Business | ¥29,800 | 中小企業・EC |
| Agency | ¥98,000 | 代理店 |
| Enterprise | ¥298,000〜 | 大手企業 |

**年商5億円の試算**: 2,030社 × 平均¥20,000/月 × 12ヶ月 + 従量課金 ≒ **¥501,440,000**

詳細は [docs/VIRALIZE_Product_Design.md](docs/VIRALIZE_Product_Design.md) を参照。

---

## 技術スタック

| レイヤー | 採用技術 |
|:---|:---|
| AI生成 | Anthropic Claude API (claude-sonnet-4-6) |
| 画像生成 | OpenAI DALL-E 3 |
| バックエンド | Python FastAPI |
| フロントエンド | Next.js 15 + TypeScript |
| ML予測 | XGBoost + PyTorch |
| インフラ | AWS ECS Fargate + RDS + ElastiCache |

---

## ライセンス

MIT License
