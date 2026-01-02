import os
import cv2
import numpy as np

# Configuration
BASE_URL = os.environ.get("TEST_BASE_URL", "http://127.0.0.1:8000/feature_site")

def create_test_image(filename, width=200, height=200, color=(0, 255, 0)):
    """Creates a simple test image with a rectangle."""
    img = np.zeros((height, width, 3), dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 150), color, -1)
    cv2.imwrite(filename, img)
    return filename

def remove_test_image(filename):
    """Removes the test image if it exists."""
    if os.path.exists(filename):
        os.remove(filename)

def create_dummy_text_file(filename, content="dummy content"):
    """Creates a dummy text file."""
    with open(filename, 'w') as f:
        f.write(content)
    return filename

def clean_upload_buffer():
    """Tries to remove the upload buffer file if it exists."""
    try:
        # Assuming path relative to test root
        path = os.path.join("apps", "feature_site", "uploads", "latest_upload_buffer.png")
        if os.path.exists(path):
            os.remove(path)
        # Also check other extensions
        for ext in ['.jpg', '.jpeg', '.webp']:
            path = os.path.join("apps", "feature_site", "uploads", f"latest_upload_buffer{ext}")
            if os.path.exists(path):
                os.remove(path)
    except Exception:
        pass

