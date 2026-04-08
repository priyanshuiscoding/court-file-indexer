from __future__ import annotations

from typing import Any, Dict, List

from app.core.index_page_detector import score_index_page
from app.core.ocr_words import extract_ocr_words_from_lines
from app.core.strict_index_validator import validate_rows
from app.core.table_region_detector import detect_table_region
from app.core.table_row_rebuilder import detect_columns, group_words_into_lines, rebuild_index_rows


class StrictIndexingError(Exception):
    pass


def _filter_lines_in_bbox(lines: list[dict], bbox: tuple[int, int, int, int]) -> list[dict]:
    x1, y1, x2, y2 = bbox
    filtered = []
    for line in lines:
        b = line.get("bbox") or {}
        lx1 = int(b.get("x1", 0))
        ly1 = int(b.get("y1", 0))
        lx2 = int(b.get("x2", 0))
        ly2 = int(b.get("y2", 0))
        if lx1 >= x1 and ly1 >= y1 and lx2 <= x2 and ly2 <= y2:
            filtered.append(line)
    return filtered


def _line_has_header_hint(text: str) -> bool:
    t = text.lower()
    compact = "".join(ch for ch in t if ch.isalnum())
    return (
        "s.no" in t
        or "s no" in t
        or "sno" in compact
        or "particular" in t
        or "annexure" in t
        or "page" in t
    )


def _detect_index_pages_structural(page_payloads: list[dict], min_score: int = 4) -> list[int]:
    index_pages: list[int] = []

    for i, page in enumerate(page_payloads):
        text_score = score_index_page(page.get("text", ""))
        lines = page.get("lines") or []

        header_found = any(_line_has_header_hint(str(line.get("text", ""))) for line in lines)
        dense_lines = len(lines) >= 15

        score = text_score
        if header_found:
            score += 3
        if dense_lines:
            score += 1

        if score >= min_score:
            index_pages.append(i)

    return index_pages


def run_strict_index_pipeline(page_payloads: List[dict], max_pdf_pages: int) -> Dict[str, Any]:
    if not page_payloads:
        raise StrictIndexingError("No OCR page payloads supplied.")

    page_payloads = sorted(page_payloads, key=lambda p: p["page_no"])

    index_pages = _detect_index_pages_structural(page_payloads)
    if not index_pages:
        # Fallback: attempt extraction on all provided pages.
        index_pages = list(range(len(page_payloads)))

    extracted_rows = []
    debug_pages = []

    for page_idx in index_pages:
        page = page_payloads[page_idx]
        width = int(page.get("width") or 0)
        height = int(page.get("height") or 0)
        lines = page.get("lines") or []

        if width <= 0 or height <= 0:
            debug_pages.append({"page": page["page_no"], "status": "missing_dimensions"})
            continue

        x1, y1, x2, y2 = detect_table_region(width, height)
        table_lines = _filter_lines_in_bbox(lines, (x1, y1, x2, y2))

        words = extract_ocr_words_from_lines(table_lines)
        lines_grouped = group_words_into_lines(words)

        cols = detect_columns(lines_grouped)
        if cols is None:
            debug_pages.append(
                {
                    "page": page["page_no"],
                    "status": "header_not_found",
                    "raw_rows": 0,
                    "crop_bbox": [x1, y1, x2, y2],
                }
            )
            continue

        rows = rebuild_index_rows(lines_grouped, cols, source_page=page["page_no"])
        extracted_rows.extend(rows)

        debug_pages.append(
            {
                "page": page["page_no"],
                "status": "parsed",
                "raw_rows": len(rows),
                "crop_bbox": [x1, y1, x2, y2],
            }
        )

    strict_rows = validate_rows(extracted_rows, max_pdf_pages=max_pdf_pages)

    return {
        "index_pages": [page_payloads[p]["page_no"] for p in index_pages],
        "rows": [
            {
                "row_no": r.row_no,
                "description": r.description,
                "annexure": r.annexure,
                "page_start": r.page_start,
                "page_end": r.page_end,
                "pages": (
                    None
                    if r.page_start is None
                    else f"{r.page_start}-{r.page_end}" if r.page_start != r.page_end
                    else str(r.page_start)
                ),
                "confidence": round(r.confidence, 3),
                "review_required": r.review_required,
                "source_page": r.source_page,
                "raw_text": r.raw_text,
            }
            for r in strict_rows
        ],
        "meta": {
            "total_rows": len(strict_rows),
            "index_pages_found": len(index_pages),
            "debug_pages": debug_pages,
            "generated_fallback": 0,
            "mode": "strict_table_extraction",
        },
    }
