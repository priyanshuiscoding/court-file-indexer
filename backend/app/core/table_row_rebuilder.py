from __future__ import annotations

import re
from statistics import median
from typing import List, Optional, Tuple

from app.schemas.index_models import OCRWord, OCRLine, TableColumns, IndexRow


SERIAL_RE = re.compile(r"^\s*(\d{1,3})[\).\-:]?\s*$")
SERIAL_ANY_RE = re.compile(r"\b(\d{1,3})\b")
PAGE_RANGE_RE = re.compile(r"(\d{1,4})\s*[-–—to]+\s*(\d{1,4})", re.IGNORECASE)
ANNEX_RE = re.compile(r"^[A-Za-z]+[\/\-]?\d{1,3}$")

HEADER_SNO_HINTS = ("s.no", "s no", "sr.no", "sr no", "sl.no", "sl no", "serial")
HEADER_DESC_HINTS = (
    "particular",
    "particulars",
    "description",
    "documents",
    "document",
)
HEADER_ANNEX_HINTS = ("annexure", "annex", "ann.")
HEADER_PAGE_HINTS = ("page", "page no", "page nos", "pageno", "remarks")

FOOTER_NOISE_PATTERNS = [
    r"\bcounsel\b",
    r"\badvocate\b",
    r"\bplace\b",
    r"\bdated\b",
    r"\bdate\b",
    r"\bdeclaration\b",
    r"\breceived\b",
    r"\bclerk\b",
    r"\bprincipal seat\b",
    r"\bhigh court\b",
    r"\bapplicant\b",
    r"\brespondent\b",
]


def clean_token(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_inline_text(text: str) -> str:
    text = clean_token(text)
    text = text.replace("|", " ")
    text = text.replace("¦", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _word_height(word: OCRWord) -> int:
    return max(1, int(word.y2 - word.y1))


def _adaptive_y_tol(words: List[OCRWord]) -> int:
    if not words:
        return 18
    heights = [_word_height(w) for w in words]
    med = int(median(heights)) if heights else 18
    return max(10, min(24, int(med * 0.85)))


def group_words_into_lines(words: List[OCRWord], y_tol: int | None = None) -> List[OCRLine]:
    if not words:
        return []

    words = sorted(words, key=lambda w: (w.y1, w.x1))
    tol = y_tol if y_tol is not None else _adaptive_y_tol(words)

    lines: List[OCRLine] = []

    for word in words:
        placed = False
        for line in lines:
            center_y = (line.y_top + line.y_bottom) / 2
            if abs(word.cy - center_y) <= tol:
                line.words.append(word)
                placed = True
                break
        if not placed:
            lines.append(OCRLine(words=[word]))

    for line in lines:
        line.words.sort(key=lambda w: w.x1)

    lines.sort(key=lambda l: l.y_top)
    return lines


def is_header_line(text: str) -> bool:
    t = normalize_inline_text(text).lower()
    compact = re.sub(r"[^a-z0-9]+", "", t)
    return (
        "particulars of document" in t
        or "description of document" in t
        or "description of documents" in t
        or "particulars" in t
        or "description" in t
        or "annexure" in t
        or "annex" in t
        or "page nos" in t
        or "page no" in t
        or "pageno" in compact
        or "remarks" in t
        or "s.no" in t
        or "s no" in t
        or "sr.no" in t
        or "sr no" in t
        or "sl.no" in t
        or "sl no" in t
        or "serial no" in t
    )


def _normalize_for_hint(text: str) -> str:
    return re.sub(r"[^a-z0-9./ -]+", " ", (text or "").lower())


def _find_header_anchors(header: OCRLine) -> dict[str, int]:
    """
    Returns approximate x anchors for:
    sno, desc, annex, pages
    """
    anchors: dict[str, int] = {}
    for w in sorted(header.words, key=lambda x: x.x1):
        wt = _normalize_for_hint(w.text)

        if "s.no" in wt or "s no" in wt or "sr.no" in wt or "sr no" in wt or "sl.no" in wt or "sl no" in wt:
            anchors.setdefault("sno", w.x1)
            continue

        if any(h in wt for h in HEADER_DESC_HINTS):
            anchors.setdefault("desc", w.x1)
            continue

        if any(h in wt for h in HEADER_ANNEX_HINTS):
            anchors.setdefault("annex", w.x1)
            continue

        if any(h in wt for h in HEADER_PAGE_HINTS):
            anchors.setdefault("pages", w.x1)
            continue

    return anchors


def detect_columns(lines: List[OCRLine]) -> Optional[TableColumns]:
    header = None
    for line in lines:
        if is_header_line(line.text):
            header = line
            break

    if header is None or not header.words:
        return None

    xs = sorted([w.x1 for w in header.words] + [w.x2 for w in header.words])
    left = min(xs)
    right = max(xs)
    width = max(1, right - left)

    anchors = _find_header_anchors(header)

    sno_anchor = anchors.get("sno", left)
    desc_anchor = anchors.get("desc", left + int(width * 0.12))
    pages_anchor = anchors.get("pages", left + int(width * 0.84))
    annex_anchor = anchors.get("annex")

    # Fallback when annex column does not really exist.
    if annex_anchor is None:
        annex_anchor = left + int(width * 0.72)

    # Sanity clamps to preserve ordering.
    sno_x_max = max(left + int(width * 0.08), min(desc_anchor - 10, left + int(width * 0.14)))
    desc_x_min = sno_x_max + 1

    desc_x_max = min(
        max(desc_anchor + int(width * 0.40), annex_anchor - 8),
        pages_anchor - 16,
    )
    desc_x_max = max(desc_x_min + 20, desc_x_max)

    annex_x_min = desc_x_max + 1
    annex_x_max = max(annex_x_min + 8, pages_anchor - 10)
    pages_x_min = annex_x_max + 1

    # Final guards in case OCR header is weird.
    if pages_x_min <= desc_x_max:
        pages_x_min = left + int(width * 0.84)
        annex_x_max = max(desc_x_max + 8, pages_x_min - 8)
        annex_x_min = max(desc_x_max + 1, left + int(width * 0.70))

    return TableColumns(
        sno_x_max=sno_x_max,
        desc_x_min=desc_x_min,
        desc_x_max=desc_x_max,
        annex_x_min=annex_x_min,
        annex_x_max=annex_x_max,
        pages_x_min=pages_x_min,
    )


def split_line_by_columns(line: OCRLine, cols: TableColumns) -> Tuple[str, str, str, str]:
    sno, desc, annex, pages = [], [], [], []

    for w in sorted(line.words, key=lambda x: x.x1):
        if w.cx <= cols.sno_x_max:
            sno.append(w.text)
        elif cols.desc_x_min <= w.cx <= cols.desc_x_max:
            desc.append(w.text)
        elif cols.annex_x_min <= w.cx <= cols.annex_x_max:
            annex.append(w.text)
        elif w.cx >= cols.pages_x_min:
            pages.append(w.text)
        else:
            desc.append(w.text)

    return (
        normalize_inline_text(" ".join(sno)),
        normalize_inline_text(" ".join(desc)),
        normalize_inline_text(" ".join(annex)),
        normalize_inline_text(" ".join(pages)),
    )


def parse_serial(text: str) -> Optional[int]:
    t = clean_token(text)
    m = SERIAL_RE.match(t)
    if m:
        return int(m.group(1))
    m = SERIAL_ANY_RE.search(t)
    return int(m.group(1)) if m else None


def parse_annexure(text: str) -> Optional[str]:
    t = clean_token(text).replace(" ", "").upper().replace("/", "-")
    if not t or t == "-":
        return None
    if ANNEX_RE.match(t):
        return t
    return None


def parse_page_range(text: str) -> Tuple[Optional[int], Optional[int]]:
    t = normalize_inline_text(text)
    t = t.replace("–", "-").replace("—", "-")
    t = re.sub(r"\bto\b", "-", t, flags=re.IGNORECASE)

    m = PAGE_RANGE_RE.search(t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return min(a, b), max(a, b)

    nums = re.findall(r"\d{1,4}", t)
    if len(nums) == 1:
        v = int(nums[0])
        return v, v
    if len(nums) >= 2:
        a, b = int(nums[0]), int(nums[1])
        return min(a, b), max(a, b)
    return None, None


def _line_is_footer_noise(text: str) -> bool:
    t = normalize_inline_text(text).lower()
    if not t:
        return False
    return any(re.search(pat, t) for pat in FOOTER_NOISE_PATTERNS)


def _line_has_desc_overlap(line: OCRLine, cols: TableColumns) -> bool:
    for w in line.words:
        if cols.desc_x_min <= w.cx <= cols.desc_x_max:
            return True
    return False


def line_looks_like_row_start(line: OCRLine, cols: TableColumns) -> bool:
    sno_text, desc_text, _, _ = split_line_by_columns(line, cols)
    return parse_serial(sno_text) is not None and bool(desc_text.strip())


def line_looks_like_continuation(line: OCRLine, cols: TableColumns) -> bool:
    if _line_is_footer_noise(line.text):
        return False

    sno_text, desc_text, annex_text, pages_text = split_line_by_columns(line, cols)

    has_serial = parse_serial(sno_text) is not None
    has_desc = bool(desc_text.strip()) and _line_has_desc_overlap(line, cols)
    has_annex = parse_annexure(annex_text) is not None
    has_pages = parse_page_range(pages_text) != (None, None)

    # Continue only if it really looks like row content, not stray fragments.
    return (not has_serial) and (has_desc or (has_pages and has_desc) or (has_annex and has_desc))


def finalize_row(parts: List[OCRLine], cols: TableColumns, source_page: int) -> Optional[IndexRow]:
    if not parts:
        return None

    sno_texts, desc_texts, annex_texts, page_texts = [], [], [], []
    all_words: List[OCRWord] = []

    for line in parts:
        sno, desc, annex, pages = split_line_by_columns(line, cols)
        if sno:
            sno_texts.append(sno)
        if desc:
            desc_texts.append(desc)
        if annex:
            annex_texts.append(annex)
        if pages:
            page_texts.append(pages)
        all_words.extend(line.words)

    row_no = parse_serial(" ".join(sno_texts))
    desc = normalize_inline_text(" ".join(desc_texts))
    annexure = parse_annexure(" ".join(annex_texts))
    page_start, page_end = parse_page_range(" ".join(page_texts))

    if row_no is None and not desc:
        return None

    if _line_is_footer_noise(desc):
        return None

    confs = [(w.conf / 100.0) if w.conf > 1 else w.conf for w in all_words]
    avg_conf = sum(confs) / max(1, len(confs))

    x1 = min(w.x1 for w in all_words)
    y1 = min(w.y1 for w in all_words)
    x2 = max(w.x2 for w in all_words)
    y2 = max(w.y2 for w in all_words)

    return IndexRow(
        row_no=row_no,
        description=desc,
        annexure=annexure,
        page_start=page_start,
        page_end=page_end,
        raw_text=" ".join(line.text for line in parts).strip(),
        confidence=avg_conf,
        review_required=False,
        source_page=source_page,
        bbox=(x1, y1, x2, y2),
    )


def rebuild_index_rows(lines: List[OCRLine], cols: TableColumns, source_page: int) -> List[IndexRow]:
    rows: List[IndexRow] = []
    current: List[OCRLine] = []
    started = False

    for line in lines:
        text = line.text.strip()
        if not text:
            continue

        if is_header_line(text):
            started = True
            continue

        if not started:
            continue

        if _line_is_footer_noise(text):
            if current:
                row = finalize_row(current, cols, source_page)
                if row:
                    rows.append(row)
                current = []
            continue

        if line_looks_like_row_start(line, cols):
            if current:
                row = finalize_row(current, cols, source_page)
                if row:
                    rows.append(row)
            current = [line]
            continue

        if current and line_looks_like_continuation(line, cols):
            current.append(line)
            continue

        if current:
            row = finalize_row(current, cols, source_page)
            if row:
                rows.append(row)
            current = []

    if current:
        row = finalize_row(current, cols, source_page)
        if row:
            rows.append(row)

    # Conservative: do not fabricate missing serial rows.
    rows = [r for r in rows if r.row_no is not None or r.description]
    rows.sort(key=lambda r: (r.row_no or 9999, r.source_page))
    return rows
