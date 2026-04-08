from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.batch_models import BatchCreateResponse, BatchDetailResponse
from app.services.batch_service import BatchService

router = APIRouter(prefix="/batches", tags=["batches"])
service = BatchService()


@router.post("/upload", response_model=BatchCreateResponse)
def upload_batch(
    files: List[UploadFile] = File(...),
    batch_name: str | None = Form(default=None),
    db: Session = Depends(get_db),
) -> BatchCreateResponse:
    pdf_files = [f for f in files if (f.filename or "").lower().endswith(".pdf")]
    if not pdf_files:
        raise HTTPException(status_code=400, detail="No PDF files supplied")

    try:
        return service.upload_documents(db, pdf_files, batch_name=batch_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{batch_id}/start", response_model=BatchDetailResponse)
def start_batch(batch_id: int, db: Session = Depends(get_db)) -> BatchDetailResponse:
    try:
        return service.start_batch(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{batch_id}", response_model=BatchDetailResponse)
def get_batch(batch_id: int, db: Session = Depends(get_db)) -> BatchDetailResponse:
    try:
        return service.get_batch_detail(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
