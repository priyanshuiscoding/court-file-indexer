from __future__ import annotations


def cluster_lines_by_y(lines: list[dict], tolerance: int = 12) -> list[list[dict]]:
    if not lines:
        return []

    ordered = sorted(lines, key=lambda l: (l["bbox"]["y1"], l["bbox"]["x1"]))
    rows: list[list[dict]] = []
    current: list[dict] = [ordered[0]]
    current_y = ordered[0]["bbox"]["y1"]

    for line in ordered[1:]:
        y = line["bbox"]["y1"]
        if abs(y - current_y) <= tolerance:
            current.append(line)
        else:
            rows.append(sorted(current, key=lambda l: l["bbox"]["x1"]))
            current = [line]
            current_y = y

    rows.append(sorted(current, key=lambda l: l["bbox"]["x1"]))
    return rows


def row_to_text(row: list[dict]) -> str:
    return " ".join(item["text"] for item in sorted(row, key=lambda l: l["bbox"]["x1"]))


def row_bounds(row: list[dict]) -> dict:
    xs1 = [item["bbox"]["x1"] for item in row]
    ys1 = [item["bbox"]["y1"] for item in row]
    xs2 = [item["bbox"]["x2"] for item in row]
    ys2 = [item["bbox"]["y2"] for item in row]
    return {"x1": min(xs1), "y1": min(ys1), "x2": max(xs2), "y2": max(ys2)}


def filter_lines_in_box(lines: list[dict], box: dict, tolerance: int = 4) -> list[dict]:
    selected = []
    for line in lines:
        b = line["bbox"]
        if (
            b["x1"] >= box["x1"] - tolerance
            and b["y1"] >= box["y1"] - tolerance
            and b["x2"] <= box["x2"] + tolerance
            and b["y2"] <= box["y2"] + tolerance
        ):
            selected.append(line)
    return selected
