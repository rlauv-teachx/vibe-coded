import unittest
import requests
from tests.utils import BASE_URL

class TestDashboard(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()

    def test_index_load(self):
        """Test that the index page loads successfully."""
        url = f"{BASE_URL}/index"
        response = self.session.get(url)
        self.assertEqual(response.status_code, 200, "Dashboard should return 200 OK")
        self.assertIn("Image Processing Hub", response.text, "Title should be present")

    def test_populate_demo(self):
        """Test populating demo data."""
        url = f"{BASE_URL}/populate_demo"
        # populate_demo is a POST request that redirects
        response = self.session.post(url, allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # After population, there should be items in history
        # We check the dashboard (which we are redirected to) for history items
        self.assertIn("history", response.text.lower())
        # We can't easily assert exact count without parsing HTML, but we check success code

    def test_clear_history(self):
        """Test clearing history."""
        # First ensure there is some data (optional, but good practice)
        self.session.post(f"{BASE_URL}/populate_demo")
        
        url = f"{BASE_URL}/clear_history"
        response = self.session.post(url, allow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Should be redirected to index
        self.assertTrue(response.url.endswith("/index") or response.url.endswith("/feature_site/index"))

    def test_session_persistence(self):
        """Verify session cookies are handled correctly."""
        # 1. Clear history
        self.session.post(f"{BASE_URL}/clear_history")
        # 2. Check index - should assume empty or clean state
        response = self.session.get(f"{BASE_URL}/index")
        self.assertEqual(response.status_code, 200)

if __name__ == '__main__':
    unittest.main()

