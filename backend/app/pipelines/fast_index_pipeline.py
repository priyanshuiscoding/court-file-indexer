import json
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.strict_index_pipeline import run_strict_index_pipeline
from app.models.document import Document
from app.models.index_row import IndexRow
from app.pipelines.ocr_pipeline import OCRPipeline
from app.services.index_display_mapping_service import IndexDisplayMappingService


class FastIndexPipeline:
    def __init__(self):
        self.ocr = OCRPipeline()
        self.mapper = IndexDisplayMappingService()

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

        for row in result["rows"]:
            _, _, display = self.mapper.build_display_value(row["description"], row.get("annexure"))

            db.add(
                IndexRow(
                    document_id=document.id,
                    row_no=row["row_no"],
                    description_raw=row["description"],
                    description_normalized=row["description"],
                    annexure_no=row["annexure"],
                    page_from=row["page_start"],
                    page_to=row["page_end"],
                    mapped_document_type=display,
                    extraction_confidence=row["confidence"],
                    verification_confidence=row["confidence"],
                    status="REVIEW" if row["review_required"] else "AUTO_OK",
                )
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
            }

        document.status = "INDEX_READY"
        db.commit()

        return {
            "rows": row_count,
            "pages_used": len(ocr_pages),
            "ok": True,
            "index_pages": result.get("index_pages", []),
            "debug_pages": (result.get("meta") or {}).get("debug_pages", []),
        }
