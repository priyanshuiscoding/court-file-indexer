import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.strict_index_pipeline import run_strict_index_pipeline
from app.models.document import Document
from app.models.index_row import IndexRow
from app.pipelines.ocr_pipeline import OCRPipeline
from app.services.index_display_mapping_service import IndexDisplayMappingService
from app.services.index_json_export_service import IndexJSONExportService

logger = logging.getLogger(__name__)


class FastIndexPipeline:
    def __init__(self):
        self.ocr = OCRPipeline()
        self.mapper = IndexDisplayMappingService()
        self.index_json_exporter = IndexJSONExportService()

    def run(self, db: Session, document: Document):
        ocr_pages = self.ocr.run_fast_until_index(db, document)

        payloads = []
        for p in ocr_pages:
            lines = p.get("lines") or []

            if not lines and p.get("ocr_json_path"):
                path = Path(p["ocr_json_path"])
                if path.exists():
                    data = json.loads(path.read_text())
                    lines = data.get("lines", [])

            payloads.append(
                {
                    "page_no": p["page_no"],
                    "width": p.get("width"),
                    "height": p.get("height"),
                    "text": p.get("text"),
                    "lines": lines,
                }
            )

        result = run_strict_index_pipeline(payloads, document.page_count)

        # clear old rows
        db.query(IndexRow).filter(IndexRow.document_id == document.id).delete()

        json_rows: list[dict] = []

        for row in result["rows"]:
            _, _, display = self.mapper.build_display_value(row["description"], row.get("annexure"))

            db_row = IndexRow(
                document_id=document.id,
                row_no=row["row_no"],
                source_page_no=row.get("source_page"),
                description_raw=row["description"],
                description_normalized=row["description"],
                annexure_no=row["annexure"],
                page_from=row["page_start"],
                page_to=row["page_end"],
                total_pages=(row["page_end"] - row["page_start"] + 1)
                if row.get("page_start") is not None and row.get("page_end") is not None
                else None,
                mapped_document_type=display,
                mapped_sub_document_type=None,
                receiving_date=None,
                extraction_confidence=row["confidence"],
                verification_confidence=row["confidence"],
                status="REVIEW" if row["review_required"] else "AUTO_OK",
            )
            db.add(db_row)

            json_rows.append(
                {
                    "row_no": row.get("row_no"),
                    "source_page_no": row.get("source_page"),
                    "description": row.get("description"),
                    "annexure_no": row.get("annexure"),
                    "page_from": row.get("page_start"),
                    "page_to": row.get("page_end"),
                    "receiving_date": None,
                    "mapped_document_type": display,
                    "mapped_sub_document_type": None,
                    "extraction_confidence": row.get("confidence"),
                    "verification_confidence": row.get("confidence"),
                    "status": "REVIEW" if row.get("review_required") else "AUTO_OK",
                    "raw_text": row.get("raw_text"),
                    "others": {},
                }
            )

        row_count = len(result["rows"])
        if row_count == 0:
            document.status = "REVIEW_REQUIRED"
            document.current_step = "No index rows found"
            db.commit()
            return {
                "rows": 0,
                "pages_used": len(ocr_pages),
                "ok": False,
                "index_pages": result.get("index_pages", []),
                "debug_pages": (result.get("meta") or {}).get("debug_pages", []),
                "index_json_path": None,
            }

        document.status = "INDEX_READY"
        db.commit()

        index_json_path = None
        try:
            index_json_path = self.index_json_exporter.save_index_json(document, json_rows)
        except Exception:
            # Export is non-blocking; do not stop pipeline progression.
            logger.exception("Failed to export index JSON for document_id=%s", document.id)

        return {
            "rows": row_count,
            "pages_used": len(ocr_pages),
            "ok": True,
            "index_pages": result.get("index_pages", []),
            "debug_pages": (result.get("meta") or {}).get("debug_pages", []),
            "index_json_path": index_json_path,
        }
