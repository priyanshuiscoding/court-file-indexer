from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.integration_models import IntegrationResultResponse
from app.services.integration_result_service import IntegrationResultService

router = APIRouter(prefix="/integrations", tags=["integrations"])
service = IntegrationResultService()


@router.get("/result/{case_key}", response_model=IntegrationResultResponse)
def get_result(case_key: str, db: Session = Depends(get_db)):
    doc = service.get_by_case_key(db, case_key)
    if not doc:
        raise HTTPException(status_code=404, detail="Case key not found")

    json_data = service.load_index_json(doc)
    status = service.infer_status(doc, json_data)

    if json_data is not None:
        return IntegrationResultResponse(
            ok=True,
            case_key=service.normalize_case_key(case_key),
            document_id=doc.id,
            status="READY",
            json_ready=True,
            json_data=json_data,
            message=None,
        )

    return IntegrationResultResponse(
        ok=False if status in {"FAILED", "REVIEW_REQUIRED"} else True,
        case_key=service.normalize_case_key(case_key),
        document_id=doc.id,
        status=status,
        json_ready=False,
        json_data=None,
        message="Processing is still in progress" if status == "PROCESSING" else "Index JSON not available",
    )
