from __future__ import annotations

import re
from typing import List

from app.schemas.index_models import IndexRow


BANNED_DESC_PATTERNS = [
    r"whether any bail application",
    r"\bcase\s*no\b",
    r"\bresult\b",
    r"\bcourt\(s\)\b",
    r"\baccused application\b",
    r"\bname of the co\b",
    r"\binstitution date\b",
    r"\bparticular of crime\b",
    r"\bdate of arrest\b",
    r"\bpolice station\b",
    r"\bsection\b",
    r"\bversus\b",
    r"\bapplicant\b",
    r"\brespondent\b",
]

HEADER_NOISE_PATTERNS = [
    r"particulars of document",
    r"annexures",
    r"page nos",
    r"\bs\.?no\b",
]

ANNEX_RE = re.compile(r"^[A-Z]+-\d{1,3}$")
DESC_MIN_LEN = 4


def normalize_desc(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text


def valid_description(desc: str) -> bool:
    d = normalize_desc(desc).lower()

    if len(d) < DESC_MIN_LEN:
        return False

    if re.fullmatch(r"[\d\W]+", d):
        return False

    for pat in HEADER_NOISE_PATTERNS:
        if re.search(pat, d):
            return False

    for pat in BANNED_DESC_PATTERNS:
        if re.search(pat, d):
            return False

    return True


def valid_annexure(value: str | None) -> bool:
    if not value:
        return True
    v = value.strip().upper()
    return bool(ANNEX_RE.fullmatch(v))


def valid_page_range(row: IndexRow, max_pdf_pages: int) -> bool:
    if row.page_start is None and row.page_end is None:
        return row.row_no == 1

    if row.page_start is None or row.page_end is None:
        return False

    if row.page_start < 1 or row.page_end < 1:
        return False
    if row.page_start > row.page_end:
        return False
    if row.page_end > max_pdf_pages:
        return False

    return True


def row_confidence_bonus(row: IndexRow) -> float:
    score = float(row.confidence or 0.0)

    if row.row_no is not None:
        score += 0.10

    if valid_description(row.description):
        score += 0.20

    if valid_annexure(row.annexure):
        score += 0.05

    if row.page_start is not None and row.page_end is not None:
        score += 0.15

    desc = normalize_desc(row.description).lower()

    if row.row_no == 1 and "index" in desc:
        score += 0.10

    if len(desc) >= 12:
        score += 0.05

    return min(score, 1.0)


def validate_rows(rows: List[IndexRow], max_pdf_pages: int) -> List[IndexRow]:
    cleaned: List[IndexRow] = []
    seen = set()

    for row in rows:
        row.description = normalize_desc(row.description)
        row.annexure = row.annexure.strip().upper() if row.annexure else None

        if row.row_no is None and not row.description:
            continue

        if row.row_no is not None and row.row_no in seen:
            continue

        if not valid_description(row.description):
            continue

        page_ok = valid_page_range(row, max_pdf_pages)
        annex_ok = valid_annexure(row.annexure)

        row.confidence = row_confidence_bonus(row)

        if not page_ok or not annex_ok or row.confidence < 0.82:
            row.review_required = True
        else:
            row.review_required = False

        if row.row_no is not None:
            seen.add(row.row_no)

        cleaned.append(row)

    cleaned.sort(key=lambda r: r.row_no or 9999)
    return cleaned
