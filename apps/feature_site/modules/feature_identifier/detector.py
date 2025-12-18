import cv2
import numpy as np
import time
from typing import List, Tuple
from .schemas import BoundingBox, DetectionResult
from .color import bgr_to_lab, calculate_delta_e_cie76
from .geometry import get_outline_coordinates, check_overlap_mask, mark_occupied, is_valid_candidate

def get_dominant_color(bgr_image: np.ndarray, x: int, y: int, w: int, h: int) -> str:
    """
    Extract the dominant color from a bounding box region.
    
    Args:
        bgr_image: BGR color image
        x, y: Top-left corner coordinates
        w, h: Width and height
        
    Returns:
        Hex color string (e.g., "#FF0000")
    """
    # Crop region
    region = bgr_image[y:y+h, x:x+w]
    
    # Reshape to list of pixels
    pixels = region.reshape((-1, 3))
    
    # Convert to float
    pixels = np.float32(pixels)
    
    # K-means clustering to find dominant color
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
    _, _, centers = cv2.kmeans(pixels, 1, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    
    # Get the dominant color (BGR format)
    dominant_color_bgr = centers[0].astype(int)
    
    # Convert BGR to RGB
    r, g, b = dominant_color_bgr[2], dominant_color_bgr[1], dominant_color_bgr[0]
    
    # Convert to hex
    hex_color = f"#{r:02X}{g:02X}{b:02X}"
    
    return hex_color

def apply_sobel_edge_detection(gray_image: np.ndarray) -> np.ndarray:
    """
    Apply Sobel edge detection to an image.
    
    Args:
        gray_image: Grayscale image
        
    Returns:
        Binary edge map
    """
    # Apply Sobel operator in x and y directions
    sobelx = cv2.Sobel(gray_image, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray_image, cv2.CV_64F, 0, 1, ksize=3)
    
    # Compute magnitude
    magnitude = np.sqrt(sobelx**2 + sobely**2)
    
    # Normalize to 0-255
    magnitude = np.uint8(255 * magnitude / np.max(magnitude))
    
    # Apply threshold to get binary image
    _, edges = cv2.threshold(magnitude, 100, 255, cv2.THRESH_BINARY)
    
    return edges

def detect_features(
    image_path: str,
    min_w: int,
    max_w: int,
    min_h: int,
    max_h: int,
    delta_e_threshold: float,
    edge_detection_method: str = "canny"
) -> DetectionResult:
    start_time = time.time()
    
    bgr_image = cv2.imread(image_path)
    if bgr_image is None:
        raise ValueError("Could not load image")
        
    lab_image = bgr_to_lab(bgr_image)
    h_img, w_img, _ = bgr_image.shape
    
    gray = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2GRAY)
    
    # Apply selected edge detection method
    if edge_detection_method.lower() == "sobel":
        edges = apply_sobel_edge_detection(gray)
    else:  # default to canny
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
            # Extract dominant color from the region
            color_hex = get_dominant_color(bgr_image, x, y, w, h)
            
            candidates.append(BoundingBox(
                x=x, y=y, w=w, h=h,
                score=validation_ratio,
                validation_ratio=validation_ratio,
                color_hex=color_hex
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

