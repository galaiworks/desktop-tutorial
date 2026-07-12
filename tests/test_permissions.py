"""L3 パーミッションガードのテスト。"""
import pytest

from pipeline.errors import PermissionViolation
from pipeline.permissions import Sandbox


@pytest.fixture
def sandbox(tmp_path):
    job_dir = tmp_path / "jobs" / "job1"
    assets_dir = tmp_path / "assets"
    job_dir.mkdir(parents=True)
    assets_dir.mkdir()
    (job_dir / "job.yaml").write_text("job_id: job1\n", encoding="utf-8")
    return Sandbox(job_dir, assets_dir)


class TestWrite:
    def test_write_inside_job_dir_allowed(self, sandbox):
        p = sandbox.writable(sandbox.job_dir / "work" / "cutlist.json")
        assert p.parent.exists()

    def test_write_outside_job_dir_denied(self, sandbox, tmp_path):
        with pytest.raises(PermissionViolation):
            sandbox.writable(tmp_path / "outside.txt")

    def test_write_to_assets_denied(self, sandbox):
        """素材ディレクトリへの書き込みは禁止(読み取り専用)。"""
        with pytest.raises(PermissionViolation):
            sandbox.writable(sandbox.assets_dir / "hack.mp4")

    def test_path_traversal_denied(self, sandbox):
        with pytest.raises(PermissionViolation):
            sandbox.writable(sandbox.job_dir / ".." / ".." / "etc" / "passwd")

    def test_job_yaml_rewrite_denied(self, sandbox):
        """job.yaml の書き換えは禁止(L3)。"""
        with pytest.raises(PermissionViolation):
            sandbox.writable(sandbox.job_dir / "job.yaml")


class TestRead:
    def test_read_job_dir_allowed(self, sandbox):
        assert sandbox.readable(sandbox.job_dir / "job.yaml")

    def test_read_assets_allowed(self, sandbox):
        assert sandbox.readable(sandbox.assets_dir / "bgm.mp3")

    def test_read_outside_denied(self, sandbox):
        with pytest.raises(PermissionViolation):
            sandbox.readable("/etc/passwd")


class TestTools:
    def test_allowed_tools(self):
        for tool in ("ffmpeg", "ffprobe", "whisper", "auto-editor"):
            Sandbox.check_tool([tool, "-v"])

    def test_disallowed_tool_denied(self):
        with pytest.raises(PermissionViolation):
            Sandbox.check_tool(["curl", "https://example.com/bgm.mp3"])

    def test_disallowed_tool_with_path_denied(self):
        with pytest.raises(PermissionViolation):
            Sandbox.check_tool(["/usr/bin/rsync", "material.mp4", "remote:"])

    def test_empty_command_denied(self):
        with pytest.raises(PermissionViolation):
            Sandbox.check_tool([])
