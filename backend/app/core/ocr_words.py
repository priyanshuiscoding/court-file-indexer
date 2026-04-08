from __future__ import annotations

from typing import List

from app.schemas.index_models import OCRWord


def extract_ocr_words_from_lines(lines: list[dict], *, offset_x: int = 0, offset_y: int = 0) -> List[OCRWord]:
    words: List[OCRWord] = []

    for item in lines:
        text = (item.get("text") or "").strip()
        if not text:
            continue

        bbox = item.get("bbox") or {}
        x1 = int(bbox.get("x1", 0)) + offset_x
        y1 = int(bbox.get("y1", 0)) + offset_y
        x2 = int(bbox.get("x2", 0)) + offset_x
        y2 = int(bbox.get("y2", 0)) + offset_y
        conf = float(item.get("confidence", 0.0) or 0.0)

        words.append(
            OCRWord(
                text=text,
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                conf=conf,
            )
        )

    return words
