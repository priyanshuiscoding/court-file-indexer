from __future__ import annotations

import json
import subprocess
from pathlib import Path
from statistics import mean
from app.core.config import get_settings

settings = get_settings()


class HindiOCRFallbackService:
    def __init__(self) -> None:
        self.ocr_root = Path(settings.OCR_STORAGE_DIR)
        self.ocr_root.mkdir(parents=True, exist_ok=True)

    def run_tesseract_hin_eng(self, document_id: int, rendered_pages: list[dict]) -> list[dict]:
        results: list[dict] = []
        doc_dir = self.ocr_root / str(document_id) / "tesseract_fallback"
        doc_dir.mkdir(parents=True, exist_ok=True)

        for page in rendered_pages:
            image_path = page["image_path"]
            out_base = doc_dir / f"page_{page['page_no']}"
            cmd = [
                settings.TESSERACT_CMD,
                image_path,
                str(out_base),
                "-l",
                "hin+eng",
                "tsv",
            ]
            subprocess.run(cmd, check=False, capture_output=True)
            tsv_path = Path(str(out_base) + ".tsv")
            parsed = self._parse_tsv(tsv_path)
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
                    "engine": "tesseract_hin_eng",
                }
            )
        return results

    def _parse_tsv(self, tsv_path: Path) -> dict:
        if not tsv_path.exists():
            return {"text": "", "confidence": 0.0, "lines": []}

        lines: list[dict] = []
        text_parts: list[str] = []
        confidences: list[float] = []
        content = tsv_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        if len(content) <= 1:
            return {"text": "", "confidence": 0.0, "lines": []}

        header = content[0].split("\t")
        index_map = {name: idx for idx, name in enumerate(header)}
        for row in content[1:]:
            cols = row.split("\t")
            if len(cols) < len(header):
                continue
            text = cols[index_map.get("text", -1)].strip() if "text" in index_map else ""
            if not text:
                continue
            conf_raw = cols[index_map.get("conf", -1)] if "conf" in index_map else "-1"
            try:
                conf = max(0.0, float(conf_raw) / 100.0)
            except ValueError:
                conf = 0.0
            left = int(cols[index_map.get("left", -1)] or 0)
            top = int(cols[index_map.get("top", -1)] or 0)
            width = int(cols[index_map.get("width", -1)] or 0)
            height = int(cols[index_map.get("height", -1)] or 0)
            lines.append(
                {
                    "text": text,
                    "confidence": conf,
                    "bbox": {
                        "x1": left,
                        "y1": top,
                        "x2": left + width,
                        "y2": top + height,
                    },
                }
            )
            text_parts.append(text)
            confidences.append(conf)

        return {
            "text": "\n".join(text_parts),
            "confidence": mean(confidences) if confidences else 0.0,
            "lines": lines,
        }
