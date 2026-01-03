import unittest
import requests
import threading
from tests.utils import BASE_URL

class TestManageData(unittest.TestCase):
    def setUp(self):
        self.session = requests.Session()
        self.url = f"{BASE_URL}/manage_data"
        self.delete_url = f"{BASE_URL}/delete_item"
        
        # Helper to create an item
        self.sample_url = f"{BASE_URL}/sample_generator"

    def create_sample_item(self):
        # 1. Create the item
        p_resp = self.session.post(self.sample_url, data={'num_features': 1})
        if p_resp.status_code != 200:
            print(f"Failed to create item: {p_resp.status_code}")
            return None
            
        # 2. Get manage_data page to find the ID
        resp = self.session.get(self.url)
        if resp.status_code == 200:
            import re
            matches = re.findall(r'<input type="hidden" name="item_id" value="([^"]+)">', resp.text)
            if matches:
                return matches[0]
            else:
                # Debugging: check if history is empty
                if "No generated samples found" in resp.text:
                    print("Debug: No samples found in manage_data")
                else:
                    print("Debug: Matches not found but history seems present?")
                    # print(resp.text[:500])
        return None

    def test_get_page(self):
        """Test page load."""
        response = self.session.get(self.url)
        self.assertEqual(response.status_code, 200)

    def test_delete_sample_item(self):
        """Test deleting a sample item."""
        # 1. Create item
        item_id = self.create_sample_item()
        self.assertIsNotNone(item_id)
        
        # 2. Verify it's in list (by checking manage page)
        resp = self.session.get(self.url)
        self.assertIn(item_id, resp.text)
        
        # 3. Delete it
        payload = {'item_id': item_id, 'item_type': 'sample'}
        resp = self.session.post(self.delete_url, data=payload, allow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        
        # 4. Verify it's gone
        resp = self.session.get(self.url)
        self.assertNotIn(item_id, resp.text)

    def test_delete_missing_params(self):
        """Test delete with missing parameters."""
        resp = self.session.post(self.delete_url, data={}, allow_redirects=True)
        # Should redirect back to manage_data and not crash
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.url.endswith("manage_data"))

    def test_delete_non_existent_item(self):
        """Test deleting an ID that doesn't exist."""
        payload = {'item_id': 'fake-uuid', 'item_type': 'sample'}
        resp = self.session.post(self.delete_url, data=payload, allow_redirects=True)
        self.assertEqual(resp.status_code, 200)
        # Should just do nothing and redirect
        self.assertTrue(resp.url.endswith("manage_data"))

    def test_concurrent_deletes(self):
        """Test concurrent deletion of the same item."""
        item_id = self.create_sample_item()
        self.assertIsNotNone(item_id)
        
        results = []
        def delete_item():
            session = requests.Session()
            payload = {'item_id': item_id, 'item_type': 'sample'}
            try:
                # We don't check for 200 strictly as the goal is to ensure server doesn't crash
                resp = session.post(self.delete_url, data=payload, allow_redirects=True)
                if resp.status_code == 200:
                    results.append(True)
            except Exception:
                pass

        threads = []
        for i in range(5):
            t = threading.Thread(target=delete_item)
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # At least one should have succeeded (conceptually), but all might return 200 because 
        # deleting a non-existent item might just redirect (as seen in test_delete_non_existent_item).
        # The main check is that the server didn't crash.
        self.assertTrue(len(results) > 0)
        
        # Verify it is gone
        resp = self.session.get(self.url)
        self.assertNotIn(item_id, resp.text)

if __name__ == '__main__':
    unittest.main()

