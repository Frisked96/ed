import os
import json
import numpy as np
import unittest
from core import Map
from map_io import save_map_json, load_map_json, MAX_MAP_WIDTH, MAX_MAP_HEIGHT

class TestMapIORobustness(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_robustness.json"

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_json_indentation(self):
        """Ensure saved JSON is human-readable (indented)."""
        m = Map(5, 5)
        m.layers[0][:] = 1
        save_map_json(m, self.test_file)

        with open(self.test_file, 'r') as f:
            content = f.read()
            self.assertIn('\n', content, "JSON file should be multi-line (indented)")
            # Check for indent=4 (4 spaces)
            self.assertIn('    ', content, "JSON file should use 4-space indentation")

    def test_load_flattened_1d_array(self):
        """Ensure loading a 1D array reshapes it to 2D if sizes match."""
        width, height = 3, 3
        # Create a flattened layer: [1, 2, 3, 4, 5, 6, 7, 8, 9]
        data = {
            "width": width,
            "height": height,
            "layers": {
                "0": [1, 2, 3, 4, 5, 6, 7, 8, 9]
            }
        }
        with open(self.test_file, 'w') as f:
            json.dump(data, f)

        m = load_map_json(self.test_file)
        self.assertEqual(m.width, width)
        self.assertEqual(m.height, height)
        self.assertEqual(m.layers[0].shape, (height, width))
        self.assertEqual(m.layers[0][1, 1], 5) # Center element

    def test_load_shape_mismatch_crop(self):
        """Ensure loading a larger array than dimensions crops it."""
        width, height = 2, 2
        # Data for 3x3 array
        layer_data = [
            [1, 2, 3],
            [4, 5, 6],
            [7, 8, 9]
        ]
        data = {
            "width": width,
            "height": height,
            "layers": {
                "0": layer_data
            }
        }
        with open(self.test_file, 'w') as f:
            json.dump(data, f)

        m = load_map_json(self.test_file)
        # Should be 2x2
        self.assertEqual(m.width, width)
        self.assertEqual(m.height, height)
        # Should contain top-left 2x2: [[1, 2], [4, 5]]
        expected = np.array([[1, 2], [4, 5]], dtype=np.uint16)
        np.testing.assert_array_equal(m.layers[0], expected)

    def test_load_shape_mismatch_pad(self):
        """Ensure loading a smaller array pads it."""
        width, height = 3, 3
        # Data for 2x2 array
        layer_data = [
            [1, 2],
            [3, 4]
        ]
        data = {
            "width": width,
            "height": height,
            "layers": {
                "0": layer_data
            }
        }
        with open(self.test_file, 'w') as f:
            json.dump(data, f)

        m = load_map_json(self.test_file)
        self.assertEqual(m.width, width)
        self.assertEqual(m.height, height)
        # Should contain 2x2 data with padding
        expected = np.zeros((3, 3), dtype=np.uint16)
        expected[:2, :2] = [[1, 2], [3, 4]]
        np.testing.assert_array_equal(m.layers[0], expected)

    def test_max_dimensions_clamping(self):
        """Ensure map dimensions are clamped to MAX_MAP_WIDTH/HEIGHT."""
        huge_w = MAX_MAP_WIDTH + 500
        huge_h = MAX_MAP_HEIGHT + 500
        data = {
            "width": huge_w,
            "height": huge_h,
            "layers": {}
        }
        with open(self.test_file, 'w') as f:
            json.dump(data, f)

        m = load_map_json(self.test_file)
        self.assertEqual(m.width, MAX_MAP_WIDTH)
        self.assertEqual(m.height, MAX_MAP_HEIGHT)

if __name__ == '__main__':
    unittest.main()
