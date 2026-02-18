import sys
from unittest.mock import MagicMock

# Mock pygame_gui and pygame to bypass import errors and GUI dependencies
sys.modules['pygame_gui'] = MagicMock()
sys.modules['pygame_gui.ui_manager'] = MagicMock()
sys.modules['pygame_gui.elements'] = MagicMock()
sys.modules['pygame_gui.windows'] = MagicMock()
sys.modules['pygame'] = MagicMock()

import unittest
import os
from unittest.mock import patch
from core import Map

# Now import the modules under test
from menu.map_ops import menu_save_map
from flow import AppFlow

class TestAutoExtension(unittest.TestCase):
    def setUp(self):
        self.map_obj = Map(5, 5)
        self.manager = MagicMock()
        self.context = MagicMock()
        self.renderer = MagicMock()
        self.test_file_base = "test_auto_ext"

        # Ensure clean state
        if os.path.exists(self.test_file_base + ".json"):
            os.remove(self.test_file_base + ".json")

    def tearDown(self):
        if os.path.exists(self.test_file_base + ".json"):
            os.remove(self.test_file_base + ".json")

    def test_save_auto_extension(self):
        """Test that menu_save_map appends .json if missing."""
        # Patch where it is imported/used. menu.map_ops imports autosave_map inside the function
        # "from map_io import autosave_map as io_save"
        # Since it's a local import inside the function, patching map_io.autosave_map works because
        # the import happens at runtime when we call the function.
        with patch('map_io.autosave_map') as mock_save:
             menu_save_map(self.manager, self.context, self.map_obj, self.test_file_base)
             mock_save.assert_called_with(self.map_obj, self.test_file_base + ".json")

    def test_load_auto_extension(self):
        """Test that AppFlow.push_load_map_wizard resolves .json if missing."""
        with open(self.test_file_base + ".json", 'w') as f:
            f.write("{}")

        flow = AppFlow(self.manager, self.renderer)

        with patch('menu.base.TextInputState') as MockTextInputState:
            flow.push_load_map_wizard(10, 10, MagicMock())
            args, _ = MockTextInputState.call_args
            on_filename = args[3]

            # Patch 'flow.load_map_from_file' because flow.py uses 'from map_io import load_map_from_file'
            # at top level.
            with patch('flow.load_map_from_file') as mock_load:
                mock_load.return_value = Map(5,5)
                on_filename(self.test_file_base)

                mock_load.assert_called_with(self.test_file_base + ".json")

if __name__ == '__main__':
    unittest.main()
