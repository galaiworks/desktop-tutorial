"""1案件分の実行コンテキスト。job.yaml(読み取り専用)と各ガードを束ねる。"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from .budget import Budget
from .errors import PipelineError
from .llm import LLMClient
from .permissions import Sandbox
from .state import State

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"


class JobContext:
    def __init__(self, job_dir: Path):
        self.job_dir = job_dir.resolve()
        job_yaml = self.job_dir / "job.yaml"
        if not job_yaml.exists():
            raise PipelineError(f"job.yaml が見つかりません: {job_yaml}")
        self.job: dict = yaml.safe_load(job_yaml.read_text(encoding="utf-8"))
        self.job_id: str = self.job.get("job_id", self.job_dir.name)

        self.sandbox = Sandbox(self.job_dir, ASSETS_DIR)
        self.state = State.load(self.job_dir)
        self.budget = Budget(self.state)
        self._llm: LLMClient | None = None

        # 作業ディレクトリ
        self.work_dir = self.job_dir / "work"
        self.logs_dir = self.job_dir / "logs"
        self.output_dir = self.job_dir / "output"
        self.preview_dir = self.job_dir / "preview"

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = LLMClient(self.budget)
        return self._llm

    # --- 成果物の読み書き(すべて sandbox 経由) ---
    def write_json(self, rel_path: str, data: dict | list) -> Path:
        path = self.sandbox.writable(self.job_dir / rel_path)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return path

    def read_json(self, rel_path: str) -> dict:
        path = self.sandbox.readable(self.job_dir / rel_path)
        return json.loads(path.read_text(encoding="utf-8"))

    def artifact_path(self, name: str) -> Path:
        rel = self.state.data["artifacts"].get(name)
        if rel is None:
            raise PipelineError(f"成果物 {name} が state.json に記録されていません")
        return self.sandbox.readable(self.job_dir / rel)

    def source_path(self) -> Path:
        """素材(assets/ 配下、読み取り専用)。"""
        rel = self.job.get("source")
        if not rel:
            raise PipelineError("job.yaml に source が指定されていません")
        return self.sandbox.readable(REPO_ROOT / rel)
