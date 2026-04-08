from __future__ import annotations

import re
from typing import List


INDEX_HINTS = [
    "index",
    "particulars of document",
    "annexures",
    "page nos",
    "s.no",
]


def normalize_text(text: str) -> str:
    text = text.lower()
    text = text.replace("\n", " ")
    text = re.sub(r"[^a-z0-9./\-\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_index_page(text: str) -> int:
    t = normalize_text(text)
    score = 0

    if "index" in t:
        score += 3
    if "particulars of document" in t:
        score += 3
    if "annexures" in t:
        score += 2
    if "page nos" in t or "page no" in t:
        score += 2
    if "s.no" in t or "s no" in t:
        score += 1

    return score


def detect_index_pages(page_texts: List[str], min_score: int = 4) -> List[int]:
    matched = []
    for i, text in enumerate(page_texts):
        score = score_index_page(text)
        if score >= min_score:
            matched.append(i)

    return matched
