from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.ops_models import BatchRuntimeStatus
from app.services.runtime_status_service import RuntimeStatusService

router = APIRouter(prefix='/runtime', tags=['runtime'])
service = RuntimeStatusService()


@router.get('/batches/{batch_id}', response_model=BatchRuntimeStatus)
def get_batch_runtime(batch_id: int, db: Session = Depends(get_db)) -> BatchRuntimeStatus:
    try:
        return service.get_batch_runtime_status(db, batch_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc