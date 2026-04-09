from __future__ import annotations

from typing import Any, Dict, List

from app.core.index_page_detector import score_index_page
from app.core.ocr_words import extract_ocr_words_from_lines
from app.core.strict_index_validator import validate_rows_with_debug
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
    t = (text or "").lower()
    compact = "".join(ch for ch in t if ch.isalnum())
    return (
        "s.no" in t
        or "s no" in t
        or "sno" in compact
        or "particular" in t
        or "annexure" in t
        or "page" in t
        or "index" in t
    )


def _serial_line_hints(lines: list[dict]) -> int:
    hits = 0
    for line in lines:
        txt = (line.get("text") or "").strip().lower()
        if not txt:
            continue
        if txt[:1].isdigit() and ("." in txt[:4] or ")" in txt[:4] or len(txt.split()) > 2):
            hits += 1
    return hits


def _continuation_signal(page: dict) -> int:
    text = (page.get("text") or "").lower()
    lines = page.get("lines") or []

    signal = 0
    if "annexure" in text:
        signal += 1
    if "page no" in text or "pages" in text:
        signal += 1
    if _serial_line_hints(lines) >= 4:
        signal += 2
    if len(lines) >= 12:
        signal += 1

    return signal


def _detect_index_pages_structural(page_payloads: list[dict], min_score: int = 4) -> list[int]:
    if not page_payloads:
        return []

    page_signals: list[dict] = []
    for i, page in enumerate(page_payloads):
        text_score = score_index_page(page.get("text", ""))
        lines = page.get("lines") or []

        header_found = any(_line_has_header_hint(str(line.get("text", ""))) for line in lines)
        dense_lines = len(lines) >= 15
        serial_hint = min(3, _serial_line_hints(lines))

        score = text_score
        if header_found:
            score += 3
        if dense_lines:
            score += 1
        score += 0.4 * serial_hint

        page_signals.append(
            {
                "idx": i,
                "score": float(score),
                "text_score": text_score,
                "continuation": _continuation_signal(page),
            }
        )

    strong = [s for s in page_signals if s["score"] >= min_score]
    if not strong:
        return []

    primary = max(strong, key=lambda x: x["score"])
    selected = [primary["idx"]]

    # Continuation logic: include up to next 2 pages if they look like table continuations.
    for step in (1, 2):
        nidx = primary["idx"] + step
        if nidx >= len(page_payloads):
            continue
        sig = next((s for s in page_signals if s["idx"] == nidx), None)
        if not sig:
            continue

        if sig["score"] >= (min_score - 0.5) or sig["continuation"] >= 3:
            selected.append(nidx)

    selected = sorted(set(selected))[:3]
    return selected


def run_strict_index_pipeline(page_payloads: List[dict], max_pdf_pages: int) -> Dict[str, Any]:
    if not page_payloads:
        raise StrictIndexingError("No OCR page payloads supplied.")

    page_payloads = sorted(page_payloads, key=lambda p: p["page_no"])

    index_pages = _detect_index_pages_structural(page_payloads)
    used_all_pages_fallback = False
    if not index_pages:
        # Conservative fallback: try top-scoring first pages rather than all pages.
        candidates = [
            {
                "idx": i,
                "score": score_index_page(page.get("text", "")),
            }
            for i, page in enumerate(page_payloads[:20])
        ]
        candidates = sorted(candidates, key=lambda x: x["score"], reverse=True)
        index_pages = sorted([c["idx"] for c in candidates[:3] if c["score"] > 0])
        if not index_pages:
            index_pages = list(range(min(3, len(page_payloads))))
        used_all_pages_fallback = True

    extracted_rows = []
    page_rows_debug: dict[int, dict] = {}

    for page_idx in index_pages:
        page = page_payloads[page_idx]
        page_no = int(page["page_no"])
        width = int(page.get("width") or 0)
        height = int(page.get("height") or 0)
        lines = page.get("lines") or []

        base_debug = {
            "page": page_no,
            "status": "",
            "rows_parsed": 0,
            "rows_kept": 0,
            "rows_dropped": 0,
            "drop_reasons": {},
            "crop_bbox": None,
            "used_full_page_fallback": False,
        }

        if width <= 0 or height <= 0:
            base_debug["status"] = "missing_dimensions"
            page_rows_debug[page_no] = base_debug
            continue

        x1, y1, x2, y2 = detect_table_region(width, height, lines=lines)
        base_debug["crop_bbox"] = [x1, y1, x2, y2]
        table_lines = _filter_lines_in_bbox(lines, (x1, y1, x2, y2))

        words = extract_ocr_words_from_lines(table_lines)
        lines_grouped = group_words_into_lines(words)
        cols = detect_columns(lines_grouped)

        if cols is None:
            base_debug["status"] = "header_not_found"
            page_rows_debug[page_no] = base_debug
            continue

        rows = rebuild_index_rows(lines_grouped, cols, source_page=page_no)

        extracted_rows.extend(rows)
        base_debug["rows_parsed"] = len(rows)
        base_debug["status"] = "parsed"
        page_rows_debug[page_no] = base_debug

    strict_rows, validation_debug = validate_rows_with_debug(extracted_rows, max_pdf_pages=max_pdf_pages)

    for page_no, v in validation_debug.items():
        page_info = page_rows_debug.get(
            page_no,
            {
                "page": page_no,
                "status": "parsed",
                "rows_parsed": 0,
                "rows_kept": 0,
                "rows_dropped": 0,
                "drop_reasons": {},
                "crop_bbox": None,
                "used_full_page_fallback": False,
            },
        )
        page_info["rows_parsed"] = int(v.get("parsed", page_info.get("rows_parsed", 0)))
        page_info["rows_dropped"] = int(v.get("dropped", 0))
        page_info["rows_kept"] = max(0, page_info["rows_parsed"] - page_info["rows_dropped"])
        page_info["drop_reasons"] = v.get("drop_reasons", {})
        page_rows_debug[page_no] = page_info

    debug_pages = [page_rows_debug[k] for k in sorted(page_rows_debug.keys())]

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
            "used_all_pages_fallback": used_all_pages_fallback,
        },
    }
