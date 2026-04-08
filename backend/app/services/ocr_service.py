from __future__ import annotations

import json
from pathlib import Path
from statistics import mean

from paddleocr import PaddleOCR

from app.core.config import get_settings

settings = get_settings()


class OCRService:
    _ocr_engines: dict[str, PaddleOCR] = {}

    def __init__(self) -> None:
        self.ocr_root = Path(settings.OCR_STORAGE_DIR)
        self.ocr_root.mkdir(parents=True, exist_ok=True)

    def _configured_languages(self) -> list[str]:
        langs = [lang.strip() for lang in (settings.OCR_LANGUAGES or "en").split(",") if lang.strip()]
        return langs or ["en"]

    def _get_engine(self, lang: str) -> PaddleOCR:
        if lang not in OCRService._ocr_engines:
            OCRService._ocr_engines[lang] = PaddleOCR(
                use_angle_cls=settings.OCR_USE_ANGLE_CLS,
                lang=lang,
                show_log=False,
            )
        return OCRService._ocr_engines[lang]

    def _run_single_lang(self, image_path: str, lang: str) -> dict:
        engine = self._get_engine(lang)
        raw = engine.ocr(image_path, cls=settings.OCR_USE_ANGLE_CLS)
        parsed = self._parse_paddle_output(raw)
        parsed["lang"] = lang
        return parsed

    def _run_best_ocr(self, image_path: str) -> dict:
        langs = self._configured_languages()
        primary = self._run_single_lang(image_path, langs[0])

        # If confidence/text quality is low, try fallback language and keep the better parse.
        if len(langs) > 1 and (primary.get("confidence", 0.0) < 0.55 or len(primary.get("text", "")) < 80):
            fallback = self._run_single_lang(image_path, langs[1])
            primary_score = primary.get("confidence", 0.0) + (len(primary.get("text", "")) / 5000)
            fallback_score = fallback.get("confidence", 0.0) + (len(fallback.get("text", "")) / 5000)
            if fallback_score > primary_score:
                return fallback

        return primary

    def run_ocr_on_rendered_pages(self, document_id: int, rendered_pages: list[dict]) -> list[dict]:
        doc_dir = self.ocr_root / str(document_id)
        doc_dir.mkdir(parents=True, exist_ok=True)

        results: list[dict] = []
        for page in rendered_pages:
            image_path = page["image_path"]
            parsed = self._run_best_ocr(image_path)
            json_path = doc_dir / f"page_{page['page_no']}.json"
            json_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")

            results.append(
                {
                    "page_no": page["page_no"],
                    "image_path": image_path,
                    "width": page.get("width"),
                    "height": page.get("height"),
                    "text": parsed["text"],
                    "confidence": parsed["confidence"],
                    "lines": parsed["lines"],
                    "ocr_json_path": str(json_path),
                }
            )
        return results

    def _parse_paddle_output(self, raw: list) -> dict:
        lines: list[dict] = []
        all_text: list[str] = []
        confidences: list[float] = []

        if not raw:
            return {"text": "", "confidence": 0.0, "lines": []}

        page_items = raw[0] if isinstance(raw, list) and raw else []
        if page_items is None:
            page_items = []

        for item in page_items:
            if not item or len(item) < 2:
                continue
            bbox = item[0]
            text_info = item[1]
            if not text_info or len(text_info) < 2:
                continue
            text = str(text_info[0]).strip()
            conf = float(text_info[1])
            if not text:
                continue

            xs = [int(p[0]) for p in bbox]
            ys = [int(p[1]) for p in bbox]
            line = {
                "text": text,
                "confidence": conf,
                "bbox": {
                    "x1": min(xs),
                    "y1": min(ys),
                    "x2": max(xs),
                    "y2": max(ys),
                },
            }
            lines.append(line)
            all_text.append(text)
            confidences.append(conf)

        lines = sorted(lines, key=lambda l: (l["bbox"]["y1"], l["bbox"]["x1"]))
        return {
            "text": "\n".join(all_text),
            "confidence": mean(confidences) if confidences else 0.0,
            "lines": lines,
        }
