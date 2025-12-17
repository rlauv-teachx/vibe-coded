import unittest
import numpy as np
import sys
import os

# Add apps to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from apps.feature_site.modules.feature_identifier.color import calculate_delta_e_cie76, bgr_to_lab
from apps.feature_site.modules.feature_identifier.geometry import check_overlap_mask, mark_occupied, get_outline_coordinates

class TestFeatureIdentifier(unittest.TestCase):
    
    def test_delta_e(self):
        # Test exact match
        c1 = np.array([50.0, 0.0, 0.0])
        c2 = np.array([50.0, 0.0, 0.0])
        self.assertAlmostEqual(calculate_delta_e_cie76(c1, c2), 0.0)
        
        # Test known distance
        # dist((50,0,0), (60,0,0)) = 10
        c3 = np.array([60.0, 0.0, 0.0])
        self.assertAlmostEqual(calculate_delta_e_cie76(c1, c3), 10.0)
        
    def test_overlap_logic(self):
        h, w = 100, 100
        mask = np.zeros((h, w), dtype=np.uint8)
        
        # Box 1: 10,10 20x20
        # Check before mark
        self.assertFalse(check_overlap_mask(mask, 10, 10, 20, 20))
        
        # Mark
        mark_occupied(mask, 10, 10, 20, 20)
        
        # Check same box
        self.assertTrue(check_overlap_mask(mask, 10, 10, 20, 20))
        
        # Check overlapping box (15, 15, 20, 20)
        self.assertTrue(check_overlap_mask(mask, 15, 15, 20, 20))
        
        # Check non-overlapping box (50, 50, 10, 10)
        self.assertFalse(check_overlap_mask(mask, 50, 50, 10, 10))
        
    def test_perimeter_coordinates(self):
        # 3x3 box
        # Top: (0,0), (1,0), (2,0)
        # Right: (2,1), (2,2)
        # Bottom: (1,2), (0,2)
        # Left: (0,1)
        # Total 8 pixels
        coords = get_outline_coordinates(0, 0, 3, 3)
        self.assertEqual(len(coords), 8)
        self.assertIn((0,0), coords)
        self.assertIn((2,2), coords)
        self.assertNotIn((1,1), coords) # Interior pixel

if __name__ == '__main__':
    unittest.main()

