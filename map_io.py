import os
import json
import curses
from PIL import Image

def load_config():
    config_path = os.path.join(os.getcwd(), 'map_editor_config.json')
    default_bindings = {
        'move_view_up': ord('w'), 'move_view_down': ord('s'),
        'move_view_left': ord('a'), 'move_view_right': ord('d'),
        'move_cursor_up': curses.KEY_UP, 'move_cursor_down': curses.KEY_DOWN,
        'move_cursor_left': curses.KEY_LEFT, 'move_cursor_right': curses.KEY_RIGHT,
        'place_tile': ord('e'), 'cycle_tile': ord('c'), 'pick_tile': ord('t'),
        'flood_fill': ord('f'), 'line_tool': ord('i'), 'rect_tool': ord('r'),
        'circle_tool': ord('b'), 'select_start': ord('v'), 'clear_selection': ord('V'),
        'copy_selection': ord('y'),
        'paste_selection': ord('p'), 'rotate_selection': ord('m'), 'flip_h': ord('j'),
        'flip_v': ord('k'), 'undo': ord('u'), 'redo': ord('z'), 'new_map': ord('n'),
        'define_tiles': ord('T'), 'save_map': ord('g'), 'load_map': ord('l'),
        'export_image': ord('x'), 'random_gen': ord('1'), 'perlin_noise': ord('2'),
        'voronoi': ord('3'), 'replace_all': ord('h'), 'clear_area': ord('0'),
        'statistics': ord('9'), 'show_help': ord('?'), 'edit_controls': ord('o'),
        'increase_brush': ord(']'), 'decrease_brush': ord('['),
        'resize_map': ord('R'), 'set_seed': ord('S'),
        'pattern_tool': ord('P'), 'define_pattern': ord('H'),
        'define_brush': ord('B'),
        'map_rotate': ord('M'), 'map_flip_h': ord('J'), 'map_flip_v': ord('K'),
        'map_shift_up': -1, 'map_shift_down': -1,
        'map_shift_left': -1, 'map_shift_right': -1,
        'macro_record_toggle': ord('('), 'macro_play': ord(')'),
        'editor_menu': curses.KEY_F1,
        'toggle_snap': ord('G'), 'set_measure': ord('N'),
        'toggle_palette': 9,
        'toggle_autotile': ord('A'),
        'quit': ord('q'),
    }
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded = json.load(f)
                default_bindings.update(loaded)
        except: pass
    return default_bindings

def save_config(bindings):
    config_path = os.path.join(os.getcwd(), 'map_editor_config.json')
    try:
        with open(config_path, 'w') as f:
            json.dump(bindings, f, indent=2)
    except: pass

def export_to_image(map_data, tile_colors, filename, tile_size=8):
    height = len(map_data)
    width = len(map_data[0])

    img = Image.new('RGB', (width * tile_size, height * tile_size), color=(0, 0, 0))
    pixels = img.load()

    color_map = {
        curses.COLOR_BLACK: (0, 0, 0),
        curses.COLOR_RED: (255, 0, 0),
        curses.COLOR_GREEN: (0, 255, 0),
        curses.COLOR_YELLOW: (255, 255, 0),
        curses.COLOR_BLUE: (0, 0, 255),
        curses.COLOR_MAGENTA: (255, 0, 255),
        curses.COLOR_CYAN: (0, 255, 255),
        curses.COLOR_WHITE: (255, 255, 255),
    }

    for y in range(height):
        for x in range(width):
            ch = map_data[y][x]
            color = color_map.get(tile_colors.get(ch, curses.COLOR_WHITE), (255, 255, 255))
            for dy in range(tile_size):
                for dx in range(tile_size):
                    pixels[x * tile_size + dx, y * tile_size + dy] = color

    img.save(filename)
