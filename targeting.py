"""Pure targeting logic, kept separate from camera and model code."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Detection:
    """One tracked person in pixel coordinates."""

    track_id: int
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def center(self) -> tuple[float, float]:
        return ((self.x1 + self.x2) / 2, (self.y1 + self.y2) / 2)

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)

    def contains(self, x: int, y: int) -> bool:
        return self.x1 <= x <= self.x2 and self.y1 <= y <= self.y2


def select_detection(
    detections: list[Detection], click_x: int, click_y: int
) -> Detection | None:
    """Select the clicked person; overlapping boxes prefer the smallest box."""

    candidates = [item for item in detections if item.contains(click_x, click_y)]
    if not candidates:
        return None
    return min(candidates, key=lambda item: item.area)


def target_signals(
    detection: Detection, frame_width: int, frame_height: int
) -> tuple[float, float]:
    """Return horizontal error [-1, 1] and bbox-height ratio [0, 1]."""

    if frame_width <= 0 or frame_height <= 0:
        raise ValueError("frame dimensions must be positive")

    center_x, _ = detection.center
    horizontal_error = (center_x - frame_width / 2) / (frame_width / 2)
    height_ratio = max(0.0, detection.y2 - detection.y1) / frame_height
    return (
        max(-1.0, min(1.0, horizontal_error)),
        max(0.0, min(1.0, height_ratio)),
    )

