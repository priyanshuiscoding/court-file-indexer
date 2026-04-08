from pydantic import BaseModel


class MappingLabelOut(BaseModel):
    document_type: str
    sub_document_type: str
    keywords_en: str | None = None
    keywords_hi: str | None = None
    regex_rules: str | None = None
    priority: int = 100
