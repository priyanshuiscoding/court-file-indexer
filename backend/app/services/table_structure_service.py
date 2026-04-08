from __future__ import annotations

import cv2


class TableStructureService:
    def detect_table_lines(self, image_path: str) -> dict:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        if image is None:
            return {"horizontal": [], "vertical": []}

        binary = cv2.threshold(image, 180, 255, cv2.THRESH_BINARY_INV)[1]
        h_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        v_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))

        h_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, h_kernel)
        v_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, v_kernel)

        h_contours, _ = cv2.findContours(h_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        v_contours, _ = cv2.findContours(v_lines, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        horizontal = [cv2.boundingRect(c) for c in h_contours]
        vertical = [cv2.boundingRect(c) for c in v_contours]
        return {"horizontal": horizontal, "vertical": vertical}
