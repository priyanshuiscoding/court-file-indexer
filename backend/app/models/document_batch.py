from sqlalchemy import Column, DateTime, Integer, String, func

from app.db.base import Base


class DocumentBatch(Base):
    __tablename__ = "document_batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_no = Column(String(120), nullable=False, unique=True, index=True)
    status = Column(String(30), nullable=False, default="PENDING")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
