import re


def parse_page_range(value: str | None) -> tuple[int | None, int | None]:
    if not value:
        return None, None

    text = value.strip()
    text = text.replace("–", "-").replace("—", "-")
    text = re.sub(r"\bto\b", "-", text, flags=re.IGNORECASE)
    text = re.sub(r"[^0-9\-]", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    if not text:
        return None, None

    if "-" in text:
        left, right = text.split("-", 1)
        left_int = _to_int(left)
        right_int = _to_int(right)
        return left_int, right_int

    number = _to_int(text)
    return number, number


def parse_page_range_from_text(text: str) -> tuple[int | None, int | None, str | None]:
    if not text:
        return None, None, None

    patterns = [
        r"\b\d{1,3}\s*[-–]\s*\d{1,3}\b",
        r"\b\d{1,3}\s+to\s+\d{1,3}\b",
        r"\b\d{1,3}\b",
    ]

    matches = []
    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            raw = m.group(0)
            start, end = parse_page_range(raw)
            if start is None:
                continue
            matches.append((m.start(), start, end, raw))

    if not matches:
        return None, None, None

    # Court index pages usually place page no near the right side / end of line.
    matches.sort(key=lambda x: x[0], reverse=True)
    _, start, end, raw = matches[0]
    return start, end, raw


def _to_int(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None
