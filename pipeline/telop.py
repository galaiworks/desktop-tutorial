"""テロップ(字幕)のユーティリティ。はみ出し検査は純粋なスクリプト検証(L2)。"""
from __future__ import annotations


def check_overflow(telop: dict, max_chars_per_line: int, max_lines: int) -> list[dict]:
    """字幕はみ出しを検査する。違反リストが空 = ゼロ(グリーン)。"""
    violations = []
    for i, entry in enumerate(telop.get("entries", [])):
        lines = str(entry.get("text", "")).split("\n")
        if len(lines) > max_lines:
            violations.append({
                "index": i, "text": entry.get("text"),
                "problem": f"行数超過: {len(lines)} > {max_lines}",
            })
            continue
        for line in lines:
            if len(line) > max_chars_per_line:
                violations.append({
                    "index": i, "text": entry.get("text"),
                    "problem": f"1行の文字数超過: {len(line)} > {max_chars_per_line}",
                })
                break
    return violations


def check_timing(telop: dict) -> list[dict]:
    """開始/終了時刻の整合(逆転・重複)を検査する。"""
    violations = []
    entries = telop.get("entries", [])
    for i, entry in enumerate(entries):
        start, end = float(entry.get("start", 0)), float(entry.get("end", 0))
        if end <= start:
            violations.append({"index": i, "problem": f"時刻が逆転しています: {start} >= {end}"})
        if i > 0 and start < float(entries[i - 1].get("end", 0)):
            violations.append({"index": i, "problem": "前のテロップと時間が重複しています"})
    return violations


def _fmt_time(seconds: float) -> str:
    ms = int(round(seconds * 1000))
    h, rem = divmod(ms, 3600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(telop: dict) -> str:
    """telop.json を SRT 形式に変換する。"""
    blocks = []
    for i, entry in enumerate(telop.get("entries", []), start=1):
        blocks.append(
            f"{i}\n{_fmt_time(float(entry['start']))} --> {_fmt_time(float(entry['end']))}\n"
            f"{entry['text']}\n"
        )
    return "\n".join(blocks)


def apply_corrections(telop: dict, corrections: list[dict]) -> int:
    """Checker の誤字指摘(original→corrected)をテロップに適用する。適用件数を返す。"""
    applied = 0
    for c in corrections:
        original, corrected = c.get("original"), c.get("corrected")
        if not original or corrected is None:
            continue
        for entry in telop.get("entries", []):
            if original in entry.get("text", ""):
                entry["text"] = entry["text"].replace(original, corrected)
                applied += 1
    return applied
