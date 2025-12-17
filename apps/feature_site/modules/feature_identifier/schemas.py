from dataclasses import dataclass
from typing import List, Tuple

@dataclass
class BoundingBox:
    x: int
    y: int
    w: int
    h: int
    score: float
    validation_ratio: float

@dataclass
class DetectionResult:
    bounding_boxes: List[BoundingBox]
    delta_e_method: str
    delta_e_threshold: float
    processing_time_ms: float

