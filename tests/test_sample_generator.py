import unittest
import requests
import threading
from tests.utils import BASE_URL

class TestSampleGenerator(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()
        self.url = f"{BASE_URL}/sample_generator"

    def test_get_page(self):
        """Test page load."""
        response = self.session.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_generate_basic(self):
        """Test generating with default parameters."""
        response = self.session.post(self.url, data={})
        self.assertEqual(response.status_code, 200)
        # Check for image tag or success indication
        self.assertIn('<img', response.text)
        self.assertIn('uploads/sample_', response.text)

    def test_generate_custom(self):
        """Test generating with custom parameters."""
        params = {
            'img_width': 300,
            'img_height': 300,
            'num_features': 10,
            'min_size': 15,
            'max_size': 30,
            'bg_color': '#ffffff',
            'feature_color': '#0000ff',
            'shape': 'circle'
        }
        response = self.session.post(self.url, data=params)
        self.assertEqual(response.status_code, 200)
        # Check that input values are preserved in form (indicating state update)
        self.assertIn('value="300"', response.text)
        self.assertIn('uploads/sample_', response.text)

    def test_generate_invalid_params(self):
        """Test with invalid numerical parameters."""
        params = {
            'img_width': 'invalid',
            'num_features': 5
        }
        response = self.session.post(self.url, data=params)
        self.assertEqual(response.status_code, 200)
        # Should show error
        self.assertIn("invalid literal for int", response.text)

    def test_concurrent_generation(self):
        """Test concurrent generation of samples."""
        results = []
        
        def generate_sample(idx):
            session = requests.Session()
            params = {
                'img_width': 200,
                'img_height': 200,
                'num_features': 5
            }
            try:
                response = session.post(self.url, data=params)
                if response.status_code == 200 and 'uploads/sample_' in response.text:
                    results.append(idx)
            except Exception:
                pass

        threads = []
        for i in range(5):
            t = threading.Thread(target=generate_sample, args=(i,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        self.assertEqual(len(results), 5)

if __name__ == '__main__':
    unittest.main()
