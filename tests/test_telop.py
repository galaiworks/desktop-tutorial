"""テロップ機械検証(字幕はみ出し・時刻整合・SRT変換・誤字適用)のテスト。"""
from pipeline.telop import apply_corrections, check_overflow, check_timing, to_srt


def telop(*entries):
    return {"entries": [{"start": s, "end": e, "text": t} for s, e, t in entries]}


class TestOverflow:
    def test_within_limits_green(self):
        t = telop((0, 3, "こんにちは"), (3, 6, "一行目\n二行目"))
        assert check_overflow(t, max_chars_per_line=26, max_lines=2) == []

    def test_too_many_chars(self):
        t = telop((0, 3, "あ" * 27))
        violations = check_overflow(t, 26, 2)
        assert len(violations) == 1
        assert "文字数超過" in violations[0]["problem"]

    def test_too_many_lines(self):
        t = telop((0, 3, "一\n二\n三"))
        violations = check_overflow(t, 26, 2)
        assert len(violations) == 1
        assert "行数超過" in violations[0]["problem"]


class TestTiming:
    def test_valid_timing(self):
        t = telop((0, 3, "a"), (3, 6, "b"))
        assert check_timing(t) == []

    def test_reversed_time(self):
        t = telop((5, 3, "a"))
        assert "逆転" in check_timing(t)[0]["problem"]

    def test_overlap(self):
        t = telop((0, 5, "a"), (4, 8, "b"))
        assert "重複" in check_timing(t)[0]["problem"]


class TestSrt:
    def test_format(self):
        srt = to_srt(telop((0, 2.5, "こんにちは"), (2.5, 5, "テスト")))
        assert "1\n00:00:00,000 --> 00:00:02,500\nこんにちは" in srt
        assert "2\n00:00:02,500 --> 00:00:05,000\nテスト" in srt

    def test_hour_boundary(self):
        srt = to_srt(telop((3661.25, 3662, "a")))
        assert "01:01:01,250" in srt


class TestCorrections:
    def test_apply(self):
        t = telop((0, 3, "こんにちわ、皆さん"))
        n = apply_corrections(t, [{"original": "こんにちわ", "corrected": "こんにちは"}])
        assert n == 1
        assert t["entries"][0]["text"] == "こんにちは、皆さん"

    def test_missing_original_skipped(self):
        t = telop((0, 3, "テスト"))
        n = apply_corrections(t, [{"original": "存在しない", "corrected": "x"}])
        assert n == 0
        assert t["entries"][0]["text"] == "テスト"
