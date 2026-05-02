from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HighCourtPDFResolverService:
    def _clean_batch_no(self, batch_no: str | int) -> str:
        value = str(batch_no).strip()
        value = value.replace(",", "")
        value = value.replace(" ", "")
        return value

    def resolve_pdf(self, batch_no: str | int) -> Path:
        batch = self._clean_batch_no(batch_no)
        if not batch:
            raise FileNotFoundError("Empty batch_no")

        root = Path(settings.HC_MOUNT_ROOT)

        if not root.exists():
            raise FileNotFoundError(f"HC_MOUNT_ROOT not found: {root}")

        if not root.is_dir():
            raise FileNotFoundError(f"HC_MOUNT_ROOT is not directory: {root}")

        folder = root / batch

        if not folder.exists():
            raise FileNotFoundError(f"Batch folder not found: {folder}")
        if not folder.is_dir():
            raise FileNotFoundError(f"Batch path is not directory: {folder}")

        pdfs = self._find_pdfs(folder)
        if not pdfs:
            raise FileNotFoundError(f"No PDF found in batch folder: {folder}")

        # Choose largest PDF because final cleaned PDF is usually the largest.
        pdfs = sorted(pdfs, key=lambda p: p.stat().st_size if p.exists() else 0, reverse=True)

        selected = pdfs[0]
        logger.info("Resolved High Court PDF batch_no=%s path=%s", batch, selected)
        return selected

    def _find_pdfs(self, folder: Path) -> list[Path]:
        pdfs: list[Path] = []

        # Direct PDFs first.
        for pattern in ("*.pdf", "*.PDF", "*.Pdf"):
            pdfs.extend([p for p in folder.glob(pattern) if p.is_file()])

        if pdfs:
            return self._unique_paths(pdfs)

        if not settings.HC_PDF_RESOLVE_RECURSIVE:
            return []

        max_depth = int(settings.HC_PDF_RESOLVE_MAX_DEPTH or 3)

        for path in folder.rglob("*"):
            if not path.is_file():
                continue

            try:
                relative_depth = len(path.relative_to(folder).parts)
            except Exception:
                relative_depth = 999

            if relative_depth > max_depth:
                continue

            if path.suffix.lower() == ".pdf":
                pdfs.append(path)

        return self._unique_paths(pdfs)

    def _unique_paths(self, paths: list[Path]) -> list[Path]:
        seen = set()
        result = []
        for path in paths:
            key = str(path.resolve())
            if key in seen:
                continue
            seen.add(key)
            result.append(path)
        return result
