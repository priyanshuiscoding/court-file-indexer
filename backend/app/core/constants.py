from enum import StrEnum


class DocumentStatus(StrEnum):
    UPLOADED = "UPLOADED"
    PREVIEW_READY = "PREVIEW_READY"
    OCR_RUNNING = "OCR_RUNNING"
    OCR_DONE = "OCR_DONE"
    VECTORIZING = "VECTORIZING"
    VECTORIZED = "VECTORIZED"
    INDEX_SEARCH_RUNNING = "INDEX_SEARCH_RUNNING"
    INDEX_FOUND = "INDEX_FOUND"
    INDEX_PARSED = "INDEX_PARSED"
    VERIFYING = "VERIFYING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    FAILED = "FAILED"


class QueueStatus(StrEnum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    STOPPED = "STOPPED"
    REVIEW = "REVIEW"


INDEX_KEYWORDS_EN = [
    "index",
    "table of contents",
    "chronology",
    "chronological events",
    "list of documents",
    "particulars",
    "annexure",
    "page no",
    "vakalatnama",
    "affidavit",
    "writ petition",
]

INDEX_KEYWORDS_HI = [
    "सूची",
    "अनुक्रमणिका",
    "दस्तावेज",
    "विवरण",
    "पृष्ठ",
    "क्रमांक",
    "वकालतनामा",
    "शपथ पत्र",
]
