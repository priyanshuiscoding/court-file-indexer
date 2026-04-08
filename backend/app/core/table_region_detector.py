from __future__ import annotations

from typing import Iterable, Tuple


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(v, hi))


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

        if lx2 <= 0:
            continue
        if lx1 < 40:
            continue
        if lx2 - lx1 < 40:
            continue
        if ly2 <= y1:
            continue

        candidate_bottoms.append(ly2)

    if not candidate_bottoms:
        return baseline_y2

    dynamic = int(max(candidate_bottoms) + (0.03 * height))
    return clamp(dynamic, int(height * 0.62), int(height * 0.90))


def detect_table_region(width: int, height: int, lines: Iterable[dict] | None = None) -> Tuple[int, int, int, int]:
    """
    Returns (x1, y1, x2, y2).
    Heuristic crop for first-page index tables in scanned court PDFs,
    with adaptive bottom extension when rows continue lower on page.
    """
    h, w = height, width

    x1 = int(w * 0.08)
    x2 = int(w * 0.92)
    y1 = int(h * 0.08)
    y2 = int(h * 0.74)

    x1 = clamp(x1, 0, w - 1)
    y1 = clamp(y1, 0, h - 1)
    x2 = clamp(x2, x1 + 1, w)

    y2 = _adaptive_bottom(h, y1, y2, lines=lines)
    y2 = clamp(y2, y1 + 1, h)

    return x1, y1, x2, y2
