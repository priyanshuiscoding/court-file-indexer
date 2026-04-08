from datetime import datetime
from pydantic import BaseModel


class ChatAskRequest(BaseModel):
    question: str


class ChatAskResponse(BaseModel):
    answer: str
    citations: list[dict]


class ChatMessageOut(BaseModel):
    id: int
    document_id: int
    role: str
    content: str
    citations_json: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
