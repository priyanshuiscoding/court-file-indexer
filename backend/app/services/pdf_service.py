from __future__ import annotations

from app.utils.pdf_utils import get_pdf_page_count


class PdfService:
    def count_pages(self, path: str) -> int:
        return get_pdf_page_count(path)
