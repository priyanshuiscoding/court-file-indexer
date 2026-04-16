from __future__ import annotations

import json
import re
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.document import Document

settings = get_settings()


class IntegrationResultService:
    def normalize_case_key(self, case_key: str) -> str:
        value = (case_key or "").strip().upper()
        value = value.replace("/", "-").replace("_", "-")
        value = re.sub(r"[^A-Z0-9-]", "", value)
        value = re.sub(r"-+", "-", value).strip("-")
        return value

    def derive_case_key_from_file_name(self, file_name: str) -> str | None:
        stem = Path(file_name).stem.upper()
        stem = stem.replace("/", "-").replace("_", "-")
        stem = re.sub(r"-+", "-", stem).strip("-")
        parts = stem.split("-")
        if len(parts) >= 3:
            return f"{parts[0]}-{parts[1]}-{parts[2]}"
        return None

    def get_by_case_key(self, db: Session, case_key: str) -> Document | None:
        normalized = self.normalize_case_key(case_key)

        doc = (
            db.query(Document)
            .filter(Document.case_key == normalized)
            .order_by(Document.created_at.desc())
            .first()
        )
        if doc:
            return doc

        docs = (
            db.query(Document)
            .filter(Document.file_name.isnot(None))
            .order_by(Document.created_at.desc())
            .all()
        )
        for item in docs:
            derived = self.derive_case_key_from_file_name(item.file_name)
            if derived == normalized:
                return item

        return None

    def resolve_json_path(self, document: Document) -> Path | None:
        if document.index_json_path:
            path = Path(document.index_json_path)
            if path.exists():
                return path

        export_dir = Path(settings.EXPORT_STORAGE_DIR) / "index_json"
        if not export_dir.exists():
            return None

        if document.case_key:
            candidates = list(export_dir.glob(f"*{document.case_key}*.json"))
            if candidates:
                return sorted(candidates)[-1]

        file_stem = Path(document.file_name).stem
        candidates = list(export_dir.glob(f"*{file_stem}*.json"))
        if candidates:
            return sorted(candidates)[-1]

        candidates = list(export_dir.glob(f"*{document.id}*.json"))
        if candidates:
            return sorted(candidates)[-1]

        return None

    def load_index_json(self, document: Document) -> dict | None:
        path = self.resolve_json_path(document)
        if not path or not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def infer_status(self, document: Document, json_data: dict | None) -> str:
        if json_data is not None:
            return "READY"
        if document.status in {"FAILED", "REVIEW_REQUIRED"}:
            return document.status
        return "PROCESSING"
