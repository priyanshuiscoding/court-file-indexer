from __future__ import annotations

from pydantic import BaseModel


class StageCounts(BaseModel):
    queued: int = 0
    ocr_processing: int = 0
    index_processing: int = 0
    vectorizing: int = 0
    completed: int = 0
    failed: int = 0


class DocumentRuntimeStatus(BaseModel):
    document_id: int
    status: str
    current_stage: str | None = None
    progress_percent: int = 0
    error_message: str | None = None


class BatchRuntimeStatus(BaseModel):
    batch_id: int
    status: str
    counts: StageCounts
    documents: list[DocumentRuntimeStatus]