from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class HighCourtPDFResolverService:
    def __init__(self) -> None:
        self.root = Path(settings.HC_MOUNT_ROOT)

    def _clean_batch_no(self, batch_no: str | int) -> str:
        value = str(batch_no).strip()
        value = value.replace(",", "")
        value = value.replace(" ", "")
        return value

    def resolve_pdf(self, batch_no: str | int) -> Optional[Path]:
        batch = self._clean_batch_no(batch_no)
        if not batch:
            logger.error("[HC_IMPORT] batch_no=%s resolved_path=<empty> exists=false pdf_count=0 reason=empty_batch_no", batch_no)
            return None

        base_path = self.root / batch
        exists = base_path.exists()
        logger.info(
            "[HC_IMPORT] batch_no=%s resolved_path=%s exists=%s",
            batch,
            base_path,
            exists,
        )

        if not exists:
            logger.error(
                "[HC_IMPORT] batch_no=%s resolved_path=%s exists=false pdf_count=0 reason=path_not_found",
                batch,
                base_path,
            )
            return None

        # Rare case: resolved path is already a direct PDF file.
        if base_path.is_file():
            if base_path.suffix.lower() == ".pdf":
                logger.info(
                    "[HC_IMPORT] batch_no=%s resolved_path=%s exists=true pdf_count=1 selected=%s mode=direct_file",
                    batch,
                    base_path,
                    base_path.name,
                )
                return base_path

            logger.error(
                "[HC_IMPORT] batch_no=%s resolved_path=%s exists=true pdf_count=0 reason=file_not_pdf",
                batch,
                base_path,
            )
            return None

        if not base_path.is_dir():
            logger.error(
                "[HC_IMPORT] batch_no=%s resolved_path=%s exists=true pdf_count=0 reason=unknown_path_type",
                batch,
                base_path,
            )
            return None

        pdfs = self._find_pdfs(base_path)
        pdf_count = len(pdfs)
        logger.info(
            "[HC_IMPORT] batch_no=%s resolved_path=%s exists=true pdf_count=%s mode=directory_scan",
            batch,
            base_path,
            pdf_count,
        )

        if not pdfs:
            logger.error(
                "[HC_IMPORT] batch_no=%s resolved_path=%s exists=true pdf_count=0 reason=no_pdfs_found",
                batch,
                base_path,
            )
            return None

        # Pick latest modified PDF.
        pdfs.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        selected = pdfs[0]
        logger.info(
            "[HC_IMPORT] batch_no=%s resolved_path=%s exists=true pdf_count=%s selected=%s selected_mtime=%s",
            batch,
            base_path,
            pdf_count,
            selected,
            int(selected.stat().st_mtime),
        )
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
