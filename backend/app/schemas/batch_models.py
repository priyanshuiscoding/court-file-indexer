from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

from app.models.enums import BatchStatus


class BatchCreateResponse(BaseModel):
    batch_id: int
    name: str
    total_documents: int
    status: BatchStatus


class DocumentQueueItem(BaseModel):
    id: int
    filename: str
    page_count: int
    status: str
    progress_percent: int
    error_message: Optional[str] = None


class BatchDetailResponse(BaseModel):
    id: int
    name: str
    status: BatchStatus
    total_documents: int
    completed_documents: int
    failed_documents: int
    created_at: datetime
    updated_at: datetime
    documents: List[DocumentQueueItem]
