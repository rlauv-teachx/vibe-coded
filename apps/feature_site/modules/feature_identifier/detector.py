import cv2
import numpy as np
import time
from typing import List, Tuple
from .schemas import BoundingBox, DetectionResult
from .color import bgr_to_lab, calculate_delta_e_cie76
from .geometry import get_outline_coordinates, check_overlap_mask, mark_occupied, is_valid_candidate

def detect_features(
    image_path: str,
    min_w: int,
    max_w: int,
    min_h: int,
    max_h: int,
    delta_e_threshold: float
) -> DetectionResult:
    start_time = time.time()
    
    bgr_image = cv2.imread(image_path)
    if bgr_image is None:
        raise ValueError("Could not load image")
        
    lab_image = bgr_to_lab(bgr_image)
    h_img, w_img, _ = bgr_image.shape
    
    gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    candidates = []
    
    seen_boxes = set()
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        if not is_valid_candidate(w, h, min_w, max_w, min_h, max_h):
            continue
            
        box_key = (x, y, w, h)
        if box_key in seen_boxes:
            continue
        seen_boxes.add(box_key)
        
        perimeter_coords = get_outline_coordinates(x, y, w, h)
        
        valid_coords = []
        for px, py in perimeter_coords:
            if 0 <= px < w_img and 0 <= py < h_img:
                valid_coords.append((px, py))
        
        if not valid_coords:
            continue
            
        rows = [c[1] for c in valid_coords]
        cols = [c[0] for c in valid_coords]
        colors = lab_image[rows, cols] # Shape (N, 3)
        
        N = len(colors)
        has_match = np.zeros(N, dtype=bool)
        
        for k in range(1, 11):
            
            # Forward neighbors
            shifted_fwd = np.roll(colors, -k, axis=0)
            dists_fwd = np.linalg.norm(colors - shifted_fwd, axis=1)
            has_match |= (dists_fwd <= delta_e_threshold)
            
            # Backward neighbors
            shifted_bwd = np.roll(colors, k, axis=0)
            dists_bwd = np.linalg.norm(colors - shifted_bwd, axis=1)
            has_match |= (dists_bwd <= delta_e_threshold)
            
        match_count = np.sum(has_match)
        validation_ratio = match_count / N if N > 0 else 0
        
        if validation_ratio >= 0.80:
            candidates.append(BoundingBox(
                x=x, y=y, w=w, h=h,
                score=validation_ratio,
                validation_ratio=validation_ratio
            ))
            
    candidates.sort(key=lambda b: b.score, reverse=True)
    
    final_boxes = []
    occupancy_mask = np.zeros((h_img, w_img), dtype=np.uint8)
    
    for box in candidates:
        if not check_overlap_mask(occupancy_mask, box.x, box.y, box.w, box.h):
            final_boxes.append(box)
            mark_occupied(occupancy_mask, box.x, box.y, box.w, box.h)
            
    processing_time = (time.time() - start_time) * 1000
    
    return DetectionResult(
        bounding_boxes=final_boxes,
        delta_e_method="CIE76 (Euclidean on Standard Lab)",
        delta_e_threshold=delta_e_threshold,
        processing_time_ms=processing_time
    )

