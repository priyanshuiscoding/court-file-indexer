from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.document import DocumentOut
from app.services.document_service import DocumentService
from app.services.file_storage import FileStorageService
from app.tasks.document_tasks import enqueue_document_pipeline
from app.utils.pdf_utils import get_pdf_page_count

router = APIRouter(prefix="/documents", tags=["documents"])


document_service = DocumentService()
storage_service = FileStorageService()


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


@router.get("/{document_id}/file")
def get_document_file(document_id: int, db: Session = Depends(get_db)):
    document = document_service.get_document(db, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return FileResponse(document.original_path, media_type="application/pdf", filename=document.file_name)
