from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.document import Document
from app.services.page_service import PageService

router = APIRouter(prefix="/pages", tags=["pages"])
page_service = PageService()


@router.get("/{document_id}")
def get_document_pages(document_id: int, db: Session = Depends(get_db)):
    document = db.get(Document, document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    pages = page_service.get_pages(db, document_id)
    return [
        {
            "page_no": p.page_no,
            "image_path": p.image_path,
            "ocr_text": p.ocr_text,
            "ocr_confidence": p.ocr_confidence,
            "is_candidate_index_page": p.is_candidate_index_page,
            "candidate_score": p.candidate_score,
        }
        for p in pages
    ]
