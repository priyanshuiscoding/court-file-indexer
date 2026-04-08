from __future__ import annotations

from pathlib import Path
import fitz
from PIL import Image
from app.core.config import get_settings

settings = get_settings()


class PDFRenderService:
    def __init__(self) -> None:
        self.render_root = Path(settings.RENDER_STORAGE_DIR)
        self.render_root.mkdir(parents=True, exist_ok=True)

    def render_pages(self, document_id: int, pdf_path: str, start_page: int, end_page: int) -> list[dict]:
        doc_dir = self.render_root / str(document_id)
        doc_dir.mkdir(parents=True, exist_ok=True)

        results: list[dict] = []
        zoom = settings.OCR_RENDER_DPI / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        with fitz.open(pdf_path) as pdf:
            total = len(pdf)
            start_page = max(1, start_page)
            end_page = min(end_page, total)

            for page_no in range(start_page, end_page + 1):
                page = pdf[page_no - 1]
                pix = page.get_pixmap(matrix=matrix, alpha=False)
                out_path = doc_dir / f"page_{page_no}.{settings.OCR_RENDER_FORMAT}"
                pix.save(str(out_path))
                with Image.open(out_path) as img:
                    width, height = img.size
                results.append(
                    {
                        "page_no": page_no,
                        "image_path": str(out_path),
                        "width": width,
                        "height": height,
                    }
                )
        return results
