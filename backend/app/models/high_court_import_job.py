from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class HighCourtImportJob(Base):
    __tablename__ = "high_court_import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)

    source_system: Mapped[str] = mapped_column(String(128), default="high_court_mysql", index=True)
    external_row_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    batch_no: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    fil_no: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    source_pdf_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    document_id: Mapped[int | None] = mapped_column(
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    status: Mapped[str] = mapped_column(String(64), default="DISCOVERED", index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    import_attempts: Mapped[int] = mapped_column(Integer, default=0)
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    imported_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    document = relationship("Document")
