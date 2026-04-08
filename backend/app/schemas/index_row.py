from datetime import datetime
from pydantic import BaseModel


class IndexRowCreate(BaseModel):
    row_no: int | None = None
    source_page_no: int | None = None
    description_raw: str
    description_normalized: str | None = None
    annexure_no: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    total_pages: int | None = None
    mapped_document_type: str | None = None
    mapped_sub_document_type: str | None = None
    receiving_date: str | None = None
    extraction_confidence: float = 0.0
    verification_confidence: float = 0.0
    status: str = "PENDING"
    generated_from_content: bool = False


class IndexRowUpdate(BaseModel):
    description_raw: str | None = None
    description_normalized: str | None = None
    annexure_no: str | None = None
    page_from: int | None = None
    page_to: int | None = None
    total_pages: int | None = None
    mapped_document_type: str | None = None
    mapped_sub_document_type: str | None = None
    receiving_date: str | None = None
    extraction_confidence: float | None = None
    verification_confidence: float | None = None
    status: str | None = None


class IndexRowOut(IndexRowCreate):
    id: int
    document_id: int
    created_at: datetime

    model_config = {"from_attributes": True}
