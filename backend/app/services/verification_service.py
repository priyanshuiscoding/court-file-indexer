from app.utils.text_normalizer import normalize_for_match


class VerificationService:
    def verify_index_rows(self, rows: list[dict], ocr_pages: list[dict], total_pdf_pages: int | None = None) -> list[dict]:
        joined = {p["page_no"]: normalize_for_match(p.get("text", "")) for p in ocr_pages}
        verified = []

        for row in rows:
            score = 0.30
            page_from = row.get("page_from")
            page_to = row.get("page_to")
            desc = normalize_for_match(row.get("description_normalized") or "")
            tokens = [t for t in desc.split() if len(t) > 3][:7]

            if page_from is not None and page_from in joined:
                score += 0.10
                page_text = joined[page_from]
                hits = sum(1 for token in tokens if token in page_text)
                score += min(0.40, hits * 0.08)

            if total_pdf_pages and page_to and page_to <= total_pdf_pages:
                score += 0.10

            if page_from and page_to and page_from <= page_to:
                score += 0.10

            if row.get("mapped_document_type"):
                score += 0.05
            if row.get("mapped_sub_document_type"):
                score += 0.05

            row["verification_confidence"] = min(0.95, round(score, 3))
            verified.append(row)

        return verified
