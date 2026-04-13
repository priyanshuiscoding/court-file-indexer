from __future__ import annotations

import re
from typing import Iterable, Tuple


def clamp(v: int, lo: int, hi: int) -> int:
    return max(lo, min(v, hi))


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _looks_headerish(text: str) -> bool:
    t = _norm(text)
    return (
        "index" in t
        or "particular" in t
        or "description" in t
        or "annexure" in t
        or "annex" in t
        or "page no" in t
        or "page nos" in t
        or "remarks" in t
        or "s.no" in t
        or "s no" in t
        or "sr.no" in t
        or "sl.no" in t
        or "serial no" in t
    )


def _looks_rowish(text: str) -> bool:
    t = _norm(text)
    if not t:
        return False
    if re.match(r"^\d{1,2}[\.)-]?\s*", t):
        return True
    if "index" in t:
        return True
    if "annexure" in t or "annex" in t:
        return True
    if "description" in t or "particular" in t:
        return True
    if "page no" in t or "page nos" in t or "remarks" in t:
        return True
    return False


def _looks_footer_noise(text: str) -> bool:
    t = _norm(text)
    if not t:
        return False
    footer_terms = (
        "counsel",
        "advocate",
        "declaration",
        "dated",
        "date:",
        "date ",
        "place",
        "received",
        "clerk",
        "principal seat",
        "high court of",
    )
    return any(term in t for term in footer_terms)


def detect_table_region(width: int, height: int, lines: Iterable[dict] | None = None) -> Tuple[int, int, int, int]:
    """
    Returns (x1, y1, x2, y2).
    Uses a conservative default crop, then lightly adapts:
    - anchors top near header if found
    - extends bottom to last row-like line
    - avoids drifting too far into footer/signature area
    """
    h, w = height, width

    x1 = int(w * 0.08)
    x2 = int(w * 0.92)
    y1 = int(h * 0.08)
    y2 = int(h * 0.72)

    x1 = clamp(x1, 0, w - 1)
    x2 = clamp(x2, x1 + 1, w)
    y1 = clamp(y1, 0, h - 1)
    y2 = clamp(y2, y1 + 1, h)

    if not lines:
        return x1, y1, x2, y2

    header_top = None
    row_bottoms: list[int] = []

    for line in lines:
        bbox = line.get("bbox") or {}
        lx1 = int(bbox.get("x1", 0))
        lx2 = int(bbox.get("x2", 0))
        ly1 = int(bbox.get("y1", 0))
        ly2 = int(bbox.get("y2", 0))
        text = str(line.get("text") or "")

        if lx2 <= 0 or ly2 <= 0:
            continue

        # Ignore narrow left-margin tokens / stamps / stray marks.
        if lx2 - lx1 < 80:
            continue

        if _looks_headerish(text) and header_top is None:
            header_top = ly1

        if _looks_rowish(text) and not _looks_footer_noise(text):
            row_bottoms.append(ly2)

    if header_top is not None:
        y1 = clamp(int(header_top - 0.03 * h), int(h * 0.06), int(h * 0.22))

    if row_bottoms:
        dynamic_bottom = int(max(row_bottoms) + 0.03 * h)
        y2 = clamp(dynamic_bottom, int(h * 0.62), int(h * 0.82))

    return x1, y1, x2, y2
