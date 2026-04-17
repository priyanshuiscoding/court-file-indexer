from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import base64
from pathlib import Path

from app.api.deps import get_db
from app.core.config import get_settings
from app.models.document import Document
from app.tasks.document_tasks import enqueue_document_pipeline

router = APIRouter(prefix="/test", tags=["test"])

settings = get_settings()


@router.post("/base64-upload")
def upload_base64(payload: dict, db: Session = Depends(get_db)):
    try:
        base64_pdf = payload.get("base64_pdf")
        file_name = payload.get("file_name", "test_case.pdf")

        if not base64_pdf:
            raise HTTPException(400, "base64_pdf is required")

        # CLEAN BASE64 (important)
        base64_pdf = base64_pdf.strip().replace("\n", "").replace("\r", "")

        # DECODE
        pdf_bytes = base64.b64decode(base64_pdf)

        # SAVE FILE
        pdf_path = Path(settings.PDF_STORAGE_DIR) / file_name
        pdf_path.parent.mkdir(parents=True, exist_ok=True)

        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        # CREATE DOCUMENT
        document = Document(
            file_name=file_name,
            original_path=str(pdf_path),
            status="UPLOADED",
            current_step="Base64 Test Upload"
        )

        db.add(document)
        db.commit()
        db.refresh(document)

        # TRIGGER EXISTING PIPELINE
        enqueue_document_pipeline.delay(document.id)

        return {
            "message": "PDF created and indexing started",
            "document_id": document.id
        }

    except Exception as e:
        raise HTTPException(500, str(e))
