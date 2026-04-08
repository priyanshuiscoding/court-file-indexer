from __future__ import annotations

import re
import time
from pathlib import Path
import pandas as pd
from app.core.config import get_settings
from app.utils.text_normalizer import normalize_for_match

settings = get_settings()


class MappingSheetService:
    def __init__(self) -> None:
        self._cache: list[dict] = []
        self._last_loaded_at: float = 0.0
        self._path = Path(settings.MAPPING_SHEET_PATH)

    def get_labels(self) -> list[dict]:
        if not self._path.exists():
            return []

        now = time.time()
        if self._cache and (now - self._last_loaded_at) < settings.MAPPING_REFRESH_SECONDS:
            return self._cache

        df = pd.read_excel(self._path, sheet_name=settings.MAPPING_SHEET_NAME)
        df = df.fillna("")
        labels: list[dict] = []
        for _, row in df.iterrows():
            labels.append(
                {
                    "document_type": str(row.get("document_type", "")).strip(),
                    "sub_document_type": str(row.get("sub_document_type", "")).strip(),
                    "keywords_en": str(row.get("keywords_en", "")).strip(),
                    "keywords_hi": str(row.get("keywords_hi", "")).strip(),
                    "regex_rules": str(row.get("regex_rules", "")).strip(),
                    "priority": int(row.get("priority", 100) or 100),
                    "lookup_text": normalize_for_match(
                        " ".join(
                            [
                                str(row.get("document_type", "")),
                                str(row.get("sub_document_type", "")),
                                str(row.get("keywords_en", "")),
                                str(row.get("keywords_hi", "")),
                            ]
                        )
                    ),
                }
            )

        labels.sort(key=lambda x: x["priority"])
        self._cache = labels
        self._last_loaded_at = now
        return labels

    def match_by_regex(self, description: str) -> dict | None:
        labels = self.get_labels()
        for label in labels:
            rule = label.get("regex_rules") or ""
            if not rule:
                continue
            try:
                if re.search(rule, description, flags=re.IGNORECASE):
                    return label
            except re.error:
                continue
        return None
