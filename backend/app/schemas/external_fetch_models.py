from pydantic import BaseModel


class ExternalFetchRunRequest(BaseModel):
    overwrite: bool = False
    limit: int | None = None


class ExternalFetchTriggerResponse(BaseModel):
    ok: bool
    message: str
    task_id: str | None = None


class ExternalFetchStatusResponse(BaseModel):
    enabled: bool
    configured: bool
    batch_size: int
    timeout_seconds: int


class ExternalFetchRunResponse(BaseModel):
    ok: bool
    message: str
    summary: dict
    items: list[dict]
