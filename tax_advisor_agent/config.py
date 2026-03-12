"""
設定モジュール
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Anthropic API
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
MODEL = "claude-opus-4-6"

# プロジェクトパス
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

RESEARCH_RESULTS_FILE = DATA_DIR / "subsidy_research.json"
BUSINESS_PROFILE_FILE = DATA_DIR / "business_profile.json"

# スケジューラー設定 (時間間隔)
RESEARCH_INTERVAL_HOURS = 24  # 毎日リサーチ

# 業種リスト
BUSINESS_TYPES = [
    "IT・ソフトウェア",
    "製造業",
    "小売・飲食",
    "農業・水産",
    "建設・不動産",
    "医療・福祉",
    "教育・学習支援",
    "サービス業",
    "運輸・物流",
    "その他",
]

# 青色申告の主要な控除・特典
AOYIRO_FEATURES = {
    "青色申告特別控除": {
        "65万円控除": "電子申告(e-Tax)または電子帳簿保存を行う場合",
        "55万円控除": "複式簿記で記帳する場合",
        "10万円控除": "簡易簿記で記帳する場合",
    },
    "純損失の繰越控除": "赤字を翌年以降3年間繰り越して黒字と相殺",
    "純損失の繰戻し還付": "前年の黒字と相殺して税金の還付を受ける",
    "減価償却の特例": "30万円未満の少額減価償却資産を全額即時償却",
    "家族従業員の給与": "青色事業専従者として給与を経費に計上",
}
