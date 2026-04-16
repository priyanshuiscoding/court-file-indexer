from typing import Any
from pydantic import BaseModel


class IntegrationResultResponse(BaseModel):
    ok: bool
    case_key: str
    document_id: int | None = None
    status: str
    json_ready: bool
    json_data: dict[str, Any] | None = None
    message: str | None = None
