import numpy as np
from typing import List, Tuple

def get_outline_coordinates(x: int, y: int, w: int, h: int) -> List[Tuple[int, int]]:
    """
    Get list of (x, y) coordinates for the bounding box perimeter.
    Order: Top-Left -> Top-Right -> Bottom-Right -> Bottom-Left -> Top-Left(exclusive)
    """
    # Top edge: (x, y) to (x+w-1, y)
    top = [(x + i, y) for i in range(w)]
    # Right edge: (x+w-1, y+1) to (x+w-1, y+h-1)
    right = [(x + w - 1, y + i) for i in range(1, h)]
    # Bottom edge: (x+w-2, y+h-1) down to (x, y+h-1)
    bottom = [(x + i, y + h - 1) for i in range(w - 2, -1, -1)]
    # Left edge: (x, y+h-2) down to (x, y+1)
    left = [(x, y + i) for i in range(h - 2, 0, -1)]
    
    return top + right + bottom + left

def check_overlap_mask(mask: np.ndarray, x: int, y: int, w: int, h: int) -> bool:
    """
    Check if the region defined by x,y,w,h overlaps with any occupied pixels in the mask.
    Returns True if overlap exists.
    """
    # Ensure coordinates are within image bounds
    h_img, w_img = mask.shape
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(w_img, x + w)
    y2 = min(h_img, y + h)
    
    if x1 >= x2 or y1 >= y2:
        return False
        
    region = mask[y1:y2, x1:x2]
    return np.any(region > 0)

def mark_occupied(mask: np.ndarray, x: int, y: int, w: int, h: int) -> None:
    """
    Mark the region defined by x,y,w,h as occupied in the mask.
    """
    h_img, w_img = mask.shape
    x1 = max(0, x)
    y1 = max(0, y)
    x2 = min(w_img, x + w)
    y2 = min(h_img, y + h)
    
    mask[y1:y2, x1:x2] = 1

def is_valid_candidate(w: int, h: int, min_w: int, max_w: int, min_h: int, max_h: int) -> bool:
    return (min_w <= w <= max_w) and (min_h <= h <= max_h)

