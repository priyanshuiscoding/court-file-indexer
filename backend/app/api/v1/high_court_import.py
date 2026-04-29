from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.client_auth import verify_client_api_key
from app.api.deps import get_db
from app.core.config import get_settings
from app.schemas.high_court_import_models import (
    HighCourtBulkMarkCompleteRequest,
    HighCourtImportItemResult,
    HighCourtImportJobListResponse,
    HighCourtImportJobOut,
    HighCourtImportRequest,
    HighCourtImportResponse,
    HighCourtMarkCompleteRequest,
    HighCourtImportStatusSyncResponse,
    HighCourtRetryRequest,
)
from app.services.high_court_completion_service import HighCourtCompletionService
from app.services.high_court_import_job_service import HighCourtImportJobService
from app.services.high_court_import_service import HighCourtImportService
from app.services.high_court_import_status_sync_service import HighCourtImportStatusSyncService
from app.services.high_court_result_service import HighCourtResultService
from app.services.high_court_mysql_service import HighCourtMySQLService
from app.tasks.high_court_scheduled_tasks import (
    import_pending_scheduled,
    mark_completed_scheduled,
    sync_status_scheduled,
)

router = APIRouter(prefix="/high-court", tags=["high-court-import"])
settings = get_settings()
service = HighCourtImportService()
job_service = HighCourtImportJobService()
status_sync_service = HighCourtImportStatusSyncService()
result_service = HighCourtResultService()
completion_service = HighCourtCompletionService()
mysql_service = HighCourtMySQLService()


@router.post("/import-pending", response_model=HighCourtImportResponse)
def import_pending(payload: HighCourtImportRequest, db: Session = Depends(get_db)):
    try:
        return service.import_pending(db, limit=payload.limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/import-jobs", response_model=HighCourtImportJobListResponse)
def list_import_jobs(
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    jobs = job_service.list_jobs(db, status=status, limit=limit, offset=offset)
    return HighCourtImportJobListResponse(ok=True, count=len(jobs), jobs=jobs)


@router.get("/import-jobs/{batch_no}", response_model=HighCourtImportJobOut)
def get_import_job(batch_no: str, db: Session = Depends(get_db)):
    job = job_service.get_by_batch_no(db, batch_no=batch_no)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return job


@router.post("/import-jobs/retry", response_model=HighCourtImportItemResult)
def retry_import_job(payload: HighCourtRetryRequest, db: Session = Depends(get_db)):
    try:
        return service.import_by_batch_no(db, payload.batch_no)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/import-jobs/sync-status", response_model=HighCourtImportStatusSyncResponse)
def sync_import_job_statuses(
    limit: int = Query(default=500, ge=1, le=5000),
    db: Session = Depends(get_db),
):
    try:
        return status_sync_service.sync_all_linked_jobs(db, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/result/{batch_no}", dependencies=[Depends(verify_client_api_key)])
def get_result(batch_no: str, db: Session = Depends(get_db)):
    result = result_service.get_result(db, batch_no)
    if not result.get("ok") and result.get("error") == "Batch not found":
        raise HTTPException(status_code=404, detail="Batch not found")
    return result


@router.get("/result/by-fil-no/{fil_no}", dependencies=[Depends(verify_client_api_key)])
def get_result_by_fil_no(fil_no: str, db: Session = Depends(get_db)):
    job = result_service.get_job_by_fil_no(db, fil_no)
    if not job:
        raise HTTPException(status_code=404, detail="fil_no not found")
    return result_service.get_result(db, job.batch_no)


@router.get("/health")
def high_court_health():
    mount_root = Path(settings.HC_MOUNT_ROOT)
    export_dir = Path(settings.EXPORT_STORAGE_DIR) / "index_json"
    mysql = mysql_service.ping()
    mount_ok = mount_root.exists() and mount_root.is_dir()
    export_ok = export_dir.exists() and export_dir.is_dir()
    ok = bool(mysql.get("ok")) and mount_ok and export_ok
    return {
        "ok": ok,
        "mysql": mysql,
        "mount_root": {"ok": mount_ok, "path": str(mount_root)},
        "export_dir": {"ok": export_ok, "path": str(export_dir)},
        "scheduler": {
            "enabled": settings.HC_SCHEDULER_ENABLED,
            "import_every_seconds": settings.HC_SCHEDULER_IMPORT_EVERY_SECONDS,
            "sync_status_every_seconds": settings.HC_SCHEDULER_SYNC_STATUS_EVERY_SECONDS,
            "mark_complete_enabled": settings.HC_SCHEDULER_MARK_COMPLETE_ENABLED,
        },
        "mark_complete_enabled": settings.HC_MYSQL_MARK_COMPLETE_ENABLED,
    }


@router.get("/import-summary")
def import_summary(db: Session = Depends(get_db)):
    return {"ok": True, "counts": job_service.count_by_status(db)}


@router.get("/config")
def high_court_config():
    return {
        "ok": True,
        "hc_mysql_host_configured": bool(settings.HC_MYSQL_HOST),
        "hc_mysql_db": settings.HC_MYSQL_DB,
        "hc_mysql_table": settings.HC_MYSQL_TABLE,
        "hc_mount_root": settings.HC_MOUNT_ROOT,
        "hc_import_limit": settings.HC_IMPORT_LIMIT,
        "hc_scheduler_enabled": settings.HC_SCHEDULER_ENABLED,
        "hc_mysql_mark_complete_enabled": settings.HC_MYSQL_MARK_COMPLETE_ENABLED,
        "client_api_auth_enabled": settings.ENABLE_CLIENT_API_AUTH,
    }


@router.post("/mark-completed")
def mark_completed(payload: HighCourtMarkCompleteRequest, db: Session = Depends(get_db)):
    try:
        return completion_service.mark_completed_by_batch_no(db, payload.batch_no)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/mark-completed-ready")
def mark_completed_ready(payload: HighCourtBulkMarkCompleteRequest, db: Session = Depends(get_db)):
    try:
        return completion_service.mark_completed_ready_jobs(db, limit=payload.limit or 100)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/scheduler/status")
def scheduler_status():
    return {
        "enabled": settings.HC_SCHEDULER_ENABLED,
        "import_every_seconds": settings.HC_SCHEDULER_IMPORT_EVERY_SECONDS,
        "import_limit": settings.HC_SCHEDULER_IMPORT_LIMIT,
        "sync_status_every_seconds": settings.HC_SCHEDULER_SYNC_STATUS_EVERY_SECONDS,
        "mark_complete_enabled": settings.HC_SCHEDULER_MARK_COMPLETE_ENABLED,
        "mark_complete_every_seconds": settings.HC_SCHEDULER_MARK_COMPLETE_EVERY_SECONDS,
        "mark_complete_limit": settings.HC_SCHEDULER_MARK_COMPLETE_LIMIT,
        "external_mysql_mark_complete_enabled": settings.HC_MYSQL_MARK_COMPLETE_ENABLED,
    }


@router.post("/scheduler/run-import-now")
def run_import_now():
    task = import_pending_scheduled.delay(True)
    return {"ok": True, "task_id": task.id}


@router.post("/scheduler/run-sync-now")
def run_sync_now():
    task = sync_status_scheduled.delay(True)
    return {"ok": True, "task_id": task.id}


@router.post("/scheduler/run-mark-completed-now")
def run_mark_completed_now():
    task = mark_completed_scheduled.delay(True)
    return {"ok": True, "task_id": task.id}
