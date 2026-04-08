from __future__ import annotations

import csv
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DocumentTypeNode:
    code: str
    parent_code: str
    label: str
    is_parent: bool


class DocumentTypeService:
    def __init__(self, csv_path: Optional[str] = None) -> None:
        if csv_path:
            self.csv_path = Path(csv_path)
        else:
            primary = Path("storage/masters_document_types_202603131239.csv")
            fallback = Path("backend/storage/masters_document_types_202603131239.csv")
            self.csv_path = primary if primary.exists() else fallback

    @lru_cache(maxsize=1)
    def load_all(self) -> List[DocumentTypeNode]:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Document type CSV not found: {self.csv_path}")

        rows: List[DocumentTypeNode] = []
        with self.csv_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for raw in reader:
                doc_code = str(raw.get("document_code", "")).strip()
                sub_code = str(raw.get("document_code1", "")).strip()
                label = str(raw.get("document_desc", "")).strip()

                if not doc_code or not sub_code or not label:
                    continue

                is_parent = sub_code == "0"
                code = f"{doc_code}-{sub_code}"

                rows.append(
                    DocumentTypeNode(
                        code=code,
                        parent_code=f"{doc_code}-0",
                        label=label,
                        is_parent=is_parent,
                    )
                )
        return rows

    def get_hierarchy(self) -> List[dict]:
        rows = self.load_all()

        parents = [r for r in rows if r.is_parent]
        children = [r for r in rows if not r.is_parent]

        grouped: Dict[str, List[DocumentTypeNode]] = {}
        for child in children:
            grouped.setdefault(child.parent_code, []).append(child)

        result: List[dict] = []
        for parent in sorted(parents, key=lambda x: (int(x.parent_code.split("-")[0]), x.label.lower())):
            sub_docs = sorted(grouped.get(parent.code, []), key=lambda x: int(x.code.split("-")[1]))
            result.append(
                {
                    "code": parent.code,
                    "label": parent.label,
                    "children": [
                        {
                            "code": child.code,
                            "label": child.label,
                        }
                        for child in sub_docs
                    ],
                }
            )
        return result

    def get_parent_by_code(self, code: str) -> Optional[dict]:
        for parent in self.get_hierarchy():
            if parent["code"] == code:
                return parent
        return None

    def find_by_codes(self, document_code: str | None, sub_document_code: str | None) -> dict:
        hierarchy = self.get_hierarchy()
        parent = next((p for p in hierarchy if p["code"] == document_code), None)

        child = None
        if parent and sub_document_code:
            child = next((c for c in parent["children"] if c["code"] == sub_document_code), None)

        return {
            "document": parent,
            "sub_document": child,
        }
