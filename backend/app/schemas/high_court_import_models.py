from __future__ import annotations

from pydantic import BaseModel, Field


class HighCourtImportRequest(BaseModel):
    limit: int | None = Field(default=None, ge=1, le=500)


class HighCourtImportItemResult(BaseModel):
    external_row_id: int | str | None = None
    batch_no: str | None = None
    fil_no: str | None = None
    pdf_path: str | None = None
    status: str
    document_id: int | None = None
    error: str | None = None


class HighCourtImportResponse(BaseModel):
    ok: bool
    fetched: int
    queued: int
    skipped: int
    failed: int
    results: list[HighCourtImportItemResult]
