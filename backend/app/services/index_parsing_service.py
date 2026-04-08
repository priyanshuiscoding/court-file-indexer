from __future__ import annotations

import re
from app.services.row_validation_service import RowValidationService
from app.services.table_region_service import TableRegionService
from app.utils.layout_utils import cluster_lines_by_y, filter_lines_in_box, row_bounds, row_to_text
from app.utils.page_range import parse_page_range_from_text
from app.utils.text_normalizer import normalize_for_match, normalize_text


HEADER_MARKERS = [
    "index",
    "particulars",
    "description of documents",
    "page no",
    "page no of document",
    "annexure",
    "annex.",
    "s.no",
    "sr.no",
    "sl.no",
    "description",
    "क्रमांक",
    "दस्तावेज",
    "पृष्ठ",
    "अनुक्रमणिका",
    "सूची",
]

SKIP_ROW_PATTERNS = [
    r"^index$",
    r"^versus$",
    r"^petitioner",
    r"^respondent",
    r"^applicant",
    r"^counsel",
    r"^dated",
    r"^place",
    r"^received",
    r"^advance copy",
    r"^jabalpur$",
]


class IndexParsingService:
    def __init__(self) -> None:
        self.table_region_service = TableRegionService()
        self.validator = RowValidationService()

    def parse_index_rows(self, pages: list[dict], page_count: int | None = None) -> list[dict]:
        all_rows: list[dict] = []
        serial_counter = 1

        for page in pages:
            rows = self._extract_rows_from_page(page, page_count=page_count)
            for row in rows:
                if row.get("row_no") is None:
                    row["row_no"] = serial_counter
                serial_counter = max(serial_counter + 1, (row["row_no"] or serial_counter) + 1)
                all_rows.append(row)

        merged = self._merge_continuations(all_rows)
        final_rows = []
        for row in merged:
            valid, _ = self.validator.is_valid_row(row, page_count=page_count)
            if valid:
                final_rows.append(row)

        return final_rows

    def _extract_rows_from_page(self, page: dict, page_count: int | None = None) -> list[dict]:
        lines = page.get("lines", []) or []
        if not lines:
            return []

        table_box = self.table_region_service.detect_index_table_region(page.get("image_path", ""), lines)
        if table_box:
            lines = filter_lines_in_box(lines, table_box, tolerance=8)

        grouped = cluster_lines_by_y(lines, tolerance=11)
        extracted: list[dict] = []

        for group in grouped:
            text = normalize_text(row_to_text(group))
            if not text:
                continue

            text_norm = normalize_for_match(text)
            if self._is_header_or_noise(text_norm):
                continue

            bounds = row_bounds(group)
            row = self._parse_single_row(text, text_norm, page["page_no"], bounds)
            if row:
                valid, _ = self.validator.is_valid_row(row, page_count=page_count)
                if valid:
                    extracted.append(row)

        return extracted

    def _parse_single_row(self, text: str, text_norm: str, source_page_no: int, bounds: dict) -> dict | None:
        serial_no = None
        serial_match = re.match(r"^(\d{1,2})[\.)]?\s+(.*)$", text)
        remaining = text
        if serial_match:
            serial_no = int(serial_match.group(1))
            remaining = serial_match.group(2).strip()

        page_from, page_to, raw_range = parse_page_range_from_text(remaining)

        annexure_no = None
        annex_match = re.search(
            r"\b([APCV][-\/]?\d+|[APCV]\s*[-/]\s*\d+|[APCV]\s*\d+|P/\d+|A/\d+|C[-/]?\d+)\b",
            remaining,
            flags=re.IGNORECASE,
        )
        if annex_match:
            annexure_no = normalize_text(annex_match.group(1)).replace(" ", "")
            remaining = remaining.replace(annex_match.group(0), " ").strip()

        if raw_range:
            remaining = remaining.replace(raw_range, " ").strip(" .:-")

        remaining = re.sub(r"\s+", " ", remaining).strip(" .:-")
        if not remaining:
            return None

        extraction_confidence = 0.45
        if serial_no is not None:
            extraction_confidence += 0.12
        if annexure_no:
            extraction_confidence += 0.12
        if page_from is not None:
            extraction_confidence += 0.16
        if len(remaining.split()) >= 2:
            extraction_confidence += 0.10
        if len(remaining.split()) >= 5:
            extraction_confidence += 0.05

        return {
            "row_no": serial_no,
            "source_page_no": source_page_no,
            "description_raw": remaining,
            "description_normalized": normalize_text(remaining),
            "annexure_no": annexure_no,
            "page_from": page_from,
            "page_to": page_to,
            "total_pages": (page_to - page_from + 1) if page_from and page_to and page_to >= page_from else None,
            "bbox": bounds,
            "extraction_confidence": min(0.95, extraction_confidence),
        }

    def _is_header_or_noise(self, text_norm: str) -> bool:
        if not text_norm:
            return True

        for marker in HEADER_MARKERS:
            marker_norm = normalize_for_match(marker)
            if text_norm == marker_norm:
                return True

        for pattern in SKIP_ROW_PATTERNS:
            if re.match(pattern, text_norm, flags=re.IGNORECASE):
                return True

        if len(text_norm) <= 2:
            return True

        return False

    def _merge_continuations(self, rows: list[dict]) -> list[dict]:
        if not rows:
            return []

        merged: list[dict] = [rows[0]]
        for row in rows[1:]:
            prev = merged[-1]

            same_serial = row.get("row_no") is not None and prev.get("row_no") == row.get("row_no")
            continuation = (
                row.get("row_no") is None
                and row.get("page_from") is None
                and row.get("annexure_no") is None
            )

            if same_serial or continuation:
                prev["description_raw"] = f"{prev['description_raw']} {row['description_raw']}".strip()
                prev["description_normalized"] = normalize_text(
                    f"{prev['description_normalized']} {row['description_normalized']}"
                )
                if prev.get("page_from") is None and row.get("page_from") is not None:
                    prev["page_from"] = row.get("page_from")
                    prev["page_to"] = row.get("page_to")
                if not prev.get("annexure_no") and row.get("annexure_no"):
                    prev["annexure_no"] = row.get("annexure_no")
                prev["extraction_confidence"] = min(0.95, prev.get("extraction_confidence", 0.5) + 0.04)
                continue

            merged.append(row)

        return merged
