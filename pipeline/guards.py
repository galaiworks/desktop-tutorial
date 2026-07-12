"""L1 三重ガード(LOOP.md §3)。

1. 反復上限: 各ステージのリトライは3回まで。3回失敗で停止しエスカレーション
2. 差分停止: カットリスト再生成で前回と95%以上同一が2回続いたら収束とみなし先に進む
3. 予算上限: budget.Budget 参照(¥2,000 超過で即停止)
"""
from __future__ import annotations

import sys
from typing import Callable

from . import config
from .errors import (
    ApprovalPendingError,
    BudgetExceededError,
    EscalationError,
    PermissionViolation,
    StageError,
)
from .state import State


def with_retry(state: State, stage: str, fn: Callable[[], None]) -> None:
    """ステージを最大 MAX_RETRIES 回試行する。使い切ったらエスカレーション。"""
    last: StageError | None = None
    for attempt in range(1, config.MAX_RETRIES + 1):
        try:
            fn()
            return
        except (EscalationError, BudgetExceededError, PermissionViolation, ApprovalPendingError):
            raise  # ガード横断の停止事由はリトライしない
        except StageError as e:
            last = e
            state.record_error(stage, str(e), attempt)
            print(f"[{stage}] 試行 {attempt}/{config.MAX_RETRIES} 失敗: {e}", file=sys.stderr)
    raise EscalationError(
        "retry_exhausted",
        f"{stage} が{config.MAX_RETRIES}回連続で失敗しました: {last}",
        {"stage": stage, "last_error": str(last)},
    )


def _segment_keys(cutlist: dict) -> set[tuple[float, float]]:
    return {
        (round(float(s["start"]), 1), round(float(s["end"]), 1))
        for s in cutlist.get("segments", [])
    }


def cutlist_similarity(a: dict | None, b: dict | None) -> float:
    """2つのカットリストの類似度(Jaccard係数、0.0〜1.0)。"""
    if a is None or b is None:
        return 0.0
    ka, kb = _segment_keys(a), _segment_keys(b)
    if not ka and not kb:
        return 1.0
    if not ka or not kb:
        return 0.0
    return len(ka & kb) / len(ka | kb)


def check_convergence(state: State, new_cutlist: dict) -> bool:
    """差分停止ガード。95%以上同一の再生成が2回続いたら True(=収束、先に進む)。"""
    conv = state.data["convergence"]
    prev = conv.get("prev_cutlist")
    similarity = cutlist_similarity(prev, new_cutlist)
    if similarity >= config.CONVERGENCE_THRESHOLD:
        conv["streak"] = conv.get("streak", 0) + 1
    else:
        conv["streak"] = 0
    conv["prev_cutlist"] = new_cutlist
    state.save()
    return conv["streak"] >= config.CONVERGENCE_STREAK
