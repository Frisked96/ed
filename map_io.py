import os
import json
import pygame
import numpy as np
from PIL import Image
from core import COLOR_MAP

def load_config():
    config_path = os.path.join(os.getcwd(), 'map_editor_config.json')
    # Default bindings using pygame key codes for special keys
    # For printable characters, we use ord(char) which matches ord(event.unicode)
    default_bindings = {
        'move_view_up': ord('w'), 'move_view_down': ord('s'),
        'move_view_left': ord('a'), 'move_view_right': ord('d'),
        'move_cursor_up': pygame.K_UP, 'move_cursor_down': pygame.K_DOWN,
        'move_cursor_left': pygame.K_LEFT, 'move_cursor_right': pygame.K_RIGHT,
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
        'editor_menu': pygame.K_F1,
        'toggle_snap': ord('G'), 'set_measure': ord('N'),
        'toggle_palette': pygame.K_TAB,
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
    height, width = map_data.shape

    # tile_colors maps char -> RGB tuple (from core.py)
    # We need to handle if tile_colors values are still old names (from loaded config?)
    # But tile_colors passed in comes from editor session which uses core.COLOR_MAP values (RGB)

    # Create an RGB array for the map
    rgb_map = np.zeros((height, width, 3), dtype=np.uint8)
    
    unique_chars = np.unique(map_data)
    for ch in unique_chars:
        # tile_colors[ch] should be an RGB tuple
        color = tile_colors.get(ch, (255, 255, 255))
        # Ensure it's a tuple, just in case
        if isinstance(color, str):
            color = COLOR_MAP.get(color, (255, 255, 255))

        rgb_map[map_data == ch] = color

    img = Image.fromarray(rgb_map, 'RGB')
    if tile_size != 1:
        img = img.resize((width * tile_size, height * tile_size), Image.NEAREST)
    
    img.save(filename)
