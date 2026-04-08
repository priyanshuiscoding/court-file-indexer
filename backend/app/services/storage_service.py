from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class StorageService:
    def __init__(self, base_dir: str = "storage/library") -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file: UploadFile) -> str:
        ext = Path(file.filename or "file.pdf").suffix.lower() or ".pdf"
        unique_name = f"{uuid4().hex}{ext}"
        output_path = self.base_dir / unique_name

        with output_path.open("wb") as target:
            shutil.copyfileobj(file.file, target)

        return str(output_path)
