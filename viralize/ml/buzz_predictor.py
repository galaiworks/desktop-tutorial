"""
VIRALIZE — バズ予測エンジン
投稿前にエンゲージメント率とバズ確率を予測する
"""

import numpy as np
from dataclasses import dataclass


@dataclass
class PostFeatures:
    """投稿の特徴量"""
    caption_length: int          # 投稿文字数
    hashtag_count: int           # ハッシュタグ数
    emoji_count: int             # 絵文字数
    sentiment_score: float       # 感情スコア (-1.0 〜 1.0)
    hour_of_day: int             # 投稿時間 (0〜23)
    day_of_week: int             # 曜日 (0=月曜〜6=日曜)
    has_image: bool              # 画像添付フラグ
    has_video: bool              # 動画添付フラグ
    has_link: bool               # URLリンクフラグ
    follower_count: int          # アカウントのフォロワー数
    avg_engagement_rate: float   # 過去投稿の平均エンゲージメント率
    trend_keyword_score: float   # トレンドキーワード含有スコア (0〜1.0)
    question_mark_count: int     # 「？」の数（会話誘発）
    exclamation_count: int       # 「！」の数（感情強調）


@dataclass
class BuzzPrediction:
    """バズ予測結果"""
    predicted_engagement_rate: float   # 予測エンゲージメント率 (%)
    buzz_probability: float            # バズ確率 (%)
    confidence: str                    # 信頼度: "high" | "medium" | "low"
    recommendation: str               # 改善提案
    optimal_post_time: str            # 最適投稿時間の提案
    score_breakdown: dict             # スコア内訳


class BuzzPredictor:
    """
    投稿コンテンツのエンゲージメント予測モデル

    実装方針:
    - MVP段階ではルールベース + 重み付きスコアリングで予測
    - 顧客データが蓄積されたらXGBoost/LightGBMモデルに置換
    - A/Bテスト結果を継続的に学習に反映

    特徴量の重要度 (事前調査ベース):
    1. 投稿時間帯: 0.25
    2. メディアタイプ(画像/動画): 0.20
    3. エンゲージメント履歴: 0.20
    4. ハッシュタグ最適化: 0.15
    5. テキスト感情スコア: 0.10
    6. トレンドキーワード: 0.10
    """

    # プラットフォーム別 最適投稿時間帯 (エンゲージメント調査ベース)
    OPTIMAL_HOURS = {
        "instagram": [7, 8, 12, 18, 19, 21],
        "x_twitter": [7, 8, 12, 17, 18, 20, 22],
        "tiktok":    [6, 10, 19, 20, 21, 22, 23],
        "youtube":   [14, 15, 16, 17, 20, 21],
        "line":      [7, 12, 19, 20, 21],
    }

    # 曜日別エンゲージメント係数 (月=0, 日=6)
    DAY_MULTIPLIERS = [0.90, 0.92, 0.95, 0.97, 1.05, 1.10, 1.08]

    def predict(self, features: PostFeatures, platform: str = "instagram") -> BuzzPrediction:
        """
        投稿の特徴量からエンゲージメント予測とバズ確率を算出する

        Args:
            features: PostFeaturesデータクラス
            platform: 対象プラットフォーム

        Returns:
            BuzzPredictionデータクラス
        """
        scores = self._calculate_scores(features, platform)
        total_score = sum(scores.values())

        # 予測エンゲージメント率: ベースレート × 総合スコア
        base_rate = min(features.avg_engagement_rate * 100, 8.0)  # 最大8%
        base_rate = max(base_rate, 0.5)  # 最小0.5%
        predicted_engagement = base_rate * total_score

        # バズ確率: エンゲージメント率3%以上をバズと定義
        buzz_threshold = 3.0
        buzz_probability = min((predicted_engagement / buzz_threshold) * 50, 95.0)
        buzz_probability = max(buzz_probability, 5.0)

        # 信頼度判定
        history_confidence = features.follower_count > 1000 and features.avg_engagement_rate > 0
        confidence = "high" if history_confidence else "medium" if features.follower_count > 100 else "low"

        return BuzzPrediction(
            predicted_engagement_rate=round(predicted_engagement, 2),
            buzz_probability=round(buzz_probability, 1),
            confidence=confidence,
            recommendation=self._generate_recommendation(features, scores, platform),
            optimal_post_time=self._suggest_post_time(features, platform),
            score_breakdown={k: round(v, 3) for k, v in scores.items()},
        )

    def _calculate_scores(self, f: PostFeatures, platform: str) -> dict[str, float]:
        """各特徴量のスコアを計算（合計が1.0に近いほど平均的パフォーマンス）"""
        scores = {}

        # 1. 投稿時間スコア (重み: 0.25)
        optimal_hours = self.OPTIMAL_HOURS.get(platform, self.OPTIMAL_HOURS["instagram"])
        time_score = 1.2 if f.hour_of_day in optimal_hours else 0.7
        day_multiplier = self.DAY_MULTIPLIERS[f.day_of_week % 7]
        scores["timing"] = time_score * day_multiplier * 0.25

        # 2. メディアスコア (重み: 0.20)
        if f.has_video:
            media_score = 1.4  # 動画は最もエンゲージメント高い
        elif f.has_image:
            media_score = 1.1
        else:
            media_score = 0.7  # テキストのみ
        scores["media"] = media_score * 0.20

        # 3. ハッシュタグスコア (重み: 0.15)
        # プラットフォームごとの最適ハッシュタグ数
        optimal_hashtag_ranges = {
            "instagram": (5, 15), "x_twitter": (1, 2), "tiktok": (3, 8),
            "youtube": (5, 10), "line": (0, 0),
        }
        min_h, max_h = optimal_hashtag_ranges.get(platform, (3, 10))
        if min_h <= f.hashtag_count <= max_h:
            hashtag_score = 1.1
        elif f.hashtag_count < min_h:
            hashtag_score = 0.8
        else:
            hashtag_score = 0.85  # 多すぎるとスパム判定リスク
        scores["hashtags"] = hashtag_score * 0.15

        # 4. テキスト感情スコア (重み: 0.10)
        # ポジティブ感情は全般的にエンゲージメント高め
        sentiment_multiplier = 1.0 + (f.sentiment_score * 0.3)
        scores["sentiment"] = sentiment_multiplier * 0.10

        # 5. エンゲージメント履歴スコア (重み: 0.20)
        history_score = min(f.avg_engagement_rate * 20, 1.5)  # 最大1.5倍
        history_score = max(history_score, 0.3)
        scores["history"] = history_score * 0.20

        # 6. トレンドスコア (重み: 0.10)
        scores["trend"] = (1.0 + f.trend_keyword_score * 0.5) * 0.10

        return scores

    def _generate_recommendation(
        self, features: PostFeatures, scores: dict, platform: str
    ) -> str:
        """スコアに基づく具体的な改善提案を生成"""
        recommendations = []
        optimal_hours = self.OPTIMAL_HOURS.get(platform, [])

        if features.hour_of_day not in optimal_hours:
            best_hour = optimal_hours[len(optimal_hours) // 2] if optimal_hours else 19
            recommendations.append(f"投稿時間を{best_hour}:00頃に変更すると効果的です")

        if not features.has_image and not features.has_video:
            recommendations.append("画像または動画を追加するとエンゲージメントが約40%向上します")

        if features.sentiment_score < 0:
            recommendations.append("より前向きなトーンに変更するとシェア率が上がります")

        if features.trend_keyword_score < 0.3:
            recommendations.append("現在のトレンドキーワードをハッシュタグに追加してください")

        if not recommendations:
            return "投稿内容は最適化されています。このまま投稿を推奨します。"

        return " / ".join(recommendations)

    def _suggest_post_time(self, features: PostFeatures, platform: str) -> str:
        """現在設定時間が最適でない場合、次の最適時間を提案"""
        optimal_hours = self.OPTIMAL_HOURS.get(platform, [19, 20, 21])
        if features.hour_of_day in optimal_hours:
            return f"現在の時間帯（{features.hour_of_day}:00）は最適です"

        # 次に近い最適時間を探す
        next_optimal = min(optimal_hours, key=lambda h: (h - features.hour_of_day) % 24)
        return f"{next_optimal}:00 に投稿するとエンゲージメント+{int((1.2/0.7 - 1) * 100)}%が期待できます"
