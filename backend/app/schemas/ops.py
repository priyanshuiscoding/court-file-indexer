from datetime import datetime

from pydantic import BaseModel


class QueueActionResponse(BaseModel):
    ok: bool = True
    message: str
    affected: int = 0


class OpsQueueItemOut(BaseModel):
    id: int
    queue_name: str
    document_id: int
    document_name: str | None = None
    document_status: str | None = None
    status: str
    priority: int
    attempts: int
    task_id: str | None = None
    heartbeat_at: datetime | None = None
    stale_seconds: int | None = None
    is_stuck: bool = False
    created_at: datetime


class OpsStatusOut(BaseModel):
    indexed_count: int
    vectorized_count: int
    pending_queue_count: int
    review_queue_count: int
    failed_count: int
