from __future__ import annotations

from rapidfuzz import fuzz
from app.services.mapping_sheet_service import MappingSheetService
from app.utils.text_normalizer import normalize_for_match


class IndexMappingService:
    def __init__(self) -> None:
        self.sheet_service = MappingSheetService()

    def map_description(self, description: str) -> tuple[str | None, str | None, float]:
        description_norm = normalize_for_match(description)
        if not description_norm:
            return None, None, 0.0

        regex_match = self.sheet_service.match_by_regex(description)
        if regex_match:
            return (
                regex_match["document_type"],
                regex_match["sub_document_type"],
                0.95,
            )

        labels = self.sheet_service.get_labels()
        best = (None, None, 0.0)
        for label in labels:
            score = fuzz.partial_ratio(description_norm, label["lookup_text"]) / 100.0
            if score > best[2]:
                best = (label["document_type"], label["sub_document_type"], score)

        if best[2] < 0.55:
            return None, None, best[2]
        return best
