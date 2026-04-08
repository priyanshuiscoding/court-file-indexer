from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class IndexRow(Base):
    __tablename__ = "index_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    row_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_page_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    description_normalized: Mapped[str | None] = mapped_column(Text, nullable=True)
    annexure_no: Mapped[str | None] = mapped_column(String(128), nullable=True)
    page_from: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_to: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_pages: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mapped_document_type: Mapped[str | None] = mapped_column(String(256), nullable=True)
    mapped_sub_document_type: Mapped[str | None] = mapped_column(String(256), nullable=True)
    receiving_date: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extraction_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    verification_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(64), default="PENDING")
    generated_from_content: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document", back_populates="index_rows")
