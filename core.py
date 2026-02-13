import curses
import time
import random
from collections import deque

DEFAULT_VIEW_WIDTH = 60
DEFAULT_VIEW_HEIGHT = 30
DEFAULT_MAP_WIDTH = 60
DEFAULT_MAP_HEIGHT = 30
DEFAULT_TILE_COLORS = {
    '.': 'white', '#': 'red', '~': 'cyan', 'T': 'green',
    'G': 'yellow', '+': 'yellow', '*': 'magenta', '@': 'blue',
}

COLOR_MAP = {
    'black': curses.COLOR_BLACK, 'red': curses.COLOR_RED,
    'green': curses.COLOR_GREEN, 'yellow': curses.COLOR_YELLOW,
    'blue': curses.COLOR_BLUE, 'magenta': curses.COLOR_MAGENTA,
    'cyan': curses.COLOR_CYAN, 'white': curses.COLOR_WHITE,
}

class Map:
    def __init__(self, width, height, data=None, undo_stack=None, fill_char='.'):
        self.width = width
        self.height = height
        self.undo_stack = undo_stack
        self.dirty = False
        if data:
            self.data = data
        else:
            self.data = [[fill_char for _ in range(width)] for _ in range(height)]

    def is_inside(self, x, y):
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x, y):
        if self.is_inside(x, y):
            return self.data[y][x]
        return None

    def set(self, x, y, char):
        if self.is_inside(x, y):
            if self.data[y][x] != char:
                self.data[y][x] = char
                self.dirty = True
                return True
        return False

    def push_undo(self):
        if self.undo_stack:
            self.undo_stack.push(self.copy_data())

    def copy_data(self):
        return [row[:] for row in self.data]

    def __iter__(self):
        return iter(self.data)

    def __getitem__(self, idx):
        return self.data[idx]

class UndoStack:
    def __init__(self, max_size=100):
        self.undo_stack = deque(maxlen=max_size)
        self.redo_stack = deque(maxlen=max_size)

    def push(self, map_data):
        self.undo_stack.append([row[:] for row in map_data])
        self.redo_stack.clear()

    def undo(self, current_map):
        if not self.undo_stack: return None
        self.redo_stack.append([row[:] for row in current_map])
        return self.undo_stack.pop()

    def redo(self, current_map):
        if not self.redo_stack: return None
        self.undo_stack.append([row[:] for row in current_map])
        return self.redo_stack.pop()

    def can_undo(self): return len(self.undo_stack) > 0
    def can_redo(self): return len(self.redo_stack) > 0

class ToolState:
    def __init__(self, macros=None, tiling_rules=None):
        self.mode = 'place'
        self.start_point = None
        self.brush_size = 1
        self.brush_shape = None
        self.dirty = False
        self.seed = 0
        self.pattern = None
        self.recording = False
        self.current_macro_actions = []
        self.macros = macros if macros is not None else {}
        self.snap_size = 1
        self.measure_start = None
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
        random.seed(self.seed)

class EditorSession:
    def __init__(self, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros=None, tiling_rules=None):
        self.map_obj = map_obj
        self.view_width = view_width
        self.view_height = view_height
        self.tile_chars = tile_chars
        self.tile_colors = tile_colors
        self.bindings = bindings
        
        self.tool_state = ToolState(macros=macros, tiling_rules=tiling_rules)
        self.undo_stack = UndoStack()
        
        self.camera_x, self.camera_y = 0, 0
        self.cursor_x, self.cursor_y = 0, 0
        self.selected_idx = 0
        self.selected_char = tile_chars[0] if tile_chars else '.'
        self.color_pairs = {}
        
        self.selection_start = None
        self.selection_end = None
        self.clipboard = None
        self.running = True
