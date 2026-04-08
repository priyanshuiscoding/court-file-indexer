from __future__ import annotations

import re
from app.core.config import get_settings
from app.core.constants import INDEX_KEYWORDS_EN, INDEX_KEYWORDS_HI
from app.utils.text_normalizer import normalize_for_match

settings = get_settings()


class IndexDetectionService:
    def score_page(self, page: dict) -> dict:
        text = page.get("text", "") or ""
        text_norm = normalize_for_match(text)
        lines = page.get("lines", []) or []

        heading_score = 0.0
        table_score = 0.0
        page_number_score = 0.0
        annexure_score = 0.0
        serial_score = 0.0

        for kw in INDEX_KEYWORDS_EN:
            if normalize_for_match(kw) in text_norm:
                heading_score += 1.2
        for kw in INDEX_KEYWORDS_HI:
            if kw in text:
                heading_score += 1.2

        line_texts = [normalize_for_match(line["text"]) for line in lines]
        serial_hits = sum(1 for lt in line_texts if re.match(r"^\d+[\.)]?$", lt) or re.match(r"^\d+[\.)]?\s", lt))
        serial_score += min(3.0, serial_hits * 0.25)

        page_range_hits = len(re.findall(r"\b\d+\s*[-–]\s*\d+\b", text))
        single_page_hits = len(re.findall(r"\bpage\s*no\b|\bpages\b|\bपृष्ठ\b", text_norm))
        page_number_score += min(3.0, page_range_hits * 0.7 + single_page_hits * 0.5)

        annexure_hits = len(re.findall(r"\b[A-ZА-Я]?[PCAV][-\/]?\d+\b", text, flags=re.IGNORECASE))
        annexure_score += min(2.0, annexure_hits * 0.5)

        table_markers = [
            "annexure",
            "particulars",
            "description of documents",
            "page no",
            "s no",
            "sr no",
            "क्रमांक",
            "दस्तावेज",
            "पृष्ठ",
        ]
        for marker in table_markers:
            if normalize_for_match(marker) in text_norm or marker in text:
                table_score += 0.8

        total_score = heading_score + table_score + page_number_score + annexure_score + serial_score
        return {
            **page,
            "heading_score": round(heading_score, 3),
            "table_score": round(table_score, 3),
            "page_number_score": round(page_number_score, 3),
            "annexure_score": round(annexure_score, 3),
            "serial_score": round(serial_score, 3),
            "index_candidate_score": round(total_score, 3),
        }

    def detect_index_pages(self, ocr_pages: list[dict]) -> list[dict]:
        scored = [self.score_page(page) for page in ocr_pages]
        scored.sort(key=lambda x: x["index_candidate_score"], reverse=True)
        return scored

    def choose_primary_and_continuations(self, candidates: list[dict]) -> list[dict]:
        if not candidates:
            return []
        best = candidates[0]
        if best["index_candidate_score"] < settings.INDEX_MIN_CANDIDATE_SCORE:
            return []

        selected = [best]
        best_page_no = best["page_no"]
        page_map = {c["page_no"]: c for c in candidates}

        for next_page_no in [best_page_no + 1, best_page_no + 2]:
            candidate = page_map.get(next_page_no)
            if candidate and candidate["index_candidate_score"] >= settings.INDEX_CONTINUATION_MIN_SCORE:
                selected.append(candidate)

        selected.sort(key=lambda x: x["page_no"])
        return selected
