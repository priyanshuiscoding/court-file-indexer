from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.high_court_import_models import HighCourtImportRequest, HighCourtImportResponse
from app.services.high_court_import_service import HighCourtImportService

router = APIRouter(prefix="/high-court", tags=["high-court-import"])
service = HighCourtImportService()


@router.post("/import-pending", response_model=HighCourtImportResponse)
def import_pending(payload: HighCourtImportRequest, db: Session = Depends(get_db)):
    try:
        return service.import_pending(db, limit=payload.limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
