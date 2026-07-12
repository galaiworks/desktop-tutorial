"""S1→S6 のエンドツーエンド統合テスト。

メディア処理(ffmpeg/whisper)と LLM 呼び出しをモック化し、
オーケストレーションのフロー(エスカレーション→承認→ゲート→完了)を検証する。
"""
import shutil

import pytest
import yaml

import pipeline.context as context_mod
import pipeline.media as media
from pipeline.context import JobContext
from pipeline.run import run_pipeline

# --- フィクスチャ: 疑似案件 ---

TRANSCRIPT = {
    "segments": [
        {"start": 0.0, "end": 300.0, "text": "本日はセミナーにお越しいただき"},
        {"start": 300.0, "end": 640.0, "text": "この方は顔出しNGなのでご注意ください"},
        {"start": 640.0, "end": 900.0, "text": "それでは本題に入ります"},
    ]
}

CUTLIST = {
    "segments": [
        {"start": 0.0, "end": 300.0, "reason": "導入"},
        {"start": 640.0, "end": 940.0, "reason": "本題"},
    ],
    "mosaic_candidates": [],
    "editorial_note": "",
}

TELOP = {
    "entries": [
        {"start": 0.0, "end": 3.0, "text": "本日はようこそ"},
        {"start": 3.0, "end": 6.0, "text": "本題に入ります"},
    ]
}

MIX = {"bgm_file": None, "gain_db": 0.0, "selection_reason": "ライブラリなし"}

CHECKER_PASS = {"typos": [], "ng_conflicts": [], "verdict": "pass", "comment": "問題なし"}


class FakeLLMClient:
    def __init__(self, budget):
        self.budget = budget

    def call(self, agent, user_content, schema):
        self.budget.charge(10.0)  # 呼び出しごとに ¥10 計上
        return {
            "editor": CUTLIST,
            "telop_writer": TELOP,
            "music_selector": MIX,
            "checker": CHECKER_PASS,
        }[agent]


@pytest.fixture
def job(tmp_path, monkeypatch):
    # リポジトリレイアウトを tmp に再現
    job_dir = tmp_path / "jobs" / "itest"
    (job_dir).mkdir(parents=True)
    assets = tmp_path / "assets" / "itest"
    assets.mkdir(parents=True)
    (assets / "source.mp4").write_bytes(b"fake video")
    (job_dir / "job.yaml").write_text(yaml.safe_dump({
        "job_id": "itest",
        "source": "assets/itest/source.mp4",
        "target_duration_sec": 600,
        "duration_tolerance_sec": 15,
        "telop": {"max_chars_per_line": 26, "max_lines": 2},
        "ng_items": ["競合名"],
    }, allow_unicode=True), encoding="utf-8")

    monkeypatch.setattr(context_mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(context_mod, "ASSETS_DIR", tmp_path / "assets")
    monkeypatch.setattr(context_mod, "LLMClient", FakeLLMClient)

    # メディア処理のモック(機械検証はすべてグリーンの値を返す)
    monkeypatch.setattr(media, "probe_duration", lambda v: 600.0)
    monkeypatch.setattr(media, "measure_mean_volume", lambda v: -20.0)
    monkeypatch.setattr(media, "measure_loudness", lambda v: -14.2)
    monkeypatch.setattr(media, "detect_black_frames", lambda v: [])
    monkeypatch.setattr(media, "transcribe", lambda src, out: TRANSCRIPT)
    monkeypatch.setattr(media, "render_cutlist",
                        lambda src, cl, out: out.write_bytes(b"cut"))
    monkeypatch.setattr(media, "mix_bgm_and_normalize",
                        lambda v, b, g, out: out.write_bytes(b"mixed"))
    monkeypatch.setattr(media, "burn_subtitles",
                        lambda v, s, out: out.write_bytes(b"final"))

    def fake_thumbs(video, out_dir, count=3):
        paths = []
        for i in range(count):
            p = out_dir / f"thumbnail_{i + 1}.png"
            p.write_bytes(b"png")
            paths.append(p)
        return paths

    monkeypatch.setattr(media, "extract_thumbnails", fake_thumbs)
    return job_dir


def test_full_pipeline_flow(job):
    # 1回目: S1 でモザイク候補(「顔出しNG」)を検出し即エスカレーション(L6)
    ctx = JobContext(job)
    assert run_pipeline(ctx) == 1
    assert ctx.state.data["status"] == "stopped"
    assert (job / "logs" / "mosaic_candidates.json").exists()
    assert not ctx.state.is_completed("S1")

    # 人間がモザイクを承認
    ctx.state.data["approvals"]["mosaic"] = True
    ctx.state.save()

    # 2回目: S1〜S4 を自動実行し、S5 の人間ゲートで待機(exit 2)
    ctx = JobContext(job)  # まっさらなセッションで state.json から再開(L4)
    assert run_pipeline(ctx) == 2
    assert ctx.state.data["status"] == "pending_approval"
    for stage in ("S1", "S2", "S3", "S4"):
        assert ctx.state.is_completed(stage)
    # 中間成果物が state.json に記録されている(L4 記録項目②)
    for artifact in ("cutlist", "telop", "mix"):
        assert artifact in ctx.state.data["artifacts"]

    # 人間がプレビュー承認・サムネ選択
    ctx.state.data["approvals"]["preview"] = True
    ctx.state.data["approvals"]["thumbnail"] = 2
    ctx.state.save()

    # 3回目: S5 通過 → S6 QA 全項目グリーン → 納品パッケージ生成
    ctx = JobContext(job)
    assert run_pipeline(ctx) == 0
    assert ctx.state.data["status"] == "done"
    out = job / "output"
    for name in ("final.mp4", "telop.srt", "thumbnail.png",
                 "checker_report.json", "qa_report.json"):
        assert (out / name).exists(), f"納品物がありません: {name}"
    # 証跡(L2): logs/checker_report.json
    assert (job / "logs" / "checker_report.json").exists()
    # コストが累計されている(L4 記録項目③)
    assert ctx.state.data["cost_total_jpy"] > 0


def test_resume_skips_completed_stages(job):
    ctx = JobContext(job)
    ctx.state.data["approvals"] = {"mosaic": True, "preview": True, "thumbnail": 1}
    ctx.state.save()
    assert run_pipeline(JobContext(job)) == 0

    # 完了後の再実行は何もせず正常終了(冪等)
    ctx2 = JobContext(job)
    cost_before = ctx2.state.data["cost_total_jpy"]
    assert run_pipeline(ctx2) == 0
    assert ctx2.state.data["cost_total_jpy"] == cost_before  # 追加コストなし
