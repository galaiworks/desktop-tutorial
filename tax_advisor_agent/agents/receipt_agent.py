"""
レシートOCRエージェント

Claude Vision を使ってレシート画像から支出情報を抽出し、
個人費・事業費の自動分類まで行う。
"""
import base64
import json
import re
from datetime import date
import anthropic

from ..config import MODEL
from ..models import AgentResponse

SYSTEM_PROMPT = """あなたはレシート・領収書読み取りの専門エージェントです。
画像からレシート情報を正確に抽出し、JSON形式で返します。

## 抽出ルール
1. 日付: レシートの日付（不明なら今日の日付）
2. 店舗名: 店名・会社名
3. 合計金額: 税込合計（円）
4. 消費税額: 税額（記載がなければ推定）
5. 明細: 商品名・金額のリスト
6. カテゴリ推定: food/dining/transport/utility/communication/medical/
   education/entertainment/clothing/equipment/software/advertising/office/rent/insurance/other

## 出力フォーマット (必ずこのJSONのみ返す)
```json
{
  "date": "YYYY-MM-DD",
  "store_name": "店舗名",
  "total_amount": 1000,
  "tax_amount": 90,
  "category": "food",
  "items": [
    {"name": "商品名", "amount": 500, "quantity": 1},
    {"name": "商品名2", "amount": 500, "quantity": 2}
  ],
  "confidence": 0.95,
  "notes": "特記事項があれば（不明瞭な箇所など）"
}
```

判読不能な場合は confidence を低く（0.5以下）し notes に理由を記載してください。"""

CLASSIFIER_SYSTEM = """あなたは個人事業主の支出を「個人費」「事業費」「混在（按分必要）」に分類する専門家です。

## 判断基準

### 事業費 (business) になるもの
- 仕事で使う消耗品・文具・事務用品
- 業務用ソフトウェア・クラウドサービス
- 取引先との会食・接待（名目が業務上のもの）
- 業務に使う書籍・セミナー・研修費
- 仕事用の交通費（出張・訪問）
- 仕事場の家賃・光熱費（事業専用部分）
- 広告宣伝費・集客費

### 個人費 (personal) になるもの
- 日常の食料品・日用品（業務用でないもの）
- 個人の衣類・趣味・娯楽
- 家族向けの支出
- プライベートの旅行・外食

### 混在 (mixed) になるもの
- 自宅兼事務所の光熱費・通信費（按分が必要）
- 個人用と業務用を兼ねる機器（PC・スマートフォンなど）
- 業務とプライベートが混在する外食

## 出力フォーマット
```json
{
  "expense_type": "business|personal|mixed",
  "business_ratio": 0.0〜1.0,
  "reason": "判断理由（日本語・簡潔に）",
  "tax_deductible": true|false,
  "notes": "申告時の注意点"
}
```"""


class ReceiptAgent:
    """レシートOCRエージェント"""

    def __init__(self):
        self.client = anthropic.Anthropic()
        self.name = "レシートOCR"

    def extract_from_image(
        self,
        image_data: bytes,
        media_type: str = "image/jpeg",
        business_type: str = "",
    ) -> AgentResponse:
        """
        レシート画像から情報を抽出する。

        Args:
            image_data: 画像バイナリ
            media_type: "image/jpeg" | "image/png" | "image/webp"
            business_type: 事業者の業種（分類精度向上に使用）
        """
        image_b64 = base64.standard_b64encode(image_data).decode()

        hint = f"\n事業者の業種: {business_type}" if business_type else ""
        user_content = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": media_type,
                    "data": image_b64,
                },
            },
            {
                "type": "text",
                "text": f"このレシート・領収書から情報を抽出してJSON形式で返してください。{hint}",
            },
        ]

        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=2048,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return AgentResponse(
                agent_name=self.name,
                content=text,
                success=True,
            )
        except anthropic.APIError as e:
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                error=str(e),
            )

    def classify_expense(
        self,
        receipt_data: dict,
        business_type: str = "",
        user_note: str = "",
    ) -> AgentResponse:
        """
        抽出済みレシートデータを個人費/事業費に分類する。

        Args:
            receipt_data: extract_from_image() で得た辞書
            business_type: 事業者の業種
            user_note: ユーザーからの補足（"接待だった" など）
        """
        items_text = "\n".join(
            f"  - {item['name']}: {item['amount']}円"
            for item in receipt_data.get("items", [])
        )
        prompt = f"""
以下のレシートを個人費・事業費・混在に分類してください。

店舗: {receipt_data.get('store_name', '不明')}
カテゴリ: {receipt_data.get('category', '不明')}
合計: {receipt_data.get('total_amount', 0):,}円
明細:
{items_text or '  （明細なし）'}
事業者業種: {business_type or '不明'}
ユーザーメモ: {user_note or 'なし'}
"""
        try:
            response = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=CLASSIFIER_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            text = next(
                (b.text for b in response.content if b.type == "text"), ""
            )
            return AgentResponse(
                agent_name=self.name,
                content=text,
                success=True,
            )
        except anthropic.APIError as e:
            return AgentResponse(
                agent_name=self.name,
                content="",
                success=False,
                error=str(e),
            )

    def process_receipt_image(
        self,
        image_data: bytes,
        business_type: str = "",
        user_note: str = "",
        media_type: str = "image/jpeg",
    ) -> dict:
        """
        レシート画像の一括処理（OCR + 分類）。
        辞書形式で結果を返す。
        """
        today = date.today().isoformat()

        # Step 1: OCR
        ocr_response = self.extract_from_image(image_data, media_type, business_type)
        if not ocr_response.success:
            return {
                "success": False,
                "error": ocr_response.error,
                "date": today,
                "store_name": "",
                "total_amount": 0,
                "category": "other",
                "expense_type": "personal",
                "business_ratio": 0.0,
                "items": [],
            }

        receipt_data = _parse_json_from_text(ocr_response.content)
        if not receipt_data:
            return {
                "success": False,
                "error": "レシート読み取り失敗（画像が不鮮明かもしれません）",
                "date": today,
                "store_name": "",
                "total_amount": 0,
                "category": "other",
                "expense_type": "personal",
                "business_ratio": 0.0,
                "items": [],
            }

        # Step 2: 分類
        classify_response = self.classify_expense(
            receipt_data, business_type, user_note
        )
        classify_data = {}
        if classify_response.success:
            classify_data = _parse_json_from_text(classify_response.content) or {}

        return {
            "success": True,
            "date": receipt_data.get("date", today),
            "store_name": receipt_data.get("store_name", ""),
            "total_amount": int(receipt_data.get("total_amount", 0)),
            "tax_amount": int(receipt_data.get("tax_amount", 0)),
            "category": receipt_data.get("category", "other"),
            "expense_type": classify_data.get("expense_type", "personal"),
            "business_ratio": float(classify_data.get("business_ratio", 0.0)),
            "classification_reason": classify_data.get("reason", ""),
            "tax_deductible": classify_data.get("tax_deductible", False),
            "notes": classify_data.get("notes", ""),
            "items": receipt_data.get("items", []),
            "confidence": receipt_data.get("confidence", 0.9),
            "ocr_notes": receipt_data.get("notes", ""),
        }


def _parse_json_from_text(text: str) -> dict | None:
    """テキストから JSON ブロックを抽出してパース"""
    # ```json ... ``` ブロックを探す
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    # プレーン JSON を試みる
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None
