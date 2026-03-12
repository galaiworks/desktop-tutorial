"""
LINE Webhook サーバー（Flask）

LINE Platform からの Webhook を受信し、MessageHandler に委譲する。
"""
import os
import logging
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    FollowEvent,
    UnfollowEvent,
)

from .message_handler import MessageHandler

logger = logging.getLogger(__name__)

app = Flask(__name__)
handler = WebhookHandler(os.environ.get("LINE_CHANNEL_SECRET", ""))
message_handler = MessageHandler()


@app.route("/webhook", methods=["POST"])
def webhook():
    """LINE Webhook エンドポイント"""
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    logger.debug(f"Webhook received: {body[:200]}")

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature")
        abort(400)
    except Exception as e:
        logger.error(f"Webhook error: {e}", exc_info=True)
        # LINE にはとにかく 200 を返す（リトライ防止）
    return "OK"


@app.route("/health", methods=["GET"])
def health():
    """ヘルスチェックエンドポイント"""
    return {"status": "ok", "service": "tax-advisor-line-bot"}


# ── LINE イベントハンドラー登録 ──────────────────────────

@handler.add(FollowEvent)
def on_follow(event: FollowEvent):
    """友だち追加イベント"""
    try:
        message_handler.handle_follow(event)
    except Exception as e:
        logger.error(f"Follow handler error: {e}", exc_info=True)


@handler.add(UnfollowEvent)
def on_unfollow(event: UnfollowEvent):
    """ブロック・フォロー解除イベント"""
    try:
        message_handler.handle_unfollow(event)
    except Exception as e:
        logger.error(f"Unfollow handler error: {e}", exc_info=True)


@handler.add(MessageEvent, message=TextMessageContent)
def on_text_message(event: MessageEvent):
    """テキストメッセージイベント"""
    try:
        message_handler.handle_text(event)
    except Exception as e:
        logger.error(f"Text handler error: {e}", exc_info=True)


@handler.add(MessageEvent, message=ImageMessageContent)
def on_image_message(event: MessageEvent):
    """画像メッセージイベント（レシートスキャン）"""
    try:
        message_handler.handle_image(event)
    except Exception as e:
        logger.error(f"Image handler error: {e}", exc_info=True)
