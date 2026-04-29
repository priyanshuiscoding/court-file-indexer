from __future__ import annotations

from pathlib import Path

from app.core.config import get_settings

settings = get_settings()


class HighCourtPDFResolverService:
    def resolve_pdf(self, batch_no: str | int) -> Path:
        batch = str(batch_no).strip()
        if not batch:
            raise FileNotFoundError("Empty batch_no")

        root = Path(settings.HC_MOUNT_ROOT)
        folder = root / batch

        if not folder.exists():
            raise FileNotFoundError(f"Batch folder not found: {folder}")
        if not folder.is_dir():
            raise FileNotFoundError(f"Batch path is not a directory: {folder}")

        pdfs = [p for p in folder.glob("*.pdf") if p.is_file()]
        if not pdfs:
            pdfs = [p for p in folder.glob("*.PDF") if p.is_file()]
        if not pdfs:
            raise FileNotFoundError(f"No PDF found in batch folder: {folder}")

        return sorted(pdfs, key=lambda p: p.stat().st_size, reverse=True)[0]
