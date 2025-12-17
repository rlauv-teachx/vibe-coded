import numpy as np
import cv2

def bgr_to_lab(image: np.ndarray) -> np.ndarray:
    """
    Convert BGR image to CIE Lab.
    OpenCV scales L to 0-255, a and b to 0-255.
    We return this as is, but we'll handle conversion to standard Lab in delta_e calculation
    if strict adherence to standard units is needed. 
    However, often calculating Euclidean distance on the scaled values is sufficient 
    if the threshold is adjusted.
    
    To be precise and allow user-standard thresholds (like 2.3), we will convert to standard Lab.
    """
    lab_scaled = cv2.cvtColor(image, cv2.COLOR_BGR2Lab).astype(np.float32)
    
    # Convert to standard Lab
    # L: 0..255 -> 0..100
    # a: 0..255 -> -128..127
    # b: 0..255 -> -128..127
    l_channel, a_channel, b_channel = cv2.split(lab_scaled)
    
    l_std = l_channel * 100.0 / 255.0
    a_std = a_channel - 128.0
    b_std = b_channel - 128.0
    
    return cv2.merge([l_std, a_std, b_std])

def calculate_delta_e_cie76(color1: np.ndarray, color2: np.ndarray) -> float:
    """
    Calculate CIE76 Delta E between two Lab colors.
    Input colors should be arrays/tuples of (L, a, b).
    Returns Euclidean distance.
    """
    return np.linalg.norm(color1 - color2)

def batch_delta_e_cie76(color_array: np.ndarray, target_color: np.ndarray) -> np.ndarray:
    """
    Calculate CIE76 Delta E between an array of colors and a target color.
    """
    diff = color_array - target_color
    return np.linalg.norm(diff, axis=1)

