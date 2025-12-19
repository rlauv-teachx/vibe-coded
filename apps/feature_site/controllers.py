import os
import uuid
import random
import cv2
import json
import numpy as np
import base64
from py4web import action, request, response, abort, redirect, URL
from ombott import static_file
from .common import session, T, cache, url_signer
from .settings import UPLOADS_FOLDER
from .modules.feature_identifier.detector import detect_features
from .modules.feature_identifier.overlay import create_overlay_image

# Allow CORS if needed, or just standard serving
@action('index', method=['GET', 'POST'])
@action.uses('index.html', session, T)
def index():
    # Initialize session storage for history if not exists
    if 'feature_identifier_history' not in session:
        session['feature_identifier_history'] = []
    
    # Handle GET - show empty form (or process sample if provided)
    if request.method == 'GET':
        sample_filename = request.params.get('sample')
        
        # If a sample image was provided, automatically process it
        if sample_filename:
            try:
                # Validate filename to prevent path traversal
                if '..' in sample_filename or '/' in sample_filename or '\\' in sample_filename:
                    raise ValueError("Invalid filename")
                
                file_path = os.path.join(UPLOADS_FOLDER, sample_filename)
                
                # Verify file exists and is within uploads folder
                if not os.path.abspath(file_path).startswith(os.path.abspath(UPLOADS_FOLDER)):
                    raise ValueError("Invalid file path")
                if not os.path.exists(file_path):
                    raise ValueError("File not found")
                
                # Use default parameters for sample processing
                min_w, max_w = 0, 10000
                min_h, max_h = 0, 10000
                threshold = 2.3
                edge_detection_method = 'canny'
                
                # Process
                detection_result = detect_features(
                    file_path,
                    min_w, max_w, min_h, max_h,
                    threshold,
                    edge_detection_method
                )
                
                # Generate overlay
                original_image = cv2.imread(file_path)
                img_height, img_width = original_image.shape[:2]
                overlay_image = create_overlay_image(original_image, detection_result.bounding_boxes)
                
                overlay_filename = f"overlay_{sample_filename}"
                overlay_path = os.path.join(UPLOADS_FOLDER, overlay_filename)
                cv2.imwrite(overlay_path, overlay_image)
                
                # Serialize result for display/download
                results_dict = {
                    "bounding_boxes": [
                        {"x": b.x, "y": b.y, "w": b.w, "h": b.h, "score": b.score, "validation_ratio": b.validation_ratio, "color_hex": b.color_hex}
                        for b in detection_result.bounding_boxes
                    ],
                    "delta_e_method": detection_result.delta_e_method,
                    "delta_e_threshold": detection_result.delta_e_threshold,
                    "processing_time_ms": detection_result.processing_time_ms
                }
                
                # Add to history
                history_item = {
                    'image_filename': sample_filename,
                    'overlay_filename': overlay_filename,
                    'image_width': img_width,
                    'image_height': img_height,
                    'results': results_dict,
                    'form_data': {
                        'min_w': min_w, 'max_w': max_w,
                        'min_h': min_h, 'max_h': max_h,
                        'threshold': threshold,
                        'edge_detection_method': edge_detection_method
                    },
                    'timestamp': str(uuid.uuid4())
                }
                
                # Prepend to history (most recent first)
                session['feature_identifier_history'].insert(0, history_item)
                # Keep only last 20 items
                session['feature_identifier_history'] = session['feature_identifier_history'][:20]
                
                return dict(
                    results=results_dict,
                    error=None,
                    image_url=URL('uploads', sample_filename),
                    overlay_url=URL('uploads', overlay_filename),
                    json_data=json.dumps(results_dict, indent=2),
                    image_width=img_width,
                    image_height=img_height,
                    form_data={
                        'min_w': min_w, 'max_w': max_w,
                        'min_h': min_h, 'max_h': max_h,
                        'threshold': threshold,
                        'edge_detection_method': edge_detection_method
                    },
                    history=session['feature_identifier_history']
                )
            except Exception as e:
                import traceback
                traceback.print_exc()
                return dict(
                    error=f"Error processing sample: {str(e)}",
                    results=None,
                    image_url=None,
                    overlay_url=None,
                    json_data=None,
                    image_width=None,
                    image_height=None,
                    form_data={},
                    history=session['feature_identifier_history']
                )
        
        # No sample provided, show empty form
        return dict(
            results=None,
            error=None,
            image_url=None,
            overlay_url=None,
            json_data=None,
            image_width=None,
            image_height=None,
            form_data={},
            history=session['feature_identifier_history']
        )
    
    # Handle POST - process the image
    try:
        min_w = int(request.forms.get('min_w', 0))
        max_w = int(request.forms.get('max_w', 10000))
        min_h = int(request.forms.get('min_h', 0))
        max_h = int(request.forms.get('max_h', 10000))
        threshold = float(request.forms.get('threshold', 2.3)) # Default CIE76 threshold often around 2.3
        edge_detection_method = request.forms.get('edge_detection_method', 'canny')
        
        uploaded_file = request.files.get('image')
        
        if not uploaded_file:
            return dict(error="No file uploaded", results=None, image_url=None, overlay_url=None, json_data=None, image_width=None, image_height=None, form_data={}, history=session['feature_identifier_history'])
            
        # Validate file
        filename = uploaded_file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
             return dict(error="Invalid file type", results=None, image_url=None, overlay_url=None, json_data=None, image_width=None, image_height=None, form_data={}, history=session['feature_identifier_history'])
             
        # Save file
        safe_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOADS_FOLDER, safe_filename)
        uploaded_file.save(file_path)
        
        # Process
        detection_result = detect_features(
            file_path,
            min_w, max_w, min_h, max_h,
            threshold,
            edge_detection_method
        )
        
        # Generate overlay
        original_image = cv2.imread(file_path)
        img_height, img_width = original_image.shape[:2]
        overlay_image = create_overlay_image(original_image, detection_result.bounding_boxes)
        
        overlay_filename = f"overlay_{safe_filename}"
        overlay_path = os.path.join(UPLOADS_FOLDER, overlay_filename)
        cv2.imwrite(overlay_path, overlay_image)
        
        # Serialize result for display/download
        # Convert dataclass to dict
        results_dict = {
            "bounding_boxes": [
                {"x": b.x, "y": b.y, "w": b.w, "h": b.h, "score": b.score, "validation_ratio": b.validation_ratio, "color_hex": b.color_hex}
                for b in detection_result.bounding_boxes
            ],
            "delta_e_method": detection_result.delta_e_method,
            "delta_e_threshold": detection_result.delta_e_threshold,
            "processing_time_ms": detection_result.processing_time_ms
        }
        
        # Add to history
        history_item = {
            'image_filename': safe_filename,
            'overlay_filename': overlay_filename,
            'image_width': img_width,
            'image_height': img_height,
            'results': results_dict,
            'form_data': {
                'min_w': min_w, 'max_w': max_w,
                'min_h': min_h, 'max_h': max_h,
                'threshold': threshold,
                'edge_detection_method': edge_detection_method
            },
            'timestamp': str(uuid.uuid4())
        }
        
        # Prepend to history (most recent first)
        session['feature_identifier_history'].insert(0, history_item)
        # Keep only last 20 items
        session['feature_identifier_history'] = session['feature_identifier_history'][:20]
        
        return dict(
            results=results_dict,
            error=None,
            image_url=URL('uploads', safe_filename),
            overlay_url=URL('uploads', overlay_filename),
            json_data=json.dumps(results_dict, indent=2),
            image_width=img_width,
            image_height=img_height,
            form_data={
                'min_w': min_w, 'max_w': max_w,
                'min_h': min_h, 'max_h': max_h,
                'threshold': threshold,
                'edge_detection_method': edge_detection_method
            },
            history=session['feature_identifier_history']
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dict(error=str(e), results=None, image_url=None, overlay_url=None, json_data=None, image_width=None, image_height=None, form_data={}, history=session['feature_identifier_history'])

# Sample image generator
@action('sample_generator', method=['GET', 'POST'])
@action.uses('sample_generator.html', session, T)
def sample_generator():
    # Initialize session storage for history if not exists
    if 'sample_generator_history' not in session:
        session['sample_generator_history'] = []
    
    # Handle GET - show empty form
    if request.method == 'GET':
        return dict(
            error=None,
            image_url=None,
            image_filename=None,
            image_width=None,
            image_height=None,
            features=[],
            form_data={},
            history=session['sample_generator_history']
        )
    
    # Handle POST - generate sample image
    try:
        img_width = int(request.forms.get('img_width', 200))
        img_height = int(request.forms.get('img_height', 200))
        num_features = int(request.forms.get('num_features', 5))
        min_size = int(request.forms.get('min_size', 10))
        max_size = int(request.forms.get('max_size', 40))
        bg_color_hex = request.forms.get('bg_color', '#e8e8e8')
        random_colors = request.forms.get('random_colors') == 'on'
        feature_color_hex = request.forms.get('feature_color', '#ff0000')
        shape = request.forms.get('shape', 'rectangle')
        
        # Parse background color
        bg_color = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (4, 2, 0))  # BGR
        
        # Create image with background
        image = np.full((img_height, img_width, 3), bg_color, dtype=np.uint8)
        
        features = []
        attempts = 0
        max_attempts = num_features * 20
        
        while len(features) < num_features and attempts < max_attempts:
            attempts += 1
            
            # Random size
            w = random.randint(min_size, max_size)
            h = random.randint(min_size, max_size)
            
            # Random position (ensure it fits)
            if w >= img_width - 4 or h >= img_height - 4:
                continue
            x = random.randint(2, img_width - w - 2)
            y = random.randint(2, img_height - h - 2)
            
            # Check for overlap with existing features
            overlap = False
            for f in features:
                if (x < f['x'] + f['w'] + 2 and x + w + 2 > f['x'] and
                    y < f['y'] + f['h'] + 2 and y + h + 2 > f['y']):
                    overlap = True
                    break
            if overlap:
                continue
            
            # Generate color
            if random_colors:
                # Generate a color that's visually distinct from background
                while True:
                    color_rgb = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                    # Simple brightness/hue difference check
                    bg_rgb = (bg_color[2], bg_color[1], bg_color[0])
                    diff = sum(abs(a - b) for a, b in zip(color_rgb, bg_rgb))
                    if diff > 150:  # Ensure sufficient contrast
                        break
                color_bgr = (color_rgb[2], color_rgb[1], color_rgb[0])
                color_hex = '#{:02x}{:02x}{:02x}'.format(*color_rgb)
            else:
                color_bgr = tuple(int(feature_color_hex.lstrip('#')[i:i+2], 16) for i in (4, 2, 0))
                color_hex = feature_color_hex
            
            # Draw feature
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
        
        # Save image
        filename = f"sample_{uuid.uuid4()}.png"
        file_path = os.path.join(UPLOADS_FOLDER, filename)
        cv2.imwrite(file_path, image)
        
        # Add to history
        history_item = {
            'image_filename': filename,
            'image_width': img_width,
            'image_height': img_height,
            'features': features,
            'form_data': {
                'img_width': img_width, 'img_height': img_height,
                'num_features': num_features,
                'min_size': min_size, 'max_size': max_size,
                'bg_color': bg_color_hex,
                'random_colors': random_colors,
                'feature_color': feature_color_hex,
                'shape': shape
            },
            'timestamp': str(uuid.uuid4())
        }
        
        # Prepend to history (most recent first)
        session['sample_generator_history'].insert(0, history_item)
        # Keep only last 20 items
        session['sample_generator_history'] = session['sample_generator_history'][:20]
        
        return dict(
            error=None,
            image_url=URL('uploads', filename),
            image_filename=filename,
            image_width=img_width,
            image_height=img_height,
            features=features,
            form_data={
                'img_width': img_width, 'img_height': img_height,
                'num_features': num_features,
                'min_size': min_size, 'max_size': max_size,
                'bg_color': bg_color_hex,
                'random_colors': random_colors,
                'feature_color': feature_color_hex,
                'shape': shape
            },
            history=session['sample_generator_history']
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dict(error=str(e), image_url=None, image_filename=None, image_width=None, image_height=None, features=[], form_data={}, history=session['sample_generator_history'])

# Canvas editor
@action('canvas_editor', method=['GET', 'POST'])
@action.uses('canvas_editor.html', session, T)
def canvas_editor():
    # Initialize session storage for drawing history if not exists
    if 'canvas_drawings' not in session:
        session['canvas_drawings'] = []
    
    # GET - show canvas editor with history
    if request.method == 'GET':
        return dict(drawing_history=session['canvas_drawings'])
    
    # POST - save drawing
    try:
        canvas_data = request.forms.get('canvas_data')
        canvas_width = int(request.forms.get('canvas_width', 200))
        canvas_height = int(request.forms.get('canvas_height', 200))
        
        if not canvas_data:
            return dict(success=False, error="No canvas data provided")
        
        # Save the drawing with metadata
        drawing_item = {
            'canvas_data': canvas_data,
            'canvas_width': canvas_width,
            'canvas_height': canvas_height,
            'timestamp': str(uuid.uuid4())
        }
        
        # Prepend to history
        session['canvas_drawings'].insert(0, drawing_item)
        # Keep only last 20 items
        session['canvas_drawings'] = session['canvas_drawings'][:20]
        
        return dict(success=True, drawing_id=drawing_item['timestamp'], drawing_history=session['canvas_drawings'])
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dict(success=False, error=str(e))

# Serve uploads
@action('uploads/<filename>')
def serve_upload(filename):
    # Prevent path traversal attacks
    if '..' in filename or '/' in filename or '\\' in filename:
        abort(403)
    filepath = os.path.join(UPLOADS_FOLDER, filename)
    if not os.path.abspath(filepath).startswith(os.path.abspath(UPLOADS_FOLDER)):
        abort(403)
    return static_file(filename, root=UPLOADS_FOLDER)

