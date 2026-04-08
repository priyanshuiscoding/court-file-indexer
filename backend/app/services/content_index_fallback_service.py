from __future__ import annotations

import re
from app.utils.text_normalizer import normalize_text


class ContentIndexFallbackService:
    def build_proposed_index(self, ocr_pages: list[dict]) -> list[dict]:
        rows: list[dict] = []
        serial = 1
        for page in ocr_pages:
            text = normalize_text(page.get("text", ""))
            if not text:
                continue
            title = self._guess_page_title(text)
            rows.append(
                {
                    "row_no": serial,
                    "source_page_no": page["page_no"],
                    "description_raw": title,
                    "description_normalized": title,
                    "annexure_no": None,
                    "page_from": page["page_no"],
                    "page_to": page["page_no"],
                    "total_pages": 1,
                    "extraction_confidence": 0.35,
                    "generated_from_content": True,
                }
            )
            serial += 1
        return rows

    def _guess_page_title(self, text: str) -> str:
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        first_lines = " ".join(lines[:3])
        first_lines = re.sub(r"\s+", " ", first_lines).strip()
        return first_lines[:180] if first_lines else "Generated content row"
