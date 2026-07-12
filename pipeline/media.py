"""機械検証・メディア処理層(LOOP.md §4)。

ffprobe/ラウドネス測定はスクリプトで実行し、LLMの自己申告を採用しない。
外部ツールの実行は L3 の許可リスト(ffmpeg/ffprobe/whisper/auto-editor)を通す。
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

from . import config
from .errors import StageError
from .permissions import Sandbox


def run_tool(cmd: list[str], timeout: int = 3600) -> subprocess.CompletedProcess:
    Sandbox.check_tool(cmd)
    if shutil.which(cmd[0]) is None:
        raise StageError(f"ツールが見つかりません(インストールが必要です): {cmd[0]}")
    try:
        return subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired as e:
        raise StageError(f"ツールの実行がタイムアウトしました: {' '.join(cmd[:3])}") from e


def probe_duration(video: Path) -> float:
    """動画の尺(秒)を ffprobe で実測する。"""
    proc = run_tool([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(video),
    ])
    if proc.returncode != 0:
        raise StageError(f"ffprobe 失敗: {proc.stderr[-500:]}")
    try:
        return float(json.loads(proc.stdout)["format"]["duration"])
    except (KeyError, ValueError, json.JSONDecodeError) as e:
        raise StageError(f"ffprobe の出力を解析できません: {e}") from e


def measure_loudness(video: Path) -> float:
    """統合ラウドネス(LUFS)を ffmpeg loudnorm で実測する。"""
    proc = run_tool([
        "ffmpeg", "-hide_banner", "-i", str(video),
        "-af", "loudnorm=print_format=json", "-f", "null", "-",
    ])
    m = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", proc.stderr, re.DOTALL)
    if not m:
        raise StageError(f"ラウドネス測定に失敗しました: {proc.stderr[-500:]}")
    return float(json.loads(m.group(0))["input_i"])


def measure_mean_volume(video: Path) -> float:
    """平均音量(dB)を volumedetect で実測する(音声品質エスカレーション用)。"""
    proc = run_tool([
        "ffmpeg", "-hide_banner", "-i", str(video),
        "-af", "volumedetect", "-f", "null", "-",
    ])
    m = re.search(r"mean_volume:\s*(-?[\d.]+)\s*dB", proc.stderr)
    if not m:
        raise StageError(f"音量測定に失敗しました: {proc.stderr[-500:]}")
    return float(m.group(1))


def detect_black_frames(video: Path) -> list[dict]:
    """黒フレーム区間を blackdetect で実測する。空リスト = ゼロ(グリーン)。"""
    proc = run_tool([
        "ffmpeg", "-hide_banner", "-i", str(video),
        "-vf", f"blackdetect=d={config.BLACK_FRAME_MIN_DURATION}:pix_th=0.10",
        "-an", "-f", "null", "-",
    ])
    found = []
    for m in re.finditer(
        r"black_start:(?P<s>[\d.]+)\s+black_end:(?P<e>[\d.]+)", proc.stderr
    ):
        found.append({"start": float(m.group("s")), "end": float(m.group("e"))})
    return found


def transcribe(source: Path, out_dir: Path) -> dict:
    """whisper CLI で文字起こしする。out_dir に JSON を出力し読み込んで返す。"""
    proc = run_tool([
        "whisper", str(source), "--model", "small", "--language", "ja",
        "--output_format", "json", "--output_dir", str(out_dir),
    ], timeout=7200)
    if proc.returncode != 0:
        raise StageError(f"whisper 失敗: {proc.stderr[-500:]}")
    json_path = out_dir / (source.stem + ".json")
    if not json_path.exists():
        raise StageError(f"whisper の出力が見つかりません: {json_path}")
    return json.loads(json_path.read_text(encoding="utf-8"))


def render_cutlist(source: Path, cutlist: dict, out: Path) -> None:
    """カットリスト(segments)に従って ffmpeg で切り出し・連結する。"""
    segments = cutlist.get("segments", [])
    if not segments:
        raise StageError("カットリストにセグメントがありません")
    parts_v, parts_a, concat = [], [], []
    for i, seg in enumerate(segments):
        s, e = float(seg["start"]), float(seg["end"])
        parts_v.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}];")
        parts_a.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}];")
        concat.append(f"[v{i}][a{i}]")
    filter_complex = (
        "".join(parts_v) + "".join(parts_a)
        + "".join(concat) + f"concat=n={len(segments)}:v=1:a=1[outv][outa]"
    )
    proc = run_tool([
        "ffmpeg", "-hide_banner", "-y", "-i", str(source),
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", str(out),
    ], timeout=7200)
    if proc.returncode != 0:
        raise StageError(f"カット編集のレンダリングに失敗しました: {proc.stderr[-800:]}")


def mix_bgm_and_normalize(video: Path, bgm: Path | None, gain_db: float, out: Path) -> None:
    """BGMミックス(任意)+ 2パス相当の loudnorm で -14 LUFS に正規化する。"""
    target = config.LOUDNESS_TARGET_LUFS
    if bgm is not None:
        af = (
            f"[1:a]volume={gain_db}dB,aloop=loop=-1:size=2e9[bgm];"
            f"[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[mix];"
            f"[mix]loudnorm=I={target}:TP=-1.5:LRA=11[aout]"
        )
        cmd = [
            "ffmpeg", "-hide_banner", "-y", "-i", str(video), "-i", str(bgm),
            "-filter_complex", af, "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out),
        ]
    else:
        cmd = [
            "ffmpeg", "-hide_banner", "-y", "-i", str(video),
            "-af", f"loudnorm=I={target}:TP=-1.5:LRA=11",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", str(out),
        ]
    proc = run_tool(cmd, timeout=7200)
    if proc.returncode != 0:
        raise StageError(f"ミックス/正規化に失敗しました: {proc.stderr[-800:]}")


def burn_subtitles(video: Path, srt: Path, out: Path) -> None:
    """SRT字幕を焼き込む。"""
    srt_escaped = str(srt).replace("'", r"\'").replace(":", r"\:")
    proc = run_tool([
        "ffmpeg", "-hide_banner", "-y", "-i", str(video),
        "-vf", f"subtitles=filename='{srt_escaped}'",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "copy", str(out),
    ], timeout=7200)
    if proc.returncode != 0:
        raise StageError(f"字幕焼き込みに失敗しました: {proc.stderr[-800:]}")


def extract_thumbnails(video: Path, out_dir: Path, count: int = 3) -> list[Path]:
    """サムネイル候補を等間隔で抽出する(S5 サムネ選択ゲート用)。"""
    duration = probe_duration(video)
    paths = []
    for i in range(count):
        t = duration * (i + 1) / (count + 1)
        out = out_dir / f"thumbnail_{i + 1}.png"
        proc = run_tool([
            "ffmpeg", "-hide_banner", "-y", "-ss", f"{t:.2f}", "-i", str(video),
            "-frames:v", "1", str(out),
        ])
        if proc.returncode != 0:
            raise StageError(f"サムネイル抽出に失敗しました: {proc.stderr[-300:]}")
        paths.append(out)
    return paths


# --- モザイク候補検出(機械側): 文字起こしから個人情報らしき言及を抽出 ---
PII_PATTERNS = [
    (r"\d{2,4}-\d{2,4}-\d{3,4}", "電話番号らしき数字列"),
    (r"[\w.+-]+@[\w-]+\.[\w.]+", "メールアドレス"),
    (r"〒?\d{3}-?\d{4}", "郵便番号らしき数字列"),
    (r"(住所|自宅|マンション名)", "住所への言及"),
    (r"(ナンバープレート|車のナンバー)", "車両ナンバーへの言及"),
    (r"(顔出しNG|モザイク|ぼかし)", "モザイク要否への直接言及"),
]


def scan_mosaic_candidates(transcript: dict) -> list[dict]:
    """文字起こしテキストから機械的にモザイク候補(PII言及)を抽出する。"""
    candidates = []
    for seg in transcript.get("segments", []):
        text = seg.get("text", "")
        for pattern, label in PII_PATTERNS:
            if re.search(pattern, text):
                candidates.append({
                    "start": seg.get("start"),
                    "end": seg.get("end"),
                    "reason": label,
                    "text": text.strip(),
                })
                break
    return candidates
