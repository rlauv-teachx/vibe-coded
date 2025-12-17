import os
import uuid
import cv2
import json
from py4web import action, request, response, abort, redirect, URL
from .common import session, T, cache, url_signer
from .settings import UPLOADS_FOLDER
from .modules.feature_identifier.detector import detect_features
from .modules.feature_identifier.overlay import create_overlay_image

# Allow CORS if needed, or just standard serving
@action('index', method=['GET', 'POST'])
@action.uses('index.html', session, T)
def index():
    return dict(
        results=None,
        error=None,
        image_url=None,
        overlay_url=None,
        json_data=None,
        form_data={}
    )

@action('process_image', method=['POST'])
@action.uses('index.html', session, T)
def process_image():
    # Parse inputs
    try:
        min_w = int(request.forms.get('min_w', 0))
        max_w = int(request.forms.get('max_w', 10000))
        min_h = int(request.forms.get('min_h', 0))
        max_h = int(request.forms.get('max_h', 10000))
        threshold = float(request.forms.get('threshold', 2.3)) # Default CIE76 threshold often around 2.3
        
        uploaded_file = request.files.get('image')
        
        if not uploaded_file:
            return dict(error="No file uploaded", results=None)
            
        # Validate file
        filename = uploaded_file.filename
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png', '.webp']:
             return dict(error="Invalid file type", results=None)
             
        # Save file
        safe_filename = f"{uuid.uuid4()}{ext}"
        file_path = os.path.join(UPLOADS_FOLDER, safe_filename)
        uploaded_file.save(file_path)
        
        # Process
        detection_result = detect_features(
            file_path,
            min_w, max_w, min_h, max_h,
            threshold
        )
        
        # Generate overlay
        original_image = cv2.imread(file_path)
        overlay_image = create_overlay_image(original_image, detection_result.bounding_boxes)
        
        overlay_filename = f"overlay_{safe_filename}"
        overlay_path = os.path.join(UPLOADS_FOLDER, overlay_filename)
        cv2.imwrite(overlay_path, overlay_image)
        
        # Serialize result for display/download
        # Convert dataclass to dict
        results_dict = {
            "bounding_boxes": [
                {"x": b.x, "y": b.y, "w": b.w, "h": b.h, "score": b.score, "validation_ratio": b.validation_ratio}
                for b in detection_result.bounding_boxes
            ],
            "delta_e_method": detection_result.delta_e_method,
            "delta_e_threshold": detection_result.delta_e_threshold,
            "processing_time_ms": detection_result.processing_time_ms
        }
        
        return dict(
            results=results_dict,
            error=None,
            image_url=URL('uploads', safe_filename),
            overlay_url=URL('uploads', overlay_filename),
            json_data=json.dumps(results_dict, indent=2),
            form_data={
                'min_w': min_w, 'max_w': max_w,
                'min_h': min_h, 'max_h': max_h,
                'threshold': threshold
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return dict(error=str(e), results=None)

# Serve uploads
@action('uploads/<filename>')
def serve_upload(filename):
    return action.stream_file(os.path.join(UPLOADS_FOLDER, filename))

