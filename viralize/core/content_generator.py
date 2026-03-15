"""
VIRALIZE — AIコンテンツジェネレーター
Claude APIを使用してSNS投稿文を自動生成する
"""

import json
from typing import Literal
from anthropic import Anthropic

client = Anthropic()

Platform = Literal["instagram", "x_twitter", "tiktok", "youtube", "line"]

PLATFORM_SPECS: dict[Platform, dict] = {
    "instagram": {
        "max_chars": 2200,
        "hashtag_limit": 30,
        "tone": "ビジュアル重視・エモーショナル",
        "tips": "改行を多用し、絵文字でテンポよく。最初の2行でフックを作る。",
    },
    "x_twitter": {
        "max_chars": 140,
        "hashtag_limit": 2,
        "tone": "簡潔・インパクト重視",
        "tips": "数字・疑問形・意外性で冒頭を引き込む。リプライ誘発ワードを使う。",
    },
    "tiktok": {
        "max_chars": 300,
        "hashtag_limit": 8,
        "tone": "トレンド重視・若者言葉OK",
        "tips": "#fyp #foryou を必ず含める。動画への興味を引く一言コメントを添える。",
    },
    "youtube": {
        "max_chars": 5000,
        "hashtag_limit": 15,
        "tone": "SEO最適化・情報提供型",
        "tips": "冒頭にキーワードを含む。タイムスタンプ・リンクも記載する。",
    },
    "line": {
        "max_chars": 500,
        "hashtag_limit": 0,
        "tone": "フレンドリー・行動促進",
        "tips": "短文で改行多用。絵文字でテンション上げる。CTAボタンと連動させる。",
    },
}


def generate_posts(
    brand_context: str,
    campaign_brief: str,
    platform: Platform,
    brand_voice_examples: list[str] | None = None,
    num_variations: int = 3,
) -> dict:
    """
    ブランドコンテキストとキャンペーン情報からSNS投稿文を生成する

    Args:
        brand_context: ブランドの説明（業種・商品・ターゲット等）
        campaign_brief: キャンペーンの目的・訴求内容
        platform: 投稿先プラットフォーム
        brand_voice_examples: 過去の人気投稿例（ブランドボイス学習用）
        num_variations: 生成するバリエーション数（デフォルト3）

    Returns:
        生成された投稿候補のリストと使用トークン数
    """
    spec = PLATFORM_SPECS[platform]

    examples_section = ""
    if brand_voice_examples:
        examples_section = "\n\n【過去の人気投稿例（ブランドボイスの参考）】\n"
        examples_section += "\n---\n".join(brand_voice_examples[:5])

    system_prompt = f"""あなたはSNSマーケティングの専門家です。
日本のSNS文化・トレンドに精通しており、エンゲージメントを最大化する投稿文を作成できます。

【プラットフォーム仕様】
- プラットフォーム: {platform}
- 文字数上限: {spec['max_chars']}文字
- ハッシュタグ数: {spec['hashtag_limit']}個以内
- トーン: {spec['tone']}
- コツ: {spec['tips']}
{examples_section}

必ず以下のJSON配列形式で{num_variations}パターン返答してください。余分なテキストは不要です:
[
  {{
    "caption": "投稿本文（改行は\\nで表現）",
    "hashtags": ["#タグ1", "#タグ2"],
    "alt_text": "画像の説明（アクセシビリティ用、50文字以内）",
    "emotion_target": "読者に期待する感情反応",
    "cta": "コール・トゥ・アクション（例: プロフのリンクをチェック！）",
    "best_post_hour": 19
  }}
]"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"""以下の情報をもとに{platform}用の投稿を{num_variations}パターン生成してください。

【ブランド情報】
{brand_context}

【キャンペーン内容】
{campaign_brief}""",
            }
        ],
    )

    raw_text = message.content[0].text
    try:
        posts = json.loads(raw_text)
    except json.JSONDecodeError:
        # JSON抽出のフォールバック
        import re
        json_match = re.search(r"\[.*\]", raw_text, re.DOTALL)
        posts = json.loads(json_match.group()) if json_match else []

    return {
        "platform": platform,
        "posts": posts,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
    }


def analyze_brand_content(
    post_history: list[dict],
    competitor_data: list[dict] | None = None,
) -> dict:
    """
    過去の投稿履歴と競合データからコンテンツ戦略を分析・提案する

    Args:
        post_history: 過去投稿データのリスト（caption, engagement_rate, posted_at等）
        competitor_data: 競合アカウントのデータ（任意）

    Returns:
        AI分析レポートと戦略提案
    """
    competitor_section = ""
    if competitor_data:
        competitor_section = f"\n\n【競合データ】\n{json.dumps(competitor_data[:5], ensure_ascii=False, indent=2)}"

    prompt = f"""以下のSNSデータを分析し、エンゲージメントを最大化するための戦略を提案してください。

【自社投稿履歴（直近）】
{json.dumps(post_history[:20], ensure_ascii=False, indent=2)}
{competitor_section}

以下の構成でMarkdownレポートを作成してください:
1. **高エンゲージメント投稿の共通パターン**（箇条書き5点）
2. **最適な投稿時間帯・曜日**（具体的な時刻を提示）
3. **効果的なコンテンツカテゴリ TOP5**（エンゲージメント率順）
4. **改善が必要な点**（具体的な改善案付き）
5. **次の30日間 コンテンツカレンダー提案**（週次テーマ）
"""

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "analysis_report": message.content[0].text,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
    }


def generate_reply(
    original_comment: str,
    brand_context: str,
    sentiment: Literal["positive", "neutral", "negative", "question"],
) -> dict:
    """
    コメントへの返信文を自動生成する（エンゲージメントアシスタント）

    Args:
        original_comment: 返信対象のコメント文
        brand_context: ブランドの説明
        sentiment: コメントの感情分類

    Returns:
        返信案3パターン
    """
    tone_guide = {
        "positive": "感謝を込めて温かく、ブランドへの好意を強化する返信",
        "neutral": "親しみやすく、会話を広げる返信",
        "negative": "誠実に謝罪・改善を伝え、信頼を回復する返信",
        "question": "丁寧に質問に答え、必要であれば詳細への誘導を含む返信",
    }

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        messages=[
            {
                "role": "user",
                "content": f"""ブランド: {brand_context}
コメント（{sentiment}）: {original_comment}
指針: {tone_guide[sentiment]}

50文字以内の返信を3パターン、JSON配列で返してください:
["返信1", "返信2", "返信3"]""",
            }
        ],
    )

    raw = message.content[0].text
    try:
        replies = json.loads(raw)
    except json.JSONDecodeError:
        replies = [message.content[0].text]

    return {"replies": replies, "sentiment": sentiment}
