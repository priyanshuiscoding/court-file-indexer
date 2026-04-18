from pathlib import Path
import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.services.document_service import DocumentService
from app.tasks.document_tasks import enqueue_document_pipeline
from app.utils.pdf_utils import get_pdf_page_count

router = APIRouter(prefix="/test", tags=["test"])

settings = get_settings()
document_service = DocumentService()


@router.post("/base64-upload")
def upload_base64(payload: dict, db: Session = Depends(get_db)):
    try:
        base64_pdf = payload.get("base64_pdf")
        file_name = payload.get("file_name", "test_case.pdf")
        cnr_number = payload.get("cnr_number")
        batch_no = payload.get("batch_no")

        if not base64_pdf:
            raise HTTPException(status_code=400, detail="base64_pdf is required")

        if not file_name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="file_name must end with .pdf")

        # Clean base64
        base64_pdf = base64_pdf.strip().replace("\n", "").replace("\r", "")
        if base64_pdf.startswith("data:application/pdf;base64,"):
            base64_pdf = base64_pdf.split(",", 1)[1]

        # Decode
        try:
            pdf_bytes = base64.b64decode(base64_pdf, validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 PDF")

        # Save file
        pdf_path = Path(settings.PDF_STORAGE_DIR) / file_name
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # Basic PDF validation
        if not pdf_path.exists() or pdf_path.stat().st_size == 0:
            raise HTTPException(status_code=500, detail="Decoded PDF file is empty")

        # Get page count exactly like normal upload flow
        try:
            page_count = get_pdf_page_count(str(pdf_path))
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Saved file is not a valid PDF: {exc}")

        if page_count <= 0:
            raise HTTPException(status_code=400, detail="PDF has zero pages")

        # Create document using existing service
        document = document_service.create_document(
            db,
            file_name=file_name,
            original_path=str(pdf_path),
            page_count=page_count,
            cnr_number=cnr_number,
            batch_no=batch_no,
        )

        # Trigger existing pipeline exactly like current repo pattern
        enqueue_document_pipeline(db, document.id)

        return {
            "message": "PDF created and indexing started",
            "document_id": document.id,
            "file_name": document.file_name,
            "page_count": document.page_count,
            "status": document.status,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
