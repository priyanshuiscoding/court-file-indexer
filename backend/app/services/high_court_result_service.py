from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document
from app.models.high_court_import_job import HighCourtImportJob

settings = get_settings()


class HighCourtResultService:
    def get_job(self, db: Session, batch_no: str) -> HighCourtImportJob | None:
        stmt = select(HighCourtImportJob).where(HighCourtImportJob.batch_no == str(batch_no))
        return db.scalars(stmt).first()

    def get_job_by_fil_no(self, db: Session, fil_no: str) -> HighCourtImportJob | None:
        stmt = select(HighCourtImportJob).where(HighCourtImportJob.fil_no == str(fil_no))
        return db.scalars(stmt).first()

    def get_result(self, db: Session, batch_no: str) -> dict:
        job = self.get_job(db, batch_no)
        if not job:
            return {
                "ok": False,
                "batch_no": str(batch_no),
                "json_ready": False,
                "error": "Batch not found",
            }

        if job.status in {"QUEUED", "PROCESSING"}:
            return {
                "ok": False,
                "status": job.status,
                "message": "Document is still processing",
                "batch_no": job.batch_no,
                "document_id": job.document_id,
                "json_ready": False,
            }

        if job.status in {"FAILED", "DOCUMENT_FAILED", "PDF_NOT_FOUND"}:
            return {
                "ok": False,
                "status": job.status,
                "error": job.error_message,
                "batch_no": job.batch_no,
                "document_id": job.document_id,
                "json_ready": False,
            }

        if job.status not in {"INDEX_READY", "CHAT_READY", "REVIEW_REQUIRED"}:
            return {
                "ok": False,
                "status": job.status,
                "error": "Unknown state",
                "batch_no": job.batch_no,
                "document_id": job.document_id,
                "json_ready": False,
            }

        json_data, json_path = self._load_index_json(db, job)
        if not json_data:
            return {
                "ok": False,
                "status": job.status,
                "error": "Index JSON not found",
                "batch_no": job.batch_no,
                "document_id": job.document_id,
                "json_ready": False,
            }

        return {
            "ok": True,
            "batch_no": job.batch_no,
            "document_id": job.document_id,
            "status": job.status,
            "json_ready": True,
            "json_file": Path(json_path).name if json_path else None,
            "index_json": json_data,
        }

    def _load_index_json(self, db: Session, job: HighCourtImportJob):
        if job.document_id:
            document = db.get(Document, job.document_id)
            if document and document.index_json_path:
                index_path = Path(document.index_json_path)
                if index_path.exists() and index_path.is_file():
                    try:
                        data = json.loads(index_path.read_text(encoding="utf-8"))
                        return data, str(index_path)
                    except Exception:
                        pass

        export_dir = Path(settings.EXPORT_STORAGE_DIR) / "index_json"
        if not export_dir.exists():
            return None, None

        for file in export_dir.glob("*.json"):
            if job.document_id is not None and f"doc_{job.document_id}_" in file.name:
                try:
                    data = json.loads(file.read_text(encoding="utf-8"))
                    return data, str(file)
                except Exception:
                    continue

        for file in export_dir.glob("*.json"):
            if job.batch_no in file.name:
                try:
                    data = json.loads(file.read_text(encoding="utf-8"))
                    return data, str(file)
                except Exception:
                    continue

        return None, None
