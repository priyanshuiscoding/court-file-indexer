from __future__ import annotations


class OCRMergeService:
    def merge_primary_and_fallback(self, primary_pages: list[dict], fallback_pages: list[dict]) -> list[dict]:
        fallback_by_page = {p["page_no"]: p for p in fallback_pages}
        merged: list[dict] = []

        for page in primary_pages:
            fallback = fallback_by_page.get(page["page_no"])
            use_fallback = False
            if fallback:
                primary_text = page.get("text", "") or ""
                primary_conf = float(page.get("confidence", 0.0) or 0.0)
                fallback_text = fallback.get("text", "") or ""
                fallback_conf = float(fallback.get("confidence", 0.0) or 0.0)

                if self._looks_hindi_heavy(fallback_text) and (fallback_conf >= primary_conf or len(fallback_text) > len(primary_text) * 1.15):
                    use_fallback = True
                elif primary_conf < 0.45 and fallback_conf > primary_conf:
                    use_fallback = True

            merged.append(fallback if use_fallback else page)
        return merged

    def _looks_hindi_heavy(self, text: str) -> bool:
        devanagari_count = sum(1 for ch in text if "\u0900" <= ch <= "\u097F")
        return devanagari_count >= 8
