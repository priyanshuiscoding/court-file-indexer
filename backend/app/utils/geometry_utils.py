from __future__ import annotations


def bbox_area(box: dict) -> int:
    return max(0, box["x2"] - box["x1"]) * max(0, box["y2"] - box["y1"])


def intersects(a: dict, b: dict) -> bool:
    return not (
        a["x2"] < b["x1"]
        or a["x1"] > b["x2"]
        or a["y2"] < b["y1"]
        or a["y1"] > b["y2"]
    )


def contains(outer: dict, inner: dict, tolerance: int = 0) -> bool:
    return (
        inner["x1"] >= outer["x1"] - tolerance
        and inner["y1"] >= outer["y1"] - tolerance
        and inner["x2"] <= outer["x2"] + tolerance
        and inner["y2"] <= outer["y2"] + tolerance
    )


def expand_box(box: dict, pad_x: int = 0, pad_y: int = 0) -> dict:
    return {
        "x1": box["x1"] - pad_x,
        "y1": box["y1"] - pad_y,
        "x2": box["x2"] + pad_x,
        "y2": box["y2"] + pad_y,
    }
