from pydantic import BaseModel


class BatchOut(BaseModel):
    id: int
    batch_no: str
    total_files: int
