"""L6 エスカレーション通知(LOOP.md §7)。

停止して人間(ガライさん)へ通知する。ローカル通知 or Slack webhook。
※ 送るのは通知テキストのみ。素材の外部送信は L3 で禁止。
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import urllib.request

from . import config


def notify(subject: str, body: str) -> None:
    """標準エラー・ローカル通知・Slack webhook の順にベストエフォートで通知する。"""
    print(f"\n=== 通知 ===\n[{subject}]\n{body}\n============", file=sys.stderr)

    # ローカル通知(Linux: notify-send / macOS: osascript)
    try:
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", subject, body], timeout=10, check=False)
        elif shutil.which("osascript"):
            script = f'display notification "{body}" with title "{subject}"'
            subprocess.run(["osascript", "-e", script], timeout=10, check=False)
    except Exception:
        pass

    # Slack webhook(環境変数 SLACK_WEBHOOK_URL 設定時のみ)
    url = os.environ.get(config.SLACK_WEBHOOK_ENV)
    if url:
        try:
            payload = json.dumps({"text": f"*{subject}*\n{body}"}).encode("utf-8")
            req = urllib.request.Request(
                url, data=payload, headers={"Content-Type": "application/json"}
            )
            urllib.request.urlopen(req, timeout=10)
        except Exception as e:
            print(f"Slack通知に失敗しました: {e}", file=sys.stderr)
