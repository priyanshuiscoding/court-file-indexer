from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.strict_index_pipeline import StrictIndexingError, run_strict_index_pipeline
from app.models.index_row import IndexRow
from app.schemas.document import ManualScanRequest, StartIndexingRequest
from app.schemas.index_row import IndexRowOut, IndexRowUpdate
from app.services.document_service import DocumentService
from app.services.index_display_mapping_service import IndexDisplayMappingService
from app.services.page_service import PageService
from app.tasks.document_tasks import enqueue_document_pipeline

router = APIRouter(prefix="/indexing", tags=["indexing"])

document_service = DocumentService()
page_service = PageService()
display_mapper = IndexDisplayMappingService()


class StrictIndexingRequest(BaseModel):
    start_page: int | None = None
    end_page: int | None = None
    replace_existing_rows: bool = True


class IndexRowCreate(BaseModel):
    row_no: int | None = None
    description_raw: str
    annexure_no: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    mapped_document_type: str | None = None
    extraction_confidence: float | None = 0.0
    verification_confidence: float | None = 0.0
    status: str = "REVIEW"


def _enqueue_or_raise(db: Session, document_id: int) -> dict:
    result = enqueue_document_pipeline(db, document_id)
    if result.get("ok"):
        return result

    reason = result.get("reason")
    if reason == "already_completed":
        raise HTTPException(status_code=409, detail=result.get("message") or "Indexing already completed")
    if reason == "already_running":
        raise HTTPException(status_code=409, detail=result.get("message") or "Indexing already running")
    raise HTTPException(status_code=404, detail="Document not found")


@router.post("/{document_id}/start")
def start_indexing(document_id: int, payload: StartIndexingRequest, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    tasks = _enqueue_or_raise(db, document_id)
    return {"ok": True, "message": "Fast indexing started", "document_id": document_id, **tasks}


@router.post("/{document_id}/manual-scan")
def manual_scan(document_id: int, payload: ManualScanRequest, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    tasks = _enqueue_or_raise(db, document_id)
    return {"message": "Manual scan indexing started", "document_id": document_id, **tasks}


@router.post("/{document_id}/strict")
def strict_indexing(document_id: int, payload: StrictIndexingRequest, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    pages = page_service.get_pages(db, document_id)
    if not pages:
        raise HTTPException(
            status_code=400,
            detail="No OCR pages found for this document. Run /indexing/{document_id}/start first.",
        )

    start_page = payload.start_page or 1
    end_page = payload.end_page or document.page_count
    if start_page < 1 or end_page < start_page:
        raise HTTPException(status_code=400, detail="Invalid page range")

    selected_pages = [p for p in pages if start_page <= p.page_no <= end_page]
    if not selected_pages:
        raise HTTPException(status_code=400, detail="No OCR pages in selected range")

    page_payloads = _build_page_payloads_from_db_pages(selected_pages)

    try:
        strict_result = run_strict_index_pipeline(page_payloads=page_payloads, max_pdf_pages=document.page_count)
    except StrictIndexingError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Strict indexing failed: {exc}") from exc

    if payload.replace_existing_rows:
        db.execute(delete(IndexRow).where(IndexRow.document_id == document_id))
        db.commit()

    saved_count = 0
    review_count = 0
    for row in strict_result["rows"]:
        _, _, mapped_display = display_mapper.build_display_value(
            row.get("description") or "",
            row.get("annexure"),
        )

        row_status = "REVIEW" if row["review_required"] else "AUTO_OK"
        if row_status == "REVIEW":
            review_count += 1

        page_from = row.get("page_start")
        page_to = row.get("page_end")
        total_pages = None
        if page_from is not None and page_to is not None and page_to >= page_from:
            total_pages = page_to - page_from + 1

        db_row = IndexRow(
            document_id=document_id,
            row_no=row.get("row_no"),
            source_page_no=row.get("source_page"),
            description_raw=row.get("description") or "",
            description_normalized=row.get("description") or "",
            annexure_no=row.get("annexure"),
            page_from=page_from,
            page_to=page_to,
            total_pages=total_pages,
            mapped_document_type=mapped_display,
            mapped_sub_document_type=None,
            extraction_confidence=float(row.get("confidence") or 0.0),
            verification_confidence=float(row.get("confidence") or 0.0),
            status=row_status,
            generated_from_content=False,
        )
        db.add(db_row)
        saved_count += 1

    if saved_count == 0:
        document.status = "REVIEW_REQUIRED"
        document.current_step = "Strict extraction found no valid rows"
    elif review_count > 0:
        document.status = "REVIEW_REQUIRED"
        document.current_step = "Strict extraction complete; review required"
    else:
        document.status = "INDEX_PARSED"
        document.current_step = "Strict extraction complete"

    db.add(document)
    db.commit()

    return {
        "ok": True,
        "document_id": document_id,
        "saved_rows": saved_count,
        "review_rows": review_count,
        "result": strict_result,
    }


@router.get("/{document_id}/rows", response_model=list[IndexRowOut])
def get_index_rows(document_id: int, db: Session = Depends(get_db)):
    rows = db.query(IndexRow).filter(IndexRow.document_id == document_id).order_by(IndexRow.row_no.asc()).all()
    return rows


@router.post("/{document_id}/rows", response_model=IndexRowOut)
def create_index_row(document_id: int, payload: IndexRowCreate, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    total_pages = None
    if payload.page_from is not None and payload.page_to is not None and payload.page_to >= payload.page_from:
        total_pages = payload.page_to - payload.page_from + 1

    mapped_display = payload.mapped_document_type
    if not mapped_display:
        _, _, mapped_display = display_mapper.build_display_value(payload.description_raw, payload.annexure_no)

    row = IndexRow(
        document_id=document_id,
        row_no=payload.row_no,
        description_raw=payload.description_raw,
        description_normalized=payload.description_raw,
        annexure_no=payload.annexure_no,
        page_from=payload.page_from,
        page_to=payload.page_to,
        total_pages=total_pages,
        mapped_document_type=mapped_display,
        mapped_sub_document_type=None,
        extraction_confidence=payload.extraction_confidence or 0.0,
        verification_confidence=payload.verification_confidence or 0.0,
        status=payload.status,
        generated_from_content=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.put("/rows/{row_id}", response_model=IndexRowOut)
def update_index_row(row_id: int, payload: IndexRowUpdate, db: Session = Depends(get_db)):
    row = db.get(IndexRow, row_id)
    if not row:
        raise HTTPException(status_code=404, detail="Index row not found")

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(row, field, value)

    if "description_raw" in update_data or "annexure_no" in update_data:
        _, _, mapped_display = display_mapper.build_display_value(row.description_raw or "", row.annexure_no)
        row.mapped_document_type = mapped_display
        row.mapped_sub_document_type = None

    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/rows/{row_id}")
def delete_index_row(row_id: int, db: Session = Depends(get_db)):
    row = db.query(IndexRow).filter(IndexRow.id == row_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Row not found")

    db.delete(row)
    db.commit()
    return {"ok": True, "deleted_row_id": row_id}


def _build_page_payloads_from_db_pages(pages: list) -> list[dict]:
    payloads: list[dict] = []

    for page in pages:
        lines = []
        text = page.ocr_text or ""

        if page.ocr_json_path:
            json_path = Path(page.ocr_json_path)
            if json_path.exists():
                data = json.loads(json_path.read_text(encoding="utf-8"))
                lines = data.get("lines") or []
                text = data.get("text") or text

        payloads.append(
            {
                "page_no": page.page_no,
                "width": page.width,
                "height": page.height,
                "text": text,
                "lines": lines,
            }
        )

    payloads.sort(key=lambda p: p["page_no"])
    return payloads
