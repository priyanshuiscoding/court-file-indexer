from __future__ import annotations

import re
from app.utils.text_normalizer import normalize_for_match


JUNK_PATTERNS = [
    r"^in the high court",
    r"^high court of",
    r"^principal seat",
    r"^versus$",
    r"^respondent",
    r"^petitioner",
    r"^applicant",
    r"^counsel",
    r"^jabalpur$",
    r"^dated",
    r"^place",
    r"^received",
    r"^advance copy",
    r"^nil$",
    r"^nil nil",
    r"^index$",
]

GOOD_DESC_HINTS = [
    "petition",
    "affidavit",
    "application",
    "vakalatnama",
    "memo",
    "copy of",
    "order",
    "fir",
    "medical",
    "list of documents",
    "chronology",
    "impugned",
    "शपथ",
    "वकालतनामा",
    "आवेदन",
    "दस्तावेज",
    "आदेश",
]


class RowValidationService:
    def is_valid_row(self, row: dict, page_count: int | None = None) -> tuple[bool, str]:
        desc = normalize_for_match(row.get("description_normalized") or row.get("description_raw") or "")
        page_from = row.get("page_from")
        page_to = row.get("page_to")
        annex = (row.get("annexure_no") or "").strip()
        row_no = row.get("row_no")

        if not desc:
            return False, "empty_description"

        for pattern in JUNK_PATTERNS:
            if re.match(pattern, desc, flags=re.IGNORECASE):
                return False, "junk_pattern"

        if len(desc) < 3:
            return False, "too_short"

        repeated_tokens = desc.split()
        if repeated_tokens and len(set(repeated_tokens)) == 1 and len(repeated_tokens) >= 2:
            return False, "repeated_token_noise"

        has_structure = any(
            [
                row_no is not None,
                page_from is not None,
                bool(annex),
                any(hint in desc for hint in GOOD_DESC_HINTS),
            ]
        )
        if not has_structure:
            return False, "no_row_structure"

        if page_from is not None and page_to is not None:
            if page_from <= 0 or page_to <= 0:
                return False, "bad_page_range"
            if page_from > page_to:
                return False, "bad_page_range"
            if page_count and (page_from > page_count or page_to > page_count):
                return False, "range_outside_pdf"

        if desc.count("nil") >= 2:
            return False, "nil_noise"

        return True, "ok"

    def suspicious_row_count(self, row_count: int) -> bool:
        return row_count <= 0 or row_count > 25
