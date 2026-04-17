from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import get_settings
from app.schemas.external_fetch_models import (
    ExternalFetchRunRequest,
    ExternalFetchRunResponse,
    ExternalFetchStatusResponse,
    ExternalFetchTriggerResponse,
)
from app.services.external_fetch_service import ExternalFetchService
from app.tasks.external_fetch_tasks import fetch_external_batch

router = APIRouter(prefix="/external", tags=["external-fetch"])
settings = get_settings()


@router.post("/fetch-now", response_model=ExternalFetchTriggerResponse)
def fetch_now(payload: ExternalFetchRunRequest):
    if not settings.EXTERNAL_FETCH_ENABLED:
        raise HTTPException(status_code=400, detail="External fetch is disabled")
    if not settings.EXTERNAL_FETCH_URL:
        raise HTTPException(status_code=400, detail="EXTERNAL_FETCH_URL is not configured")

    task = fetch_external_batch.delay(overwrite=payload.overwrite, limit=payload.limit)
    return ExternalFetchTriggerResponse(
        ok=True,
        message="External fetch started",
        task_id=task.id,
    )


@router.post("/fetch-now-sync", response_model=ExternalFetchRunResponse)
def fetch_now_sync(payload: ExternalFetchRunRequest, db: Session = Depends(get_db)):
    if not settings.EXTERNAL_FETCH_ENABLED:
        raise HTTPException(status_code=400, detail="External fetch is disabled")
    if not settings.EXTERNAL_FETCH_URL:
        raise HTTPException(status_code=400, detail="EXTERNAL_FETCH_URL is not configured")

    try:
        service = ExternalFetchService()
        result = service.fetch_and_ingest(db, overwrite=payload.overwrite, limit=payload.limit)
        return ExternalFetchRunResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"External fetch sync failed: {str(exc)}") from exc


@router.get("/fetch-status", response_model=ExternalFetchStatusResponse)
def fetch_status():
    return ExternalFetchStatusResponse(
        enabled=settings.EXTERNAL_FETCH_ENABLED,
        configured=bool(settings.EXTERNAL_FETCH_URL),
        batch_size=settings.EXTERNAL_FETCH_BATCH_SIZE,
        timeout_seconds=settings.EXTERNAL_FETCH_TIMEOUT_SECONDS,
    )
