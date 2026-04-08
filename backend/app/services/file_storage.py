from pathlib import Path
from uuid import uuid4
from fastapi import UploadFile
from app.core.config import get_settings

settings = get_settings()


class FileStorageService:
    def __init__(self) -> None:
        self.pdf_dir = Path(settings.PDF_STORAGE_DIR)
        self.render_dir = Path(settings.RENDER_STORAGE_DIR)
        self.ocr_dir = Path(settings.OCR_STORAGE_DIR)
        self.export_dir = Path(settings.EXPORT_STORAGE_DIR)
        self.log_dir = Path(settings.LOG_STORAGE_DIR)
        for directory in [self.pdf_dir, self.render_dir, self.ocr_dir, self.export_dir, self.log_dir]:
            directory.mkdir(parents=True, exist_ok=True)

    async def save_pdf(self, file: UploadFile) -> str:
        suffix = Path(file.filename).suffix or ".pdf"
        file_name = f"{uuid4().hex}{suffix}"
        target = self.pdf_dir / file_name
        with target.open("wb") as f:
            while chunk := await file.read(1024 * 1024):
                f.write(chunk)
        return str(target)
