from __future__ import annotations

from app.services.index_mapping_service import IndexMappingService


class IndexDisplayMappingService:
    def __init__(self) -> None:
        self.mapper = IndexMappingService()

    def build_display_value(self, description: str, annexure: str | None = None) -> tuple[str | None, str | None, str | None]:
        mapped_doc, mapped_sub, _ = self.mapper.map_description(description)

        display = None
        if mapped_doc and mapped_sub:
            display = f"{mapped_doc} ({mapped_sub})"
        elif mapped_doc:
            display = mapped_doc

        if annexure:
            if display:
                display = f"{display} [{annexure}]"
            else:
                display = f"[{annexure}]"

        return mapped_doc, mapped_sub, display
