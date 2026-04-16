from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    cnr_number: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)

    case_type: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    case_no: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    case_year: Mapped[str | None] = mapped_column(String(16), index=True, nullable=True)
    case_key: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)

    case_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    original_path: Mapped[str] = mapped_column(Text, nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    language_hint: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), default="UPLOADED")
    current_step: Mapped[str] = mapped_column(String(128), default="Uploaded")
    is_vectorized: Mapped[bool] = mapped_column(Boolean, default=False)
    chat_ready: Mapped[bool] = mapped_column(Boolean, default=False)
    batch_no: Mapped[str | None] = mapped_column(String(128), index=True, nullable=True)

    source_system: Mapped[str | None] = mapped_column(String(64), nullable=True)
    index_json_path: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    index_rows = relationship("IndexRow", back_populates="document", cascade="all, delete-orphan")
    logs = relationship("ProcessingLog", back_populates="document", cascade="all, delete-orphan")
    jobs = relationship("ProcessingJob", back_populates="document", cascade="all, delete-orphan")
