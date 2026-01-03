import os
import uuid
import random
import cv2
import json
import time
import numpy as np
import base64
from py4web import action, request, response, abort, redirect, URL
from ombott import static_file
from .common import session, T, cache, url_signer, DB_FOLDER
from .settings import UPLOADS_FOLDER
from .modules.feature_identifier.detector import detect_features
from .modules.feature_identifier.overlay import create_overlay_image
from .modules.demo_utils import generate_dummy_history, create_sample_image

# Dashboard
@action('index')
@action.uses('index.html', session, T)
def index():
    history = session.get('feature_identifier_history', [])
    return dict(history=history)

@action('populate_demo', method='POST')
@action.uses(session)
def populate_demo():
    generate_dummy_history(session, UPLOADS_FOLDER, num_items=5)
    redirect(URL('index'))

@action('clear_history', method='POST')
@action.uses(session)
def clear_history():
    session['feature_identifier_history'] = []
    session['sample_generator_history'] = []
    session['canvas_drawings'] = []
    # Reset image filter state
    session['image_filter_state'] = {
            'original_file': None,
            'processed_file': None,
            'filter_type': 'grayscale',
            'intensity': 5
        }
    redirect(URL('index'))

# Distinct Feature Identifier
@action('feature_identifier', method=['GET', 'POST'])
@action.uses('feature_identifier.html', session, T)
def feature_identifier():
    # Initialize session storage for history and state if not exists
    if 'feature_identifier_history' not in session:
        session['feature_identifier_history'] = []
    
    if 'feature_identifier_state' not in session:
        session['feature_identifier_state'] = {
            'chosen_file': None,
            'form_data': {
                'min_w': 10, 'max_w': 500,
                'min_h': 10, 'max_h': 500,
                'threshold': 2.3,
                'edge_detection_method': 'canny'
            }
        }
    
    if 'canvas_drawings' in session:
        cleaned_drawings = []
        for item in session['canvas_drawings']:
            if 'canvas_filename' in item and 'canvas_data' not in item:
                cleaned_drawings.append(item)
        session['canvas_drawings'] = cleaned_drawings
    
    # Handle GET - show empty form (or set chosen file if sample provided)
    if request.method == 'GET':
        sample_filename = request.params.get('sample')
        
        # If a sample image was provided, set it as the chosen file
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
                
                session['feature_identifier_state']['chosen_file'] = sample_filename
                # Mark session as modified for nested mutation
                session['feature_identifier_state'] = session['feature_identifier_state']
                
            except Exception as e:
                return dict(
                    error=f"Error selecting sample: {str(e)}",
                    results=None,
                    image_url=None,
                    overlay_url=None,
                    json_data=None,
                    image_width=None,
                    image_height=None,
                    form_data=session['feature_identifier_state']['form_data'],
                    history=session['feature_identifier_history'],
                    chosen_file=session['feature_identifier_state']['chosen_file']
                )
        
        # Return current state
        chosen_file = session['feature_identifier_state']['chosen_file']
        image_url = URL('uploads', chosen_file) if chosen_file else None
        
        return dict(
            results=None,
            error=None,
            image_url=image_url,
            overlay_url=None,
            json_data=None,
            image_width=None,
            image_height=None,
            form_data=session['feature_identifier_state']['form_data'],
            history=session['feature_identifier_history'],
            chosen_file=chosen_file
        )
    
    # Handle POST - process the image
    try:
        # Update form data in session
        form_data = {
            'min_w': int(request.forms.get('min_w', 10)),
            'max_w': int(request.forms.get('max_w', 500)),
            'min_h': int(request.forms.get('min_h', 10)),
            'max_h': int(request.forms.get('max_h', 500)),
            'threshold': float(request.forms.get('threshold', 2.3)),
            'edge_detection_method': request.forms.get('edge_detection_method', 'canny')
        }
        session['feature_identifier_state']['form_data'] = form_data
        # Mark session as modified
        session['feature_identifier_state'] = session['feature_identifier_state']
        
        uploaded_file = request.files.get('image')
        
        safe_filename = None
        if uploaded_file and uploaded_file.filename:
            # Validate file
            filename = uploaded_file.filename
            ext = os.path.splitext(filename)[1].lower()
            if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                 return dict(error="Invalid file type", results=None, image_url=None, overlay_url=None, json_data=None, image_width=None, image_height=None, form_data=form_data, history=session['feature_identifier_history'], chosen_file=session['feature_identifier_state']['chosen_file'])
                 
            # Save file
            # OPTIMIZATION: Use a fixed filename to prevent disk usage from growing indefinitely
            # and to reuse file system blocks.
            safe_filename = "latest_upload_buffer" + ext
            file_path = os.path.join(UPLOADS_FOLDER, safe_filename)
            uploaded_file.save(file_path)
            session['feature_identifier_state']['chosen_file'] = safe_filename
            # Mark session as modified
            session['feature_identifier_state'] = session['feature_identifier_state']
        else:
            # Use previously chosen file
            safe_filename = session['feature_identifier_state'].get('chosen_file')
            
        if not safe_filename:
            return dict(error="No file selected", results=None, image_url=None, overlay_url=None, json_data=None, image_width=None, image_height=None, form_data=form_data, history=session['feature_identifier_history'], chosen_file=session['feature_identifier_state'].get('chosen_file'))
            
        file_path = os.path.join(UPLOADS_FOLDER, safe_filename)
        if not os.path.exists(file_path):
             return dict(error="File not found", results=None, image_url=None, overlay_url=None, json_data=None, image_width=None, image_height=None, form_data=form_data, history=session['feature_identifier_history'], chosen_file=session['feature_identifier_state'].get('chosen_file'))

        # Process
        detection_result = detect_features(
            file_path,
            form_data['min_w'], form_data['max_w'], 
            form_data['min_h'], form_data['max_h'],
            form_data['threshold'],
            form_data['edge_detection_method']
        )
        
        # Generate overlay
        original_image = cv2.imread(file_path)
        img_height, img_width = original_image.shape[:2]
        overlay_image = create_overlay_image(original_image, detection_result.bounding_boxes)
        
        overlay_filename = f"overlay_{safe_filename}"
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
            'image_filename': safe_filename,
            'overlay_filename': overlay_filename,
            'image_width': img_width,
            'image_height': img_height,
            'num_features': len(results_dict['bounding_boxes']),
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
            form_data=form_data,
            history=session['feature_identifier_history'],
            chosen_file=safe_filename
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dict(error=str(e), results=None, image_url=None, overlay_url=None, json_data=None, image_width=None, image_height=None, form_data=session['feature_identifier_state']['form_data'], history=session['feature_identifier_history'], chosen_file=session['feature_identifier_state']['chosen_file'])

# Sample image generator
@action('sample_generator', method=['GET', 'POST'])
@action.uses('sample_generator.html', session, T)
def sample_generator():
    if 'sample_generator_history' not in session:
        session['sample_generator_history'] = []
    
    if 'canvas_drawings' in session:
        cleaned_drawings = []
        for item in session['canvas_drawings']:
            if 'canvas_filename' in item and 'canvas_data' not in item:
                cleaned_drawings.append(item)
        session['canvas_drawings'] = cleaned_drawings
    
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
        
        # Generate image using shared utility
        image, features = create_sample_image(
            img_width, img_height, num_features,
            min_size=min_size, max_size=max_size,
            bg_color_hex=bg_color_hex,
            random_colors=random_colors,
            feature_color_hex=feature_color_hex,
            shape=shape
        )
        
        # Save image
        filename = f"sample_{uuid.uuid4()}.png"
        file_path = os.path.join(UPLOADS_FOLDER, filename)
        cv2.imwrite(file_path, image)
        
        # Add to history
        history_item = {
            'image_filename': filename,
            'image_width': img_width,
            'image_height': img_height,
            'num_features': len(features),
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
    
    cleaned_drawings = []
    for item in session['canvas_drawings']:
        if 'canvas_filename' in item and 'canvas_data' not in item:
            cleaned_drawings.append(item)
    session['canvas_drawings'] = cleaned_drawings
    
    # GET - show canvas editor with history
    if request.method == 'GET':
        # Build history with URLs for display
        history_with_urls = []
        for item in session['canvas_drawings']:
            history_with_urls.append({
                'canvas_filename': item['canvas_filename'],
                'canvas_url': URL('uploads', item['canvas_filename']),
                'canvas_width': item['canvas_width'],
                'canvas_height': item['canvas_height'],
                'timestamp': item['timestamp']
            })
        return dict(drawing_history=history_with_urls, json_history=json.dumps(history_with_urls))
    
    # POST - save drawing
    try:
        canvas_data = request.forms.get('canvas_data')
        canvas_width = int(request.forms.get('canvas_width', 200))
        canvas_height = int(request.forms.get('canvas_height', 200))
        
        if not canvas_data:
            return dict(success=False, error="No canvas data provided")
        
        if ',' in canvas_data:
            base64_data = canvas_data.split(',', 1)[1]
        else:
            base64_data = canvas_data
        
        image_bytes = base64.b64decode(base64_data)
        filename = f"canvas_{uuid.uuid4()}.png"
        file_path = os.path.join(UPLOADS_FOLDER, filename)
        with open(file_path, 'wb') as f:
            f.write(image_bytes)
        
        drawing_item = {
            'canvas_filename': filename,
            'canvas_width': canvas_width,
            'canvas_height': canvas_height,
            'timestamp': str(uuid.uuid4())
        }
        
        # Prepend to history
        session['canvas_drawings'].insert(0, drawing_item)
        # Keep only last 20 items
        session['canvas_drawings'] = session['canvas_drawings'][:20]
        
        history_with_urls = []
        for item in session['canvas_drawings']:
            history_with_urls.append({
                'canvas_filename': item['canvas_filename'],
                'canvas_url': URL('uploads', item['canvas_filename']),
                'canvas_width': item['canvas_width'],
                'canvas_height': item['canvas_height'],
                'timestamp': item['timestamp']
            })
        
        return dict(success=True, drawing_id=drawing_item['timestamp'], drawing_history=history_with_urls, json_history=json.dumps(history_with_urls))
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        history_with_urls = []
        for item in session.get('canvas_drawings', []):
            if 'canvas_filename' in item:  # Only include new-format items
                history_with_urls.append({
                    'canvas_filename': item['canvas_filename'],
                    'canvas_url': URL('uploads', item['canvas_filename']),
                    'canvas_width': item['canvas_width'],
                    'canvas_height': item['canvas_height'],
                    'timestamp': item['timestamp']
                })
        return dict(success=False, error=str(e), drawing_history=history_with_urls)

# Manage Data
@action('manage_data')
@action.uses('manage_data.html', session, T)
def manage_data():
    return dict(
        feature_history=session.get('feature_identifier_history', []),
        sample_history=session.get('sample_generator_history', []),
        canvas_history=session.get('canvas_drawings', [])
    )

@action('delete_item', method='POST')
@action.uses(session)
def delete_item():
    item_id = request.forms.get('item_id')
    item_type = request.forms.get('item_type')
    
    if not item_id or not item_type:
        redirect(URL('manage_data'))
        
    if item_type == 'feature':
        history = session.get('feature_identifier_history', [])
        for i, item in enumerate(history):
            if item['timestamp'] == item_id:
                # Delete files
                for key in ['image_filename', 'overlay_filename']:
                    filename = item.get(key)
                    if filename:
                        filepath = os.path.join(UPLOADS_FOLDER, filename)
                        if os.path.exists(filepath) and not item.get('is_demo'):
                            try:
                                os.remove(filepath)
                            except:
                                pass
                # Remove from history
                history.pop(i)
                session['feature_identifier_history'] = history
                break
    elif item_type == 'sample':
        history = session.get('sample_generator_history', [])
        for i, item in enumerate(history):
            if item['timestamp'] == item_id:
                # Delete file
                filename = item.get('image_filename')
                if filename:
                    filepath = os.path.join(UPLOADS_FOLDER, filename)
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except:
                            pass
                # Remove from history
                history.pop(i)
                session['sample_generator_history'] = history
                break
    elif item_type == 'canvas':
        history = session.get('canvas_drawings', [])
        for i, item in enumerate(history):
            if item['timestamp'] == item_id:
                # Delete file
                filename = item.get('canvas_filename')
                if filename:
                    filepath = os.path.join(UPLOADS_FOLDER, filename)
                    if os.path.exists(filepath):
                        try:
                            os.remove(filepath)
                        except:
                            pass
                # Remove from history
                history.pop(i)
                session['canvas_drawings'] = history
                break
                
    redirect(URL('manage_data'))

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

# Image Filter
@action('image_filter', method=['GET', 'POST'])
@action.uses('image_filter.html', session, T)
def image_filter():
    if 'image_filter_state' not in session:
        session['image_filter_state'] = {
            'original_file': None,
            'current_file': None,
            'filter_type': 'grayscale',
            'intensity': 5
        }
        
    error = None
    state = session['image_filter_state']
    
    # Handle GET
    if request.method == 'GET':
        return dict(
            error=None,
            current_image_url=URL('uploads', state['current_file']) if state['current_file'] else (URL('uploads', state['original_file']) if state['original_file'] else None),
            filter_type=state['filter_type'],
            intensity=state['intensity']
        )
        
    # Handle POST
    try:
        action_type = request.forms.get('action')
        
        # 1. Upload
        if action_type == 'upload':
            uploaded_file = request.files.get('image')
            if uploaded_file and uploaded_file.filename:
                filename = uploaded_file.filename
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
                     error = "Invalid file type"
                else:
                    safe_filename = f"{uuid.uuid4()}{ext}"
                    file_path = os.path.join(UPLOADS_FOLDER, safe_filename)
                    uploaded_file.save(file_path)
                    
                    state['original_file'] = safe_filename
                    state['current_file'] = safe_filename # Reset current to original
            else:
                error = "No file selected"

        # 2. Reset
        elif action_type == 'reset':
            state['current_file'] = state['original_file']

        # 3. Apply Filter
        elif action_type == 'filter':
            filter_type = request.forms.get('filter_type', 'grayscale')
            intensity = int(request.forms.get('intensity', 5))
            
            state['filter_type'] = filter_type
            state['intensity'] = intensity
            
            target_file = state['current_file'] or state['original_file']
            
            if target_file:
                file_path = os.path.join(UPLOADS_FOLDER, target_file)
                if os.path.exists(file_path):
                    img = cv2.imread(file_path)
                    
                    # Apply Filters
                    if filter_type == 'grayscale':
                        processed = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                        processed = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
                    elif filter_type == 'blur':
                        ksize = intensity * 2 + 1 
                        processed = cv2.GaussianBlur(img, (ksize, ksize), 0)
                    elif filter_type == 'invert':
                        processed = cv2.bitwise_not(img)
                    elif filter_type == 'sepia':
                        kernel = np.array([[0.272, 0.534, 0.131],
                                           [0.349, 0.686, 0.168],
                                           [0.393, 0.769, 0.189]])
                        processed = cv2.transform(img, kernel)
                        processed = np.clip(processed, 0, 255).astype(np.uint8)
                    elif filter_type == 'sharpen':
                        kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
                        processed = cv2.filter2D(img, -1, kernel)
                    elif filter_type == 'edge_enhance':
                         kernel = np.array([[-1,-1,-1,-1,-1],
                                   [-1,2,2,2,-1],
                                   [-1,2,8,2,-1],
                                   [-1,2,2,2,-1],
                                   [-1,-1,-1,-1,-1]]) / 8.0
                         processed = cv2.filter2D(img, -1, kernel)
                    else:
                        processed = img
                        
                    # Save
                    new_filename = f"filtered_{uuid.uuid4()}.png"
                    new_path = os.path.join(UPLOADS_FOLDER, new_filename)
                    cv2.imwrite(new_path, processed)
                    state['current_file'] = new_filename
                else:
                    error = "File not found"
            else:
                error = "No image to filter"

        # 4. Detect Features (Auto)
        elif action_type == 'detect':
            target_file = state['current_file'] or state['original_file']
            method = request.forms.get('method', 'canny')
            
            if target_file:
                file_path = os.path.join(UPLOADS_FOLDER, target_file)
                if os.path.exists(file_path):
                    # Use default moderate params for quick detection
                    detection_result = detect_features(
                        file_path,
                        min_w=10, max_w=5000, 
                        min_h=10, max_h=5000,
                        delta_e_threshold=5.0, # looser threshold
                        edge_detection_method=method
                    )
                    
                    original_image = cv2.imread(file_path)
                    overlay_image = create_overlay_image(original_image, detection_result.bounding_boxes)
                    
                    new_filename = f"detected_{uuid.uuid4()}.png"
                    new_path = os.path.join(UPLOADS_FOLDER, new_filename)
                    cv2.imwrite(new_path, overlay_image)
                    state['current_file'] = new_filename
                else:
                     error = "File not found"
            else:
                 error = "No image to detect on"

        # 5. Draw Manual Boxes
        elif action_type == 'draw_boxes':
            target_file = state['current_file'] or state['original_file']
            boxes_json = request.forms.get('boxes')
            
            if target_file and boxes_json:
                file_path = os.path.join(UPLOADS_FOLDER, target_file)
                if os.path.exists(file_path):
                    try:
                        boxes = json.loads(boxes_json)
                        img = cv2.imread(file_path)
                        h_img, w_img = img.shape[:2]
                        
                        # Draw boxes
                        for box in boxes:
                            # Coordinates are normalized (0-1), convert to pixels
                            x = int(box['x'] * w_img)
                            y = int(box['y'] * h_img)
                            w = int(box['w'] * w_img)
                            h = int(box['h'] * h_img)
                            
                            # Draw rectangle (Green, thickness 2)
                            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                            
                        new_filename = f"drawn_{uuid.uuid4()}.png"
                        new_path = os.path.join(UPLOADS_FOLDER, new_filename)
                        cv2.imwrite(new_path, img)
                        state['current_file'] = new_filename
                        
                    except json.JSONDecodeError:
                        error = "Invalid box data"
                else:
                    error = "File not found"
            else:
                error = "Missing data"

        # Save session
        session['image_filter_state'] = state
        
        return dict(
            error=error,
            current_image_url=URL('uploads', state['current_file']) if state['current_file'] else (URL('uploads', state['original_file']) if state['original_file'] else None),
            filter_type=state['filter_type'],
            intensity=state['intensity']
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dict(
            error=str(e),
            current_image_url=None,
            filter_type='grayscale',
            intensity=5
        )

