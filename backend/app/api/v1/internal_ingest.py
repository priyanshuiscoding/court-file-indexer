from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.services.base64_ingest_service import Base64IngestService

router = APIRouter(prefix="/internal", tags=["internal-ingest"])
service = Base64IngestService()


class Base64DocumentIn(BaseModel):
    case_type: str
    case_no: str
    case_year: int
    base64_pdf: str


class IngestBase64Request(BaseModel):
    case_type: str | None = None
    case_no: str | None = None
    case_year: int | None = None
    base64_pdf: str | None = None
    documents: list[Base64DocumentIn] | None = None
    overwrite: bool = False


@router.post("/ingest-base64")
def ingest_base64(payload: IngestBase64Request, db: Session = Depends(get_db)):
    try:
        if payload.documents:
            items = [item.model_dump() for item in payload.documents]
            results = service.ingest_batch(db, items, overwrite=payload.overwrite)
            return {
                "message": "batch accepted",
                "documents": results,
            }

        if not payload.case_type or not payload.case_no or payload.case_year is None or not payload.base64_pdf:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: case_type, case_no, case_year, base64_pdf",
            )

        result = service.ingest_one(
            db,
            case_type=payload.case_type,
            case_no=payload.case_no,
            case_year=payload.case_year,
            base64_pdf=payload.base64_pdf,
            overwrite=payload.overwrite,
        )
        return {
            "message": "accepted",
            "document": result,
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal ingest failed: {str(exc)}") from exc
