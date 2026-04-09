from __future__ import annotations

import re
from typing import Iterable, Tuple


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(v, hi))


def _looks_tableish(text: str) -> bool:
    t = (text or "").strip().lower()
    if not t:
        return False
    if re.match(r"^\d{1,2}[\.)-]?\s", t):
        return True
    if "index" in t:
        return True
    if "annexure" in t:
        return True
    if "description" in t:
        return True
    if "page no" in t or "page nos" in t:
        return True
    if "s.no" in t or "s no" in t or "sr.no" in t or "sl.no" in t:
        return True
    return False


def _adaptive_bottom(
    height: int,
    y1: int,
    baseline_y2: int,
    lines: Iterable[dict] | None = None,
) -> int:
    if not lines:
        return baseline_y2

    candidate_bottoms: list[int] = []
    for line in lines:
        bbox = line.get("bbox") or {}
        lx1 = int(bbox.get("x1", 0))
        lx2 = int(bbox.get("x2", 0))
        ly2 = int(bbox.get("y2", 0))
        text = str(line.get("text") or "")

        if lx2 <= 0:
            continue
        if lx1 < 40:
            continue
        if lx2 - lx1 < 120:
            continue
        if ly2 <= y1:
            continue
        if not _looks_tableish(text):
            continue

        candidate_bottoms.append(ly2)

    if not candidate_bottoms:
        return baseline_y2

    dynamic = int(max(candidate_bottoms) + (0.02 * height))
    # Keep bottom conservative to avoid declaration/footer contamination.
    return clamp(dynamic, int(height * 0.62), int(height * 0.80))


def detect_table_region(width: int, height: int, lines: Iterable[dict] | None = None) -> Tuple[int, int, int, int]:
    """
    Returns (x1, y1, x2, y2).
    Conservative table crop with light adaptive bottom extension.
    """
    h, w = height, width

    x1 = int(w * 0.08)
    x2 = int(w * 0.92)
    y1 = int(h * 0.08)
    y2 = int(h * 0.70)

    x1 = clamp(x1, 0, w - 1)
    y1 = clamp(y1, 0, h - 1)
    x2 = clamp(x2, x1 + 1, w)

    y2 = _adaptive_bottom(h, y1, y2, lines=lines)
    y2 = clamp(y2, y1 + 1, h)

    return x1, y1, x2, y2
