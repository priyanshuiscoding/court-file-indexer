from __future__ import annotations

import base64
import binascii
import re
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document
from app.tasks.document_tasks import enqueue_document_pipeline
from app.utils.pdf_utils import get_pdf_page_count

settings = get_settings()


class Base64IngestService:
    def _normalize_case_key(self, case_type: str, case_no: str, case_year: int | str) -> str:
        ctype = re.sub(r"[^A-Za-z0-9]+", "", str(case_type or "")).upper()
        cno = re.sub(r"[^A-Za-z0-9]+", "", str(case_no or "")).upper()
        cyear = re.sub(r"[^0-9]+", "", str(case_year or ""))
        if not ctype or not cno or not cyear:
            raise ValueError("case_type, case_no, and case_year are required")
        return f"{ctype}-{cno}-{cyear}"

    def _decode_base64(self, base64_str: str) -> bytes:
        if not base64_str or not base64_str.strip():
            raise ValueError("base64_pdf is required")

        value = base64_str.strip()
        if "," in value and value.lower().startswith("data:"):
            value = value.split(",", 1)[1]

        try:
            data = base64.b64decode(value, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid base64_pdf") from exc

        if not data:
            raise ValueError("Decoded PDF is empty")
        return data

    def _save_pdf(self, case_key: str, pdf_bytes: bytes) -> str:
        pdf_dir = Path(settings.PDF_STORAGE_DIR)
        pdf_dir.mkdir(parents=True, exist_ok=True)
        target = pdf_dir / f"{case_key}.pdf"
        target.write_bytes(pdf_bytes)
        return str(target)

    def _check_duplicate(self, db: Session, case_key: str) -> Document | None:
        return (
            db.query(Document)
            .filter(Document.case_key == case_key)
            .order_by(Document.created_at.desc())
            .first()
        )

    def ingest_one(
        self,
        db: Session,
        *,
        case_type: str,
        case_no: str,
        case_year: int,
        base64_pdf: str,
        overwrite: bool = False,
        source_system: str = "manual_test",
    ) -> dict[str, Any]:
        case_key = self._normalize_case_key(case_type, case_no, case_year)

        duplicate = self._check_duplicate(db, case_key)
        if duplicate and not overwrite:
            return {
                "case_key": case_key,
                "status": "skipped_duplicate",
                "document_id": duplicate.id,
            }

        pdf_bytes = self._decode_base64(base64_pdf)
        saved_path = self._save_pdf(case_key, pdf_bytes)

        try:
            page_count = get_pdf_page_count(saved_path)
        except Exception as exc:
            raise ValueError("Decoded content is not a valid PDF") from exc

        document = Document(
            file_name=f"{case_key}.pdf",
            original_path=saved_path,
            page_count=page_count,
            cnr_number=None,
            case_type=str(case_type).upper(),
            case_no=str(case_no),
            case_year=str(case_year),
            case_key=case_key,
            source_system=source_system,
            status="UPLOADED",
            current_step="Base64 Ingested",
        )
        db.add(document)
        db.commit()
        db.refresh(document)

        enqueue_result = enqueue_document_pipeline(db, document.id)
        if not enqueue_result.get("ok"):
            return {
                "case_key": case_key,
                "status": "enqueue_failed",
                "document_id": document.id,
                "message": enqueue_result.get("message") or enqueue_result.get("reason") or "Enqueue failed",
            }

        return {
            "case_key": case_key,
            "status": "queued",
            "document_id": document.id,
        }

    def ingest_batch(
        self,
        db: Session,
        documents: list[dict[str, Any]],
        overwrite: bool = False,
        source_system: str = "manual_test",
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in documents:
            try:
                result = self.ingest_one(
                    db,
                    case_type=str(item.get("case_type", "")),
                    case_no=str(item.get("case_no", "")),
                    case_year=int(item.get("case_year")),
                    base64_pdf=str(item.get("base64_pdf", "")),
                    overwrite=overwrite,
                    source_system=source_system,
                )
                results.append(result)
            except Exception as exc:
                case_type = str(item.get("case_type", "")).upper() if item.get("case_type") is not None else ""
                case_no = str(item.get("case_no", "")) if item.get("case_no") is not None else ""
                case_year = str(item.get("case_year", "")) if item.get("case_year") is not None else ""
                case_key = f"{case_type}-{case_no}-{case_year}".strip("-")
                results.append(
                    {
                        "case_key": case_key,
                        "status": "failed",
                        "document_id": None,
                        "error": str(exc),
                    }
                )
        return results
