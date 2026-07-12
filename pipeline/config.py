"""パイプライン全体の定数設定(LOOP.md 準拠)。"""
from __future__ import annotations

import os

# --- L1 三重ガード ---
MAX_RETRIES = 3                 # 各ステージのリトライ上限。3回失敗で停止しエスカレーション
CONVERGENCE_THRESHOLD = 0.95    # カットリスト再生成の差分停止しきい値(95%以上同一)
CONVERGENCE_STREAK = 2          # 上記が連続する回数で収束とみなす
BUDGET_JPY = 2000.0             # 1案件あたりのAPIコスト上限(円)。超過で即停止

# --- L2 Maker-Checker ---
# Maker は Sonnet 系、Checker は Opus 系の別エージェント(LOOP.md §4)
MAKER_MODEL = "claude-sonnet-5"
CHECKER_MODEL = "claude-opus-4-8"
MAX_TOKENS = 16000

# APIコスト計算(USD/100万トークン)と円換算レート
PRICES_USD_PER_MTOK = {
    "claude-sonnet-5": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
}
USD_JPY = float(os.environ.get("PIPELINE_USD_JPY", "155"))

# --- QA 基準(S6) ---
LOUDNESS_TARGET_LUFS = -14.0
LOUDNESS_TOLERANCE_LU = 1.0
BLACK_FRAME_MIN_DURATION = 0.1  # blackdetect の最小検出秒数

# --- 音声品質エスカレーション基準(L6) ---
MIN_MEAN_VOLUME_DB = -50.0      # 平均音量がこれ未満なら録音破綻とみなす

# --- L3 パーミッション: 実行を許可する外部ツール ---
ALLOWED_TOOLS = {"ffmpeg", "ffprobe", "whisper", "auto-editor"}

# --- L6 通知 ---
SLACK_WEBHOOK_ENV = "SLACK_WEBHOOK_URL"

# --- ステージ定義 ---
STAGE_ORDER = ["S1", "S2", "S3", "S4", "S5", "S6"]
