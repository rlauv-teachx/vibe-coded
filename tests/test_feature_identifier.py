import unittest
import requests
import os
import threading
import time
from tests.utils import BASE_URL, create_test_image, remove_test_image, create_dummy_text_file, clean_upload_buffer
import numpy as np
import cv2

class TestFeatureIdentifier(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()
        self.test_image = "test_feature_id.png"
        self.dummy_file = "test_dummy.txt"
        create_test_image(self.test_image)
        create_dummy_text_file(self.dummy_file)
        clean_upload_buffer()
        
        # Files for race condition
        self.large_image_path = "large_test_image.png"
        self.small_image_path = "small_test_image.png"
        
        # Create a large image (e.g. 2000x2000) with around 8 features
        large_img = np.zeros((2000, 2000, 3), dtype=np.uint8)
        # Add fewer, larger, more distant rectangles
        for i in range(8):
            # Start at 200, step by 200. Size 100x100.
            start_x = 200 + i * 200
            start_y = 200 + i * 200
            cv2.rectangle(large_img, (start_x, start_y), (start_x + 100, start_y + 100), (0, 255, 0), -1)
        cv2.imwrite(self.large_image_path, large_img)
        
        # Create a small image (e.g. 100x100) with 1 feature
        small_img = np.zeros((100, 100, 3), dtype=np.uint8)
        cv2.rectangle(small_img, (10, 10), (50, 50), (0, 0, 255), -1)
        cv2.imwrite(self.small_image_path, small_img)

    def tearDown(self):
        remove_test_image(self.test_image)
        remove_test_image(self.dummy_file)
        remove_test_image(self.large_image_path)
        remove_test_image(self.small_image_path)
        clean_upload_buffer()

    def test_get_page(self):
        """Test loading the feature identifier page."""
        url = f"{BASE_URL}/feature_identifier"
        response = self.session.get(url)
        self.assertEqual(response.status_code, 200)

    def test_upload_process_valid(self):
        """Test uploading a valid image for processing."""
        url = f"{BASE_URL}/feature_identifier"
        files = {'image': open(self.test_image, 'rb')}
        data = {
            'min_w': 10, 'max_w': 500,
            'min_h': 10, 'max_h': 500,
            'threshold': 2.3,
            'edge_detection_method': 'canny'
        }
        # Expect HTML response
        response = self.session.post(url, files=files, data=data)
        self.assertEqual(response.status_code, 200)
        
        # Check if results are in the HTML
        # The controller passes json_data=json.dumps(results_dict)
        self.assertIn('bounding_boxes', response.text)
        self.assertIn('processing_time_ms', response.text)

    def test_invalid_file_type(self):
        """Test uploading an invalid file type."""
        url = f"{BASE_URL}/feature_identifier"
        files = {'image': open(self.dummy_file, 'rb')} # Text file
        response = self.session.post(url, files=files)
        
        self.assertEqual(response.status_code, 200)
        # Check for error message in HTML
        self.assertIn("Invalid file type", response.text)

    def test_use_sample_param(self):
        """Test using a sample image via GET parameter."""
        # Generate sample first
        gen_url = f"{BASE_URL}/sample_generator"
        self.session.post(gen_url, data={'num_features': 1})
        # We need to find the filename. It's in the response HTML or we can guess/check uploads
        # But simpler: just check that the page loads with ?sample=... without error
        # A bit hard to get exact filename without parsing. 
        # Let's just test that the endpoint accepts the param.
        
        url = f"{BASE_URL}/feature_identifier"
        # We'll use a dummy filename that doesn't exist to check error handling/validation
        # or use a known one if we could.
        response = self.session.get(url, params={'sample': 'non_existent.png'})
        self.assertEqual(response.status_code, 200)
        # Should show error or handle it
        self.assertIn("Error selecting sample", response.text)

    def test_no_file_selected(self):
        """Test submitting without selecting a file."""
        new_session = requests.Session()
        url = f"{BASE_URL}/feature_identifier"
        response = new_session.post(url, data={})
        
        self.assertEqual(response.status_code, 200)
        self.assertIn("No file selected", response.text)

    def upload_and_process(self, image_path, expected_min_features):
        """
        Uploads an image and checks the result.
        """
        url = f"{BASE_URL}/feature_identifier"
        files = {'image': open(image_path, 'rb')}
        data = {
            'min_w': 10, 'max_w': 5000,
            'min_h': 10, 'max_h': 5000,
            'threshold': 2.3,
            'edge_detection_method': 'canny'
        }
        
        try:
            # Create a new session for each upload to simulate different users
            session = requests.Session()
            response = session.post(url, files=files, data=data)
            if response.status_code == 200:
                result = response.json()
                if result.get('results'):
                    num_features = len(result['results']['bounding_boxes'])
                    return num_features
                else:
                    return -1
            else:
                return -1
        except Exception as e:
            return -1

    def test_race_condition_overwrite(self):
        """
        Demonstrate race condition where a small upload overwrites a large upload
        being processed, causing the large upload to return incorrect results.
        """
        results = {}
        
        def run_large_test():
            # Large test expects many features (approx 8)
            results['large'] = self.upload_and_process(self.large_image_path, 8)
            
        def run_small_test():
            # Delay slightly to ensure large test has started upload/processing
            time.sleep(0.1) 
            # Small test expects 1 feature
            results['small'] = self.upload_and_process(self.small_image_path, 1)

        # Start threads
        t1 = threading.Thread(target=run_large_test)
        t2 = threading.Thread(target=run_small_test)
        
        t1.start()
        t2.start()
        
        t1.join()
        t2.join()
        
        # Assertion: Large test should have found ~8 features. 
        # If race condition hit, it might have found 1 (from small image) or failed.
        self.assertGreater(results.get('large', 0), 5, 
            f"Race Condition Detected! Large test returned {results.get('large')} features instead of ~8. "
            "It likely processed the small image uploaded by Thread 2.")

if __name__ == '__main__':
    unittest.main()
