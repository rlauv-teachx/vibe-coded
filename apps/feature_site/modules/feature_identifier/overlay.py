import cv2
import numpy as np
from .schemas import BoundingBox
from typing import List

def create_overlay_image(original_image: np.ndarray, boxes: List[BoundingBox]) -> np.ndarray:
    """
    Draws bounding boxes on a copy of the original image.
    """
    overlay = original_image.copy()
    
    for box in boxes:
        # Green box
        cv2.rectangle(overlay, (box.x, box.y), (box.x + box.w, box.y + box.h), (0, 255, 0), 1)
        # Text with score
        label = f"{box.score:.2f}"
        cv2.putText(overlay, label, (box.x, box.y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
    return overlay

