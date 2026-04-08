from __future__ import annotations

from enum import Enum


class BatchStatus(str, Enum):
    DRAFT = "draft"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    COMPLETED_WITH_ERRORS = "completed_with_errors"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DocumentStatus(str, Enum):
    UPLOADED = "uploaded"
    QUEUED = "queued"
    OCR_PROCESSING = "ocr_processing"
    OCR_DONE = "ocr_done"
    INDEX_PROCESSING = "index_processing"
    INDEX_DONE = "index_done"
    VECTORIZING = "vectorizing"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL_FAILED = "partial_failed"
    CANCELLED = "cancelled"


class PageStatus(str, Enum):
    QUEUED = "queued"
    RENDERED = "rendered"
    OCR_DONE = "ocr_done"
    INDEXED = "indexed"
    EMBEDDED = "embedded"
    FAILED = "failed"


class JobType(str, Enum):
    OCR_DOCUMENT = "ocr_document"
    EXTRACT_INDEX = "extract_index"
    VECTORIZE_DOCUMENT = "vectorize_document"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"
