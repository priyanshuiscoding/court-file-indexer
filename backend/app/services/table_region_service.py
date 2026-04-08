from __future__ import annotations

import cv2
from app.utils.geometry_utils import bbox_area


class TableRegionService:
    def detect_index_table_region(self, image_path: str, lines: list[dict]) -> dict | None:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return self._fallback_from_ocr(lines)

        h, w = image.shape[:2]
        binary = cv2.threshold(image, 180, 255, cv2.THRESH_BINARY_INV)[1]

        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(25, w // 25), 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(25, h // 25)))

        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)
        table_mask = cv2.add(h_lines, v_lines)

        contours, _ = cv2.findContours(table_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in contours:
            x, y, bw, bh = cv2.boundingRect(c)
            if bw < w * 0.18 or bh < h * 0.08:
                continue
            boxes.append({"x1": x, "y1": y, "x2": x + bw, "y2": y + bh})

        if boxes:
            boxes.sort(key=bbox_area, reverse=True)
            candidate = boxes[0]
            heading_y = self._find_index_heading_y(lines)
            if heading_y is not None:
                below_heading = [b for b in boxes if b["y1"] >= heading_y - 15]
                if below_heading:
                    below_heading.sort(key=bbox_area, reverse=True)
                    candidate = below_heading[0]
            return candidate

        return self._fallback_from_ocr(lines)

    def _find_index_heading_y(self, lines: list[dict]) -> int | None:
        for line in lines:
            text = (line.get("text") or "").strip().lower()
            if text == "index" or "अनुक्रमणिका" in text or text == "सूची":
                return line["bbox"]["y2"]
        return None

    def _fallback_from_ocr(self, lines: list[dict]) -> dict | None:
        if not lines:
            return None

        heading_idx = None
        for idx, line in enumerate(lines):
            text = (line.get("text") or "").strip().lower()
            if text == "index" or "अनुक्रमणिका" in text or text == "सूची":
                heading_idx = idx
                break

        candidate_lines = lines[heading_idx + 1 :] if heading_idx is not None else lines
        candidate_lines = [ln for ln in candidate_lines if len((ln.get("text") or "").strip()) > 0]
        if not candidate_lines:
            return None

        xs1 = [ln["bbox"]["x1"] for ln in candidate_lines]
        ys1 = [ln["bbox"]["y1"] for ln in candidate_lines]
        xs2 = [ln["bbox"]["x2"] for ln in candidate_lines]
        ys2 = [ln["bbox"]["y2"] for ln in candidate_lines]
        return {
            "x1": min(xs1),
            "y1": min(ys1),
            "x2": max(xs2),
            "y2": max(ys2),
        }
