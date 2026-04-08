from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


BBox = Tuple[int, int, int, int]


@dataclass
class OCRWord:
    text: str
    x1: int
    y1: int
    x2: int
    y2: int
    conf: float

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2

    @property
    def cy(self) -> float:
        return (self.y1 + self.y2) / 2

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1


@dataclass
class OCRLine:
    words: List[OCRWord] = field(default_factory=list)

    @property
    def text(self) -> str:
        ordered = sorted(self.words, key=lambda w: w.x1)
        return " ".join(w.text for w in ordered if w.text.strip()).strip()

    @property
    def y_top(self) -> int:
        return min(w.y1 for w in self.words) if self.words else 0

    @property
    def y_bottom(self) -> int:
        return max(w.y2 for w in self.words) if self.words else 0

    @property
    def x_left(self) -> int:
        return min(w.x1 for w in self.words) if self.words else 0

    @property
    def x_right(self) -> int:
        return max(w.x2 for w in self.words) if self.words else 0

    @property
    def height(self) -> int:
        return max(0, self.y_bottom - self.y_top)


@dataclass
class TableColumns:
    sno_x_max: int
    desc_x_min: int
    desc_x_max: int
    annex_x_min: int
    annex_x_max: int
    pages_x_min: int


@dataclass
class IndexRow:
    row_no: Optional[int]
    description: str
    annexure: Optional[str]
    page_start: Optional[int]
    page_end: Optional[int]
    raw_text: str
    confidence: float
    review_required: bool
    source_page: int
    bbox: Optional[BBox] = None
