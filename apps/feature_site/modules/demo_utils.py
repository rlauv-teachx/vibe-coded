import os
import uuid
import random
import cv2
import numpy as np

def create_sample_image(width, height, num_features, min_size=10, max_size=40, bg_color_hex='#e8e8e8', random_colors=True, feature_color_hex='#ff0000', shape='mixed'):
    """
    Core logic to generate a sample image with random shapes.
    Extracted from controllers.py for reusability.
    """
    # Parse background color
    bg_color = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (4, 2, 0))  # BGR
    
    # Create image with background
    image = np.full((height, width, 3), bg_color, dtype=np.uint8)
    
    features = []
    attempts = 0
    max_attempts = num_features * 20
    
    while len(features) < num_features and attempts < max_attempts:
        attempts += 1
        
        # Random size
        w = random.randint(min_size, max_size)
        h = random.randint(min_size, max_size)
        
        # Random position (ensure it fits)
        if w >= width - 4 or h >= height - 4:
            continue
        x = random.randint(2, width - w - 2)
        y = random.randint(2, height - h - 2)
        
        # Check for overlap
        overlap = False
        for f in features:
            if (x < f['x'] + f['w'] + 2 and x + w + 2 > f['x'] and
                y < f['y'] + f['h'] + 2 and y + h + 2 > f['y']):
                overlap = True
                break
        if overlap:
            continue
        
        # Color
        if random_colors:
            while True:
                color_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                bg_rgb = (bg_color[2], bg_color[1], bg_color[0])
                diff = sum(abs(a - b) for a, b in zip(color_rgb, bg_rgb))
                if diff > 150:
                    break
            color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])
            color_hex = '#{:02x}{:02x}{:02x}'.format(*color_rgb)
        else:
            color_bgr = tuple(int(feature_color_hex.lstrip('#')[i:i+2], 16) for i in (4, 2, 0))
            color_hex = feature_color_hex
        
        # Shape
        use_shape = shape if shape != 'mixed' else random.choice(['rectangle', 'ellipse'])
        if use_shape == 'rectangle':
            cv2.rectangle(image, (x, y), (x + w, y + h), color_bgr, -1)
        else:
            center = (x + w // 2, y + h // 2)
            axes = (w // 2, h // 2)
            cv2.ellipse(image, center, axes, 0, 0, 360, color_bgr, -1)
        
        features.append({
            'x': x, 'y': y, 'w': w, 'h': h,
            'color': color_hex, 'shape': use_shape
        })
    
    return image, features

def generate_dummy_history(session, uploads_folder, num_items=5):
    """
    Generates dummy data using the actual sample generation logic.
    """
    if 'feature_identifier_history' not in session:
        session['feature_identifier_history'] = []
        
    presets = [
        {"w": 800, "h": 600, "num": 12, "bg": "#f0f0f0", "shape": "mixed"},
        {"w": 400, "h": 400, "num": 5, "bg": "#ffffff", "shape": "rectangle"},
        {"w": 640, "h": 480, "num": 20, "bg": "#e0e0e0", "shape": "ellipse"},
        {"w": 1024, "h": 768, "num": 8, "bg": "#d0d0d0", "shape": "mixed"},
        {"w": 500, "h": 500, "num": 15, "bg": "#f5f5f5", "shape": "rectangle"},
    ]

    for _ in range(num_items):
        preset = random.choice(presets)
        fake_filename = f"demo_{uuid.uuid4().hex[:8]}.png"
        file_path = os.path.join(uploads_folder, fake_filename)
        
        # Use the real generator logic
        image, features = create_sample_image(
            preset['w'], preset['h'], preset['num'],
            bg_color_hex=preset['bg'],
            shape=preset['shape']
        )
        
        cv2.imwrite(file_path, image)
        
        # For demo purposes, we'll use the same image as the overlay
        # In a real run, the detector would generate this.
        overlay_filename = f"overlay_{fake_filename}"
        overlay_path = os.path.join(uploads_folder, overlay_filename)
        cv2.imwrite(overlay_path, image)
        
        history_item = {
            'image_filename': fake_filename,
            'overlay_filename': overlay_filename,
            'image_width': preset['w'],
            'image_height': preset['h'],
            'num_features': len(features),
            'timestamp': str(uuid.uuid4()),
            'is_demo': True
        }
        session['feature_identifier_history'].insert(0, history_item)
    
    session['feature_identifier_history'] = session['feature_identifier_history'][:20]
    return len(session['feature_identifier_history'])
