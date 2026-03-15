"""
VIRALIZE — FastAPI バックエンド
SNS×AI自動化プラットフォームのRESTful API
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional
import os

# ローカルモジュール（実運用時はパッケージとしてインポート）
# from viralize.core.content_generator import generate_posts, analyze_brand_content, generate_reply
# from viralize.ml.buzz_predictor import BuzzPredictor, PostFeatures

app = FastAPI(
    title="VIRALIZE API",
    description="SNS×AI自動化プラットフォーム — コンテンツ生成・バズ予測・エンゲージメント管理",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.viralize.jp", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── リクエスト / レスポンスモデル ──────────────────────────────────────────

class GeneratePostRequest(BaseModel):
    brand_context: str = Field(..., description="ブランドの説明（業種・商品・ターゲット等）", min_length=10)
    campaign_brief: str = Field(..., description="キャンペーンの目的・訴求内容", min_length=10)
    platform: Literal["instagram", "x_twitter", "tiktok", "youtube", "line"]
    brand_voice_examples: Optional[list[str]] = Field(default=None, description="過去の人気投稿例（最大5件）")
    num_variations: int = Field(default=3, ge=1, le=5, description="生成するバリエーション数")

    class Config:
        json_schema_extra = {
            "example": {
                "brand_context": "オーガニックコーヒー専門店。20〜40代の健康意識高い男女がターゲット。",
                "campaign_brief": "エチオピア産新作スペシャルティコーヒーの発売告知。明るくポップなトーン。",
                "platform": "instagram",
                "num_variations": 3,
            }
        }


class GeneratePostResponse(BaseModel):
    platform: str
    posts: list[dict]
    usage: dict


class BuzzPredictRequest(BaseModel):
    caption: str = Field(..., description="投稿本文")
    hashtags: list[str] = Field(default=[], description="ハッシュタグリスト")
    platform: Literal["instagram", "x_twitter", "tiktok", "youtube", "line"]
    has_image: bool = False
    has_video: bool = False
    has_link: bool = False
    hour_of_day: int = Field(default=19, ge=0, le=23, description="投稿予定時刻")
    day_of_week: int = Field(default=4, ge=0, le=6, description="曜日 (0=月〜6=日)")
    follower_count: int = Field(default=1000, ge=0)
    avg_engagement_rate: float = Field(default=0.02, ge=0.0, le=1.0, description="過去平均エンゲージメント率")
    trend_keyword_score: float = Field(default=0.5, ge=0.0, le=1.0)


class AnalyzeRequest(BaseModel):
    post_history: list[dict] = Field(..., description="過去投稿データのリスト")
    competitor_data: Optional[list[dict]] = Field(default=None, description="競合アカウントデータ")


class GenerateReplyRequest(BaseModel):
    original_comment: str = Field(..., description="返信対象のコメント")
    brand_context: str = Field(..., description="ブランドの説明")
    sentiment: Literal["positive", "neutral", "negative", "question"]


# ── エンドポイント ──────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "VIRALIZE API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {"status": "healthy", "anthropic_api": "connected" if os.getenv("ANTHROPIC_API_KEY") else "not configured"}


@app.post("/api/v1/posts/generate", response_model=GeneratePostResponse)
async def generate_post_endpoint(request: GeneratePostRequest):
    """
    AIによるSNS投稿文の自動生成

    - Claude APIを使用してブランドに最適化された投稿を複数パターン生成
    - プラットフォームごとの文字数・ハッシュタグ制限に自動対応
    - ブランドボイスの学習に対応（過去投稿例を渡すことでトーン最適化）
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY が設定されていません")

    try:
        # from viralize.core.content_generator import generate_posts
        # result = generate_posts(...)
        # ↑ 実装済みの generate_posts() を呼び出す

        # デモ用モックレスポンス（API統合前の動作確認用）
        result = {
            "platform": request.platform,
            "posts": [
                {
                    "caption": f"【{request.platform.upper()}向けサンプル投稿】\n{request.campaign_brief[:50]}...",
                    "hashtags": ["#サンプル", "#VIRALIZE"],
                    "alt_text": "商品の画像",
                    "emotion_target": "ワクワク感・購買欲",
                    "cta": "プロフのリンクをチェック！",
                    "best_post_hour": 19,
                }
            ] * request.num_variations,
            "usage": {"input_tokens": 0, "output_tokens": 0},
        }
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"コンテンツ生成エラー: {str(e)}")


@app.post("/api/v1/posts/predict-buzz")
async def predict_buzz_endpoint(request: BuzzPredictRequest):
    """
    投稿のバズ予測スコアを返す

    - 投稿前にエンゲージメント率とバズ確率を予測
    - 改善提案と最適投稿時間を提示
    """
    try:
        # from viralize.ml.buzz_predictor import BuzzPredictor, PostFeatures
        # predictor = BuzzPredictor()
        # features = PostFeatures(...)
        # prediction = predictor.predict(features, request.platform)

        # デモ用モックレスポンス
        prediction = {
            "predicted_engagement_rate": 3.8,
            "buzz_probability": 63.3,
            "confidence": "medium",
            "recommendation": "投稿時間を19:00頃に変更するとさらに効果的です",
            "optimal_post_time": "19:00 に投稿するとエンゲージメント+71%が期待できます",
            "score_breakdown": {
                "timing": 0.175,
                "media": 0.22,
                "hashtags": 0.165,
                "sentiment": 0.10,
                "history": 0.20,
                "trend": 0.13,
            },
        }
        return prediction

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"予測エラー: {str(e)}")


@app.post("/api/v1/content/analyze")
async def analyze_content_endpoint(request: AnalyzeRequest):
    """
    投稿履歴の分析とコンテンツ戦略提案

    - 高エンゲージメント投稿のパターン分析
    - 最適投稿時間帯・コンテンツカテゴリの提案
    - 競合との差別化ポイント抽出
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY が設定されていません")

    if len(request.post_history) < 3:
        raise HTTPException(status_code=400, detail="分析には最低3件以上の投稿履歴が必要です")

    try:
        # from viralize.core.content_generator import analyze_brand_content
        # result = analyze_brand_content(request.post_history, request.competitor_data)
        return {"message": "分析機能は実装中です。/docs で最新仕様を確認してください。"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析エラー: {str(e)}")


@app.post("/api/v1/engagement/reply")
async def generate_reply_endpoint(request: GenerateReplyRequest):
    """
    コメントへのAI返信文を自動生成

    - ポジティブ/ネガティブ/質問を判定し、最適なトーンで返信
    - 3パターンの返信案を提示
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(status_code=503, detail="ANTHROPIC_API_KEY が設定されていません")

    try:
        # from viralize.core.content_generator import generate_reply
        # result = generate_reply(...)
        return {
            "replies": [
                "ありがとうございます！今後ともよろしくお願いします🙏",
                "嬉しいお言葉ありがとうございます✨ またぜひご利用ください！",
                "ご支持いただき、とても励みになります！引き続きよろしくお願いします😊",
            ],
            "sentiment": request.sentiment,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"返信生成エラー: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
