from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.core.strict_index_pipeline import run_strict_index_pipeline
from app.models.document import Document
from app.models.index_row import IndexRow
from app.services.index_display_mapping_service import IndexDisplayMappingService
from app.services.page_service import PageService


class IndexPipelineService:
    def __init__(self) -> None:
        self.page_service = PageService()
        self.mapper = IndexDisplayMappingService()

    def process_document(self, db: Session, document: Document) -> list[IndexRow]:
        pages = self.page_service.get_pages(db, document.id)
        payloads: list[dict] = []

        for p in pages:
            lines = []
            text = p.ocr_text or ""
            if p.ocr_json_path:
                path = Path(p.ocr_json_path)
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                    lines = data.get("lines", [])
                    text = data.get("text", text)

            payloads.append(
                {
                    "page_no": p.page_no,
                    "width": p.width,
                    "height": p.height,
                    "text": text,
                    "lines": lines,
                }
            )

        result = run_strict_index_pipeline(payloads, document.page_count)

        db.execute(delete(IndexRow).where(IndexRow.document_id == document.id))
        db.flush()

        rows: list[IndexRow] = []
        for row in result["rows"]:
            _, _, display = self.mapper.build_display_value(row.get("description") or "", row.get("annexure"))

            item = IndexRow(
                document_id=document.id,
                row_no=row.get("row_no"),
                source_page_no=row.get("source_page"),
                description_raw=row.get("description") or "",
                description_normalized=row.get("description") or "",
                annexure_no=row.get("annexure"),
                page_from=row.get("page_start"),
                page_to=row.get("page_end"),
                mapped_document_type=display,
                extraction_confidence=float(row.get("confidence") or 0.0),
                verification_confidence=float(row.get("confidence") or 0.0),
                status="REVIEW" if row.get("review_required") else "AUTO_OK",
            )
            db.add(item)
            rows.append(item)

        db.flush()
        return rows
