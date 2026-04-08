from __future__ import annotations

import re
from typing import List, Optional, Tuple

from app.schemas.index_models import OCRWord, OCRLine, TableColumns, IndexRow


SERIAL_RE = re.compile(r"^\s*(\d{1,3})[\).\-:]?\s*$")
SERIAL_ANY_RE = re.compile(r"\b(\d{1,3})\b")
PAGE_RANGE_RE = re.compile(r"(\d{1,4})\s*[-to]+\s*(\d{1,4})", re.IGNORECASE)
ANNEX_RE = re.compile(r"^[A-Za-z]+[\/\-]?\d{1,3}$")


def clean_token(text: str) -> str:
    text = text.strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_inline_text(text: str) -> str:
    text = clean_token(text)
    text = text.replace("|", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def group_words_into_lines(words: List[OCRWord], y_tol: int = 18) -> List[OCRLine]:
    if not words:
        return []

    words = sorted(words, key=lambda w: (w.y1, w.x1))
    lines: List[OCRLine] = []

    for word in words:
        placed = False
        for line in lines:
            center_y = (line.y_top + line.y_bottom) / 2
            if abs(word.cy - center_y) <= y_tol:
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
    t = text.lower()
    return (
        "particulars of document" in t
        or "description of document" in t
        or "description of documents" in t
        or "annexure" in t
        or "page nos" in t
        or "page no of document" in t
        or "s.no" in t
        or "sr.no" in t
        or "sl.no" in t
    )


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

    return TableColumns(
        sno_x_max=left + int(width * 0.11),
        desc_x_min=left + int(width * 0.11) + 1,
        desc_x_max=left + int(width * 0.66),
        annex_x_min=left + int(width * 0.66) + 1,
        annex_x_max=left + int(width * 0.82),
        pages_x_min=left + int(width * 0.82) + 1,
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
    t = clean_token(text).replace("-", "-").lower()
    t = re.sub(r"\bto\b", "-", t)
    m = PAGE_RANGE_RE.search(t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return a, b

    nums = re.findall(r"\d{1,4}", t)
    if len(nums) == 1:
        v = int(nums[0])
        return v, v
    if len(nums) >= 2:
        a, b = int(nums[0]), int(nums[1])
        return a, b
    return None, None


def line_looks_like_row_start(line: OCRLine, cols: TableColumns) -> bool:
    sno_text, desc_text, _, _ = split_line_by_columns(line, cols)
    return parse_serial(sno_text) is not None and bool(desc_text.strip())


def line_looks_like_continuation(line: OCRLine, cols: TableColumns) -> bool:
    sno_text, desc_text, annex_text, pages_text = split_line_by_columns(line, cols)
    return (
        parse_serial(sno_text) is None
        and (
            bool(desc_text.strip())
            or parse_annexure(annex_text) is not None
            or parse_page_range(pages_text) != (None, None)
        )
    )


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


def reconcile_missing_rows(rows: List[IndexRow]) -> List[IndexRow]:
    rows = [r for r in rows if r.row_no is not None or r.description]
    rows.sort(key=lambda r: (r.row_no or 9999, r.source_page))

    explicit = [r.row_no for r in rows if r.row_no is not None]
    if not explicit:
        return rows

    expected = set(range(min(explicit), max(explicit) + 1))
    present = set(explicit)
    missing = sorted(expected - present)

    fillers = [r for r in rows if r.row_no is None and r.description]

    for miss in missing:
        if not fillers:
            break
        filler = fillers.pop(0)
        filler.row_no = miss
        filler.review_required = True
        filler.confidence = min(filler.confidence, 0.65)
        rows.append(filler)

    rows.sort(key=lambda r: (r.row_no or 9999, r.source_page))
    return rows


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

    return reconcile_missing_rows(rows)
