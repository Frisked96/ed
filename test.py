
import cProfile
import pstats
import io
import os
import random
import sys
import shutil
from unittest.mock import MagicMock, patch

# Mock curses before it's imported by other modules
sys.modules['curses'] = MagicMock()

from core import Map, UndoStack, ToolState, EditorSession, DEFAULT_VIEW_WIDTH, DEFAULT_VIEW_HEIGHT, DEFAULT_TILE_COLORS
from utils import parse_color_name
from map_io import load_config
from drawing import place_tile_at, flood_fill, draw_line, draw_rectangle, draw_circle, draw_pattern_rectangle
from menus import menu_new_map, menu_statistics

class MockStdscr:
    def getmaxyx(self):
        return 200, 200
    def getch(self):
        return -1
    def addstr(self, *args, **kwargs):
        pass
    def clear(self):
        pass
    def refresh(self):
        pass
    def keypad(self, *args, **kwargs):
        pass
    def nodelay(self, *args, **kwargs):
        pass
    def timeout(self, *args, **kwargs):
        pass

def mock_init_color_pairs(tile_colors):
    # Return a dummy dictionary of color pairs
    return {char: i + 1 for i, char in enumerate(tile_colors)}

@patch('ui.init_color_pairs', new=mock_init_color_pairs)
def test_application():
    stdscr = MockStdscr()
    map_obj = Map(100, 100)
    view_width, view_height = DEFAULT_VIEW_WIDTH, DEFAULT_VIEW_HEIGHT
    tile_colors = {ch: parse_color_name(col) for ch, col in DEFAULT_TILE_COLORS.items()}
    tile_chars, bindings = list(tile_colors.keys()), load_config()
    macros, tiling_rules = {}, {}
    session = EditorSession(map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
    session.color_pairs = mock_init_color_pairs(tile_colors)
    session.map_obj.undo_stack = session.undo_stack

    # Simulate some drawing operations
    for _ in range(50):
        x, y = random.randint(0, 99), random.randint(0, 99)
        char = random.choice(tile_chars)
        session.map_obj.push_undo()
        place_tile_at(session.map_obj, x, y, char, tool_state=session.tool_state)

    session.map_obj.push_undo()
    flood_fill(session.map_obj, 50, 50, 'F')
    session.map_obj.push_undo()
    draw_line(session.map_obj, 10, 10, 90, 90, 'L', tool_state=session.tool_state)
    session.map_obj.push_undo()
    draw_rectangle(session.map_obj, 20, 20, 80, 80, 'R', False, tool_state=session.tool_state)
    session.map_obj.push_undo()
    draw_rectangle(session.map_obj, 25, 25, 75, 75, 'R', True, tool_state=session.tool_state)
    session.map_obj.push_undo()
    draw_circle(session.map_obj, 50, 50, 20, 'C', False, tool_state=session.tool_state)
    session.map_obj.push_undo()
    draw_circle(session.map_obj, 50, 50, 15, 'C', True, tool_state=session.tool_state)
    
    # Simulate some more drawing operations
    session.map_obj.push_undo()
    draw_pattern_rectangle(session.map_obj, 5, 5, 15, 15, [['a', 'b'], ['c', 'd']])


    # Simulate some menu operations
    # Can't call menu_new_map directly as it tries to get user input.
    # We can call the core logic behind it though.
    new_map = Map(20, 20, fill_char='.')
    session.map_obj = new_map
    
    # Can't call menu_statistics as it's all curses based.
    # Instead, we can simulate the data gathering part if it were separate.
    # For now, we will skip it.

    # Simulate undo/redo
    for _ in range(10):
        if session.undo_stack.can_undo():
            res = session.undo_stack.undo(session.map_obj.copy_data())
            if res:
                session.map_obj.data = res

    for _ in range(5):
        if session.undo_stack.can_redo():
            res = session.undo_stack.redo(session.map_obj.copy_data())
            if res:
                session.map_obj.data = res


def main():
    profiler = cProfile.Profile()
    profiler.enable()

    test_application()

    profiler.disable()
    s = io.StringIO()
    sortby = pstats.SortKey.CUMULATIVE
    ps = pstats.Stats(profiler, stream=s).sort_stats(sortby)
    ps.print_stats(30)
    print(s.getvalue())

if __name__ == '__main__':
    main()
