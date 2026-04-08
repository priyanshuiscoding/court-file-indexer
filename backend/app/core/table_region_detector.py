from __future__ import annotations

from typing import Tuple


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(v, hi))


def detect_table_region(width: int, height: int) -> Tuple[int, int, int, int]:
    """
    Returns (x1, y1, x2, y2).
    Heuristic crop for first-page index tables in scanned court PDFs.
    """
    h, w = height, width

    x1 = int(w * 0.08)
    x2 = int(w * 0.92)
    y1 = int(h * 0.08)
    y2 = int(h * 0.62)

    x1 = clamp(x1, 0, w - 1)
    y1 = clamp(y1, 0, h - 1)
    x2 = clamp(x2, x1 + 1, w)
    y2 = clamp(y2, y1 + 1, h)

    return x1, y1, x2, y2
