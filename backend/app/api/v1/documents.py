from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.chat import ChatMessage
from app.models.document_chat_message import DocumentChatMessage
from app.models.document_page import DocumentPage
from app.models.queue_item import QueueItem
from app.schemas.document import DocumentOut
from app.services.document_service import DocumentService
from app.services.file_storage import FileStorageService
from app.services.qdrant_service import QdrantService
from app.services.queue_service import QueueService
from app.tasks.document_tasks import enqueue_document_pipeline
from app.utils.pdf_utils import get_pdf_page_count

router = APIRouter(prefix="/documents", tags=["documents"])


document_service = DocumentService()
storage_service = FileStorageService()
queue_service = QueueService()
qdrant_service = QdrantService()
settings = get_settings()


class BulkDeleteDocumentsRequest(BaseModel):
    document_ids: list[int] = Field(min_length=1, max_length=500)


def _collect_document_file_paths(db: Session, document_id: int, original_path: str | None) -> set[str]:
    paths: set[str] = set()

    if original_path:
        paths.add(original_path)

    stmt = select(DocumentPage.image_path, DocumentPage.ocr_json_path).where(DocumentPage.document_id == document_id)
    for image_path, ocr_json_path in db.execute(stmt).all():
        if image_path:
            paths.add(image_path)
        if ocr_json_path:
            paths.add(ocr_json_path)

    return paths


def _safe_unlink(path_str: str) -> None:
    storage_root = Path(settings.STORAGE_ROOT).resolve()
    path = Path(path_str)

    try:
        resolved = path.resolve()
    except Exception:
        return

    try:
        resolved.relative_to(storage_root)
    except ValueError:
        # Never unlink outside configured storage root.
        return

    if resolved.exists() and resolved.is_file():
        try:
            resolved.unlink()
        except Exception:
            return


def _delete_document_and_related(db: Session, document_id: int) -> dict:
    document = document_service.get_document(db, document_id)
    if not document:
        return {"ok": False, "reason": "not_found"}

    if queue_service.has_active_for_document(db, document_id):
        return {"ok": False, "reason": "active"}

    paths_to_delete = _collect_document_file_paths(db, document_id, document.original_path)

    # Best-effort vector cleanup in Qdrant.
    qdrant_service.delete_document_points(document_id)

    db.execute(sa_delete(DocumentChatMessage).where(DocumentChatMessage.document_id == document_id))
    db.execute(sa_delete(ChatMessage).where(ChatMessage.document_id == document_id))
    db.execute(sa_delete(QueueItem).where(QueueItem.document_id == document_id))

    db.delete(document)
    db.commit()

    for path in paths_to_delete:
        _safe_unlink(path)

    return {"ok": True, "deleted_document_id": document_id}


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    cnr_number: str | None = Form(default=None),
    batch_no: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    saved_path = await storage_service.save_pdf(file)
    page_count = get_pdf_page_count(saved_path)
    document = document_service.create_document(
        db,
        file_name=file.filename,
        original_path=saved_path,
        page_count=page_count,
        cnr_number=cnr_number,
        batch_no=batch_no,
    )
    return document


@router.post("/batch-upload")
async def batch_upload_documents(
    files: list[UploadFile] = File(...),
    batch_no: str | None = Form(default=None),
    db: Session = Depends(get_db),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files were provided")

    effective_batch_no = (batch_no or "").strip() or f"BATCH_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    created_docs = []
    failed = []

    for file in files:
        filename = file.filename or "unknown.pdf"

        if not filename.lower().endswith(".pdf"):
            failed.append({"file_name": filename, "error": "Only PDF files are allowed"})
            continue

        try:
            saved_path = await storage_service.save_pdf(file)
            page_count = get_pdf_page_count(saved_path)
            doc = document_service.create_document(
                db,
                file_name=filename,
                original_path=saved_path,
                page_count=page_count,
                cnr_number=None,
                batch_no=effective_batch_no,
            )
            created_docs.append(doc)
        except Exception as exc:
            failed.append({"file_name": filename, "error": str(exc)})

    if not created_docs:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Batch upload failed for all files",
                "batch_no": effective_batch_no,
                "failed": failed,
            },
        )

    # Operational control: start only the first FAST_INDEX task now.
    # Next FAST_INDEX jobs are chained by task orchestration.
    enqueue_document_pipeline(db, created_docs[0].id)

    return {
        "ok": len(failed) == 0,
        "batch_no": effective_batch_no,
        "created_count": len(created_docs),
        "failed_count": len(failed),
        "failed": failed,
        "documents": [{"id": d.id, "file_name": d.file_name, "batch_no": d.batch_no} for d in created_docs],
    }


@router.get("", response_model=list[DocumentOut])
def list_documents(
    cnr: str | None = None,
    batch_no: str | None = None,
    db: Session = Depends(get_db),
):
    return document_service.list_documents(db, cnr=cnr, batch_no=batch_no)


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return document


@router.delete("/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    result = _delete_document_and_related(db, document_id)

    if not result["ok"] and result.get("reason") == "not_found":
        raise HTTPException(status_code=404, detail="Document not found")
    if not result["ok"] and result.get("reason") == "active":
        raise HTTPException(status_code=409, detail="Cannot delete document while processing is active")

    return result


@router.post("/delete-bulk")
def delete_documents_bulk(payload: BulkDeleteDocumentsRequest, db: Session = Depends(get_db)):
    document_ids = list(dict.fromkeys(payload.document_ids))

    deleted_document_ids: list[int] = []
    active_document_ids: list[int] = []
    not_found_document_ids: list[int] = []

    for document_id in document_ids:
        result = _delete_document_and_related(db, document_id)
        if result.get("ok"):
            deleted_document_ids.append(document_id)
        elif result.get("reason") == "active":
            active_document_ids.append(document_id)
        elif result.get("reason") == "not_found":
            not_found_document_ids.append(document_id)

    return {
        "ok": True,
        "deleted_count": len(deleted_document_ids),
        "deleted_document_ids": deleted_document_ids,
        "active_document_ids": active_document_ids,
        "not_found_document_ids": not_found_document_ids,
    }


@router.get("/{document_id}/file")
def get_document_file(document_id: int, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(document.original_path, media_type="application/pdf", filename=document.file_name)
