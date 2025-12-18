from dataclasses import dataclass
from typing import List, Tuple, Optional

@dataclass
class BoundingBox:
    x: int
    y: int
    w: int
    h: int
    score: float
    validation_ratio: float
    color_hex: Optional[str] = None  # RGB hex color, e.g., "#FF0000"

@dataclass
class DetectionResult:
    bounding_boxes: List[BoundingBox]
    delta_e_method: str
    delta_e_threshold: float
    processing_time_ms: float

