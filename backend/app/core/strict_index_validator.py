from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Tuple

from app.schemas.index_models import IndexRow


BANNED_DESC_PATTERNS = [
    r"whether any bail application",
    r"\bresult\b",
    r"\bcourt\(s\)\b",
    r"\baccused application\b",
    r"\bname of the co\b",
    r"\binstitution date\b",
    r"\bparticular of crime\b",
    r"\bdate of arrest\b",
    r"\bpolice station\b",
    r"\bcounsel\b",
    r"\badvocate\b",
    r"\bdeclaration\b",
    r"\breceived\b",
    r"\bclerk\b",
    r"\bplace\b",
]

HEADER_NOISE_PATTERNS = [
    r"particulars of document",
    r"description of document",
    r"description of documents",
    r"\bparticulars\b",
    r"\bdescription\b",
    r"\bannexures?\b",
    r"\bann\.\b",
    r"\bpage nos?\b",
    r"\bremarks\b",
    r"\bs\.?no\b",
    r"\bsr\.?no\b",
    r"\bsl\.?no\b",
]

ANNEX_RE = re.compile(r"^[A-Z]+-\d{1,3}$")
ANNEX_ONLY_TOKEN_RE = re.compile(r"^[A-Z]+/?\d+$")
DESC_MIN_LEN = 4


def normalize_desc(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:])", r"\1", text)
    return text


def _is_annex_only_description(desc: str) -> bool:
    tokens = [t for t in re.split(r"\s+", desc.upper()) if t]
    if not tokens:
        return False
    return all(ANNEX_ONLY_TOKEN_RE.match(t.replace("-", "")) for t in tokens)


def valid_description(desc: str) -> bool:
    d = normalize_desc(desc).lower()

    if len(d) < DESC_MIN_LEN:
        return False

    if re.fullmatch(r"[\d\W]+", d):
        return False

    if _is_annex_only_description(d):
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
        # First row "Index" may not have explicit pages.
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


def _add_reason(stats: dict, reason: str) -> None:
    drop_reasons = stats["drop_reasons"]
    drop_reasons[reason] = int(drop_reasons.get(reason, 0)) + 1


def _drop_with_reason(stats: dict, reason: str) -> None:
    stats["dropped"] += 1
    _add_reason(stats, reason)


def validate_rows_with_debug(rows: List[IndexRow], max_pdf_pages: int) -> Tuple[List[IndexRow], Dict[int, dict]]:
    cleaned: List[IndexRow] = []
    seen = set()

    stats_by_page: dict = defaultdict(lambda: {"parsed": 0, "dropped": 0, "drop_reasons": {}})

    for row in rows:
        source_page = int(getattr(row, "source_page", 0) or 0)
        stats = stats_by_page[source_page]
        stats["parsed"] += 1

        row.description = normalize_desc(row.description)
        row.annexure = row.annexure.strip().upper() if row.annexure else None

        if row.row_no is None and not row.description:
            _drop_with_reason(stats, "empty_row")
            continue

        if row.row_no is not None and row.row_no in seen:
            _drop_with_reason(stats, "duplicate_row_no")
            continue

        if not valid_description(row.description):
            _drop_with_reason(stats, "invalid_description")
            continue

        page_ok = valid_page_range(row, max_pdf_pages)
        annex_ok = valid_annexure(row.annexure)

        row.confidence = row_confidence_bonus(row)

        if not page_ok:
            row.review_required = True
            _add_reason(stats, "review_bad_page_range")
        elif not annex_ok:
            row.review_required = True
            _add_reason(stats, "review_bad_annexure")
        elif row.confidence < 0.82:
            row.review_required = True
            _add_reason(stats, "review_low_confidence")
        else:
            row.review_required = False

        if row.row_no is not None:
            seen.add(row.row_no)

        cleaned.append(row)

    cleaned.sort(key=lambda r: r.row_no or 9999)

    debug = {int(k): v for k, v in sorted(stats_by_page.items(), key=lambda kv: kv[0])}
    return cleaned, debug


def validate_rows(rows: List[IndexRow], max_pdf_pages: int) -> List[IndexRow]:
    cleaned, _ = validate_rows_with_debug(rows, max_pdf_pages=max_pdf_pages)
    return cleaned
