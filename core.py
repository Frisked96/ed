import time
import random
import numpy as np
from collections import deque
from tiles import REGISTRY, TileDefinition

# RGB Color Map
COLOR_MAP = {
    'black': (0, 0, 0),
    'red': (255, 0, 0),
    'green': (0, 255, 0),
    'yellow': (255, 255, 0),
    'blue': (0, 0, 255),
    'magenta': (255, 0, 255),
    'cyan': (0, 255, 255),
    'white': (255, 255, 255),
}

class Map:
    def __init__(self, width, height, data=None, undo_stack=None, fill_tile_id=None):
        if fill_tile_id is None:
            fill_tile_id = REGISTRY.get_by_char('.') or 1
            
        self.width = width
        self.height = height
        self.undo_stack = undo_stack
        self.dirty = False
        self.listeners = []
        self.on_tile_changed_callback = None
        if data is not None:
            if isinstance(data, np.ndarray):
                self.data = data.copy()
            else:
                self.data = np.array(data, dtype=np.uint16)
        else:
            self.data = np.full((height, width), fill_tile_id, dtype=np.uint16)

    def is_inside(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.data[y, x]
        return None
    
    def get_tile_def(self, x, y):
        tid = self.get(x, y)
        if tid is not None:
            return REGISTRY.get(tid)
        return None

    def set(self, x, y, tile_id):
        if 0 <= x < self.width and 0 <= y < self.height:
            if self.data[y, x] != tile_id:
                self.data[y, x] = tile_id
                self.dirty = True
                for l in self.listeners:
                    l(x, y)
                if self.on_tile_changed_callback:
                    self.on_tile_changed_callback(x, y, tile_id)
                return True
        return False
    
    def trigger_full_update(self):
        for l in self.listeners:
            l(None, None) # Special case for full redraw

    def push_undo(self):
        if self.undo_stack:
            self.undo_stack.push(self.data.copy())

    def copy_data(self):
        return self.data.copy()

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, idx):
        return self.data[idx]

class UndoStack:
    def __init__(self, max_size=100):
        self.undo_stack = deque(maxlen=max_size)
        self.redo_stack = deque(maxlen=max_size)

    def push(self, map_data_copy):
        self.undo_stack.append(map_data_copy)
        self.redo_stack.clear()

    def undo(self, current_map_copy):
        if not self.undo_stack: return None
        self.redo_stack.append(current_map_copy)
        return self.undo_stack.pop()

    def redo(self, current_map_copy):
        if not self.redo_stack: return None
        self.undo_stack.append(current_map_copy)
        return self.redo_stack.pop()

    @property
    def undo_count(self): return len(self.undo_stack)

    @property
    def redo_count(self): return len(self.redo_stack)

class ToolState:
    def __init__(self, macros=None, tiling_rules=None):
        self.mode = 'place'
        self.start_point = None
        self.shape_fill_mode = 'ask' # 'ask', 'fill', 'outline'
        self.brush_size = 1
        self.brush_shape = None
        self.dirty = False
        self.seed = None
        self.pattern = None
        
        # Macro State
        self.recording = False
        self.macro_origin = None
        self.current_macro_tiles = [] # List of (dx, dy, tid)
        self.macros = macros if macros is not None else {}
        self.selected_macro = None
        self.macro_iterations = 1
        self.macro_until_end = False
        self.macro_offset = (1, 0) # Default offset per iteration
        
        self.snap_size = 1
        self.measure_start = None
        self.measurement_active = False
        self.measurement_config = {
            'grid_size': 100, 
            'show_coords': True, 
            'color': (0, 255, 255),
            'points': [] # List of (x, y)
        }
        self.show_palette = False
        self.auto_tiling = False
        self.tiling_rules = tiling_rules if tiling_rules is not None else {}
        self.autosave_enabled = False
        self.autosave_mode = 'time'
        self.autosave_interval = 5
        self.autosave_edits_threshold = 20
        self.edits_since_save = 0
        self.last_autosave_time = time.time()
        self.autosave_filename = "autosave_map.txt"
        if self.seed is not None:
            random.seed(self.seed)

class EditorSession:
    def __init__(self, map_obj, view_width, view_height, bindings, macros=None, tiling_rules=None):
        self.map_obj = map_obj
        self.view_width = view_width
        self.view_height = view_height
        
        # Fixed pixel dimensions for the viewport area
        self.viewport_px_w = 0 
        self.viewport_px_h = 0
        
        self.bindings = bindings
        
        self.undo_stack = UndoStack()
        self.map_obj.undo_stack = self.undo_stack 
        
        self.tool_state = ToolState(macros=macros, tiling_rules=tiling_rules)
        
        self.camera_x, self.camera_y = 0, 0
        self.cursor_x, self.cursor_y = 0, 0
        
        # Default selection
        self.selected_tile_id = 1 
        
        self.selection_start = None
        self.selection_end = None
        self.clipboard = None
        self.running = True
        self.key_map = {}
        self.action_queue = deque()
        self.status_y = 0

    def draw_long_line(self, direction, x, y):
        """Draws a line of the selected tile across the entire map."""
        self.map_obj.push_undo()
        if direction == 'horizontal':
            for lx in range(self.map_obj.width):
                self.map_obj.set(lx, y, self.selected_tile_id)
        elif direction == 'vertical':
            for ly in range(self.map_obj.height):
                self.map_obj.set(x, ly, self.selected_tile_id)

