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
    
    # Load image
    bgr_image = cv2.imread(image_path)
    if bgr_image is None:
        raise ValueError("Could not load image")
        
    lab_image = bgr_to_lab(bgr_image)
    h_img, w_img, _ = bgr_image.shape
    
    # Generate candidates
    # Use Canny edge detection
    gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    # Use Otsu's thresholding for Canny high/low thresholds or just fixed
    # Otsu is good for bimodal, but Canny is often better with fixed for general natural images
    # Let's use a fairly standard wide range
    edges = cv2.Canny(gray, 50, 150)
    
    # Find contours
    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    
    candidates = []
    
    # Optimization: deduplicate bounding boxes
    seen_boxes = set()
    
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        
        # 1. Size Filter
        if not is_valid_candidate(w, h, min_w, max_w, min_h, max_h):
            continue
            
        box_key = (x, y, w, h)
        if box_key in seen_boxes:
            continue
        seen_boxes.add(box_key)
        
        # 2. Validation
        # Get pixels along the bounding box perimeter
        perimeter_coords = get_outline_coordinates(x, y, w, h)
        
        # Extract colors for these coords
        # Handle boundary checks
        valid_coords = []
        for px, py in perimeter_coords:
            if 0 <= px < w_img and 0 <= py < h_img:
                valid_coords.append((px, py))
        
        if not valid_coords:
            continue
            
        # Get colors (N, 3)
        # Using integer indexing for speed
        rows = [c[1] for c in valid_coords]
        cols = [c[0] for c in valid_coords]
        colors = lab_image[rows, cols] # Shape (N, 3)
        
        N = len(colors)
        if N < 20: # Too small to validate with 10px neighbor logic meaningfully
             # Or maybe just pass? prompt doesn't specify min size other than user range
             # But if N < 2, logic breaks?
             pass
             
        # Vectorized check for neighbors within distance 10
        # matches[i] = True if exists j in [i-10, i+10] such that dist(C[i], C[j]) <= thresh
        
        # We can shift the colors array and compare
        has_match = np.zeros(N, dtype=bool)
        
        # Check offsets -10 to +10 (excluding 0)
        # 10 pixels distance implies we check neighbors at index distance k?
        # "within 10 pixels distance along the same bounding box"
        # Since we walked the perimeter pixel by pixel, index distance == pixel distance.
        
        for k in range(1, 11):
            # Check forward k
            # Roll colors by -k (shifts elements left, so i compares with i+k)
            # Actually if we roll by -k, index i gets value from i+k. 
            # diff = colors - roll(colors, -k) => colors[i] - colors[i+k]
            
            # Forward neighbors
            shifted_fwd = np.roll(colors, -k, axis=0)
            dists_fwd = np.linalg.norm(colors - shifted_fwd, axis=1)
            has_match |= (dists_fwd <= delta_e_threshold)
            
            # Backward neighbors
            shifted_bwd = np.roll(colors, k, axis=0)
            dists_bwd = np.linalg.norm(colors - shifted_bwd, axis=1)
            has_match |= (dists_bwd <= delta_e_threshold)
            
            # Optimization: if all true, break? (Unlikely early on)
            
        match_count = np.sum(has_match)
        validation_ratio = match_count / N if N > 0 else 0
        
        if validation_ratio >= 0.80:
            candidates.append(BoundingBox(
                x=x, y=y, w=w, h=h,
                score=validation_ratio, # Using ratio as score, could combine with perimeter length
                validation_ratio=validation_ratio
            ))
            
    # 3. Exclusivity / Non-overlap
    # Sort by score (descending)
    candidates.sort(key=lambda b: b.score, reverse=True)
    
    final_boxes = []
    # Mask for occupied pixels
    # Initialize with zeros
    occupancy_mask = np.zeros((h_img, w_img), dtype=np.uint8)
    
    for box in candidates:
        # Check overlap
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

