import unittest
import requests
import os
from tests.utils import BASE_URL, create_test_image, remove_test_image

class TestImageFilter(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()
        self.url = f"{BASE_URL}/image_filter"
        self.test_image = "test_filter_img.png"
        create_test_image(self.test_image)

    def tearDown(self):
        remove_test_image(self.test_image)

    def test_get_page(self):
        """Test page load."""
        response = self.session.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_upload_image(self):
        """Test uploading an image to the filter tool."""
        with open(self.test_image, 'rb') as f:
            files = {'image': f}
            data = {'action': 'upload'}
            response = self.session.post(self.url, files=files, data=data)
            
            self.assertEqual(response.status_code, 200)
            # Check if image is displayed (searching for current_image_url usage or img tag)
            self.assertIn('uploads/', response.text)

    def test_apply_filter(self):
        """Test applying a filter."""
        # 1. Upload first
        with open(self.test_image, 'rb') as f:
            self.session.post(self.url, files={'image': f}, data={'action': 'upload'})
        
        # 2. Apply Blur
        data = {'action': 'filter', 'filter_type': 'blur', 'intensity': 10}
        response = self.session.post(self.url, data=data)
        self.assertEqual(response.status_code, 200)
        
        # Check that the filter type is selected in the UI
        self.assertIn('value="blur" selected', response.text)

    def test_reset_filter(self):
        """Test resetting the image."""
        # 1. Upload
        with open(self.test_image, 'rb') as f:
            self.session.post(self.url, files={'image': f}, data={'action': 'upload'})
        
        # 2. Reset
        data = {'action': 'reset'}
        response = self.session.post(self.url, data=data)
        self.assertEqual(response.status_code, 200)

    def test_detect_from_filter(self):
        """Test running detection from the filter page."""
        # 1. Upload
        with open(self.test_image, 'rb') as f:
            self.session.post(self.url, files={'image': f}, data={'action': 'upload'})
            
        # 2. Detect
        data = {'action': 'detect', 'method': 'canny'}
        response = self.session.post(self.url, data=data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("detected_", response.text)

if __name__ == '__main__':
    unittest.main()
