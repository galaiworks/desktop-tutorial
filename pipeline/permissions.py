"""L3 パーミッションガード(LOOP.md §5)。

自動許可: jobs/<job_id>/ 配下の読み書き、ffmpeg/whisper/auto-editor の実行、assets/ の読み取り
禁止:     jobs/ 外への書き込み、job.yaml の書き換え、素材の外部送信・外部取得
"""
from __future__ import annotations

from pathlib import Path

from . import config
from .errors import PermissionViolation


class Sandbox:
    """1案件分のファイルアクセス境界。すべての書き込みはここを通す。"""

    def __init__(self, job_dir: Path, assets_dir: Path):
        self.job_dir = job_dir.resolve()
        self.assets_dir = assets_dir.resolve()
        self.job_yaml = self.job_dir / "job.yaml"

    # --- 書き込み ---
    def writable(self, path: Path | str) -> Path:
        """jobs/<job_id>/ 配下のみ書き込み可。job.yaml は書き換え禁止。"""
        p = Path(path)
        resolved = (self.job_dir / p).resolve() if not p.is_absolute() else p.resolve()
        if not resolved.is_relative_to(self.job_dir):
            raise PermissionViolation(f"jobs/ 外への書き込みは禁止です: {resolved}")
        if resolved == self.job_yaml:
            raise PermissionViolation("job.yaml の書き換えは禁止です")
        resolved.parent.mkdir(parents=True, exist_ok=True)
        return resolved

    # --- 読み取り ---
    def readable(self, path: Path | str) -> Path:
        """jobs/<job_id>/ と assets/ のみ読み取り可。"""
        resolved = Path(path).resolve()
        if resolved.is_relative_to(self.job_dir) or resolved.is_relative_to(self.assets_dir):
            return resolved
        raise PermissionViolation(f"読み取りが許可されていないパスです: {resolved}")

    # --- 外部ツール実行 ---
    @staticmethod
    def check_tool(cmd: list[str]) -> None:
        """許可リスト(ffmpeg/ffprobe/whisper/auto-editor)以外の実行を拒否。"""
        if not cmd:
            raise PermissionViolation("空のコマンドは実行できません")
        tool = Path(cmd[0]).name
        if tool not in config.ALLOWED_TOOLS:
            raise PermissionViolation(f"許可されていないツールです: {tool}")
