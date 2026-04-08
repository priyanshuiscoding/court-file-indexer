from datetime import datetime
from pydantic import BaseModel


class DocumentOut(BaseModel):
    id: int
    cnr_number: str | None = None
    case_title: str | None = None
    file_name: str
    page_count: int
    status: str
    current_step: str
    is_vectorized: bool
    chat_ready: bool
    batch_no: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StartIndexingRequest(BaseModel):
    start_page: int | None = None
    end_page: int | None = None
    reindex: bool = False


class ManualScanRequest(BaseModel):
    start_page: int
    end_page: int
