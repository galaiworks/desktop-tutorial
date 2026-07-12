"""L4 メモリ: jobs/<job_id>/state.json の管理(LOOP.md §6)。

記録4項目:
  1. 現在ステージと完了ステージ
  2. 中間成果物パス(cutlist.json / telop.json / mix.json)
  3. 消費コスト累計(円)
  4. 直近エラーとリトライ回数

セッションはまっさらで再起動し、state.json から続行する。
"""
from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


def _default_state() -> dict:
    return {
        "current_stage": "S1",
        "completed_stages": [],
        "artifacts": {},            # 例: {"cutlist": "work/cutlist.json", ...}
        "cost_total_jpy": 0.0,
        "last_error": None,         # {"stage": str, "message": str, "retry_count": int}
        "approvals": {},            # S5ゲート: {"preview": bool, "mosaic": bool, "thumbnail": int}
        "convergence": {"streak": 0, "prev_cutlist": None},
        "status": "running",        # running / pending_approval / done / stopped
    }


@dataclass
class State:
    path: Path
    data: dict = field(default_factory=_default_state)

    @classmethod
    def load(cls, job_dir: Path) -> "State":
        path = job_dir / "state.json"
        if path.exists():
            data = _default_state()
            data.update(json.loads(path.read_text(encoding="utf-8")))
            return cls(path=path, data=data)
        return cls(path=path)

    def save(self) -> None:
        """アトミック書き込み(途中クラッシュで state.json を壊さない)。"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    # --- ステージ進行 ---
    def is_completed(self, stage: str) -> bool:
        return stage in self.data["completed_stages"]

    def mark_completed(self, stage: str, next_stage: str | None) -> None:
        if stage not in self.data["completed_stages"]:
            self.data["completed_stages"].append(stage)
        if next_stage:
            self.data["current_stage"] = next_stage
        self.data["last_error"] = None
        self.save()

    # --- 成果物 ---
    def set_artifact(self, name: str, rel_path: str) -> None:
        self.data["artifacts"][name] = rel_path
        self.save()

    # --- コスト ---
    def add_cost(self, jpy: float) -> float:
        self.data["cost_total_jpy"] = round(self.data["cost_total_jpy"] + jpy, 4)
        self.save()
        return self.data["cost_total_jpy"]

    # --- エラー記録 ---
    def record_error(self, stage: str, message: str, retry_count: int) -> None:
        self.data["last_error"] = {
            "stage": stage,
            "message": message[:2000],
            "retry_count": retry_count,
        }
        self.save()
