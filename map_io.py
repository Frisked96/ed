import os
import json
import pygame
import numpy as np
from tiles import REGISTRY
from core import COLOR_MAP

def load_config():
    config_path = os.path.join(os.getcwd(), 'map_editor_config.json')
    # Default bindings now use string names for all keys
    default_bindings = {
        'move_view_up': 'w', 'move_view_down': 's',
        'move_view_left': 'a', 'move_view_right': 'd',
        'move_cursor_up': 'up', 'move_cursor_down': 'down',
        'move_cursor_left': 'left', 'move_cursor_right': 'right',
        'place_tile': ['e', 'mouse 1', 'space'], 'cycle_tile': 'c', 'pick_tile': 't',
        'flood_fill': 'f', 'line_tool': 'i', 'rect_tool': 'r',
        'circle_tool': 'b', 'select_start': 'v', 'clear_selection': 'V',
        'copy_selection': 'y',
        'paste_selection': 'p', 'rotate_selection': 'm', 'flip_h': 'j',
        'flip_v': 'k', 'undo': 'u', 'redo': 'z', 'new_map': 'n',
        'define_tiles': 'T', 'save_map': 'g', 'load_map': 'l',
        'goto_coords': ';',
        'export_image': 'x', 'random_gen': '1', 'perlin_noise': '2',
        'voronoi': '3', 'replace_all': 'h', 'clear_area': '0',
        'statistics': '9', 'show_help': ['?', '/'], 'edit_controls': 'o',
        'increase_brush': ']', 'decrease_brush': '[',
        'resize_map': 'R', 'set_seed': 'S',
        'pattern_tool': 'P', 'define_pattern': 'H',
        'define_brush': 'B',
        'map_rotate': 'M', 'map_flip_h': 'J', 'map_flip_v': 'K',
        'map_shift_up': 'None', 'map_shift_down': 'None',
        'map_shift_left': 'None', 'map_shift_right': 'None',
        'macro_record_toggle': '(', 'macro_play': ')',
        'editor_menu': 'f1',
        'toggle_snap': 'G', 'set_measure': 'N',
        'toggle_palette': 'tab',
        'toggle_autotile': 'A',
        'zoom_in': ['=', 'mouse 4'], 'zoom_out': ['-', 'mouse 5'],
        'open_context_menu': 'mouse 3',
        'toggle_measurement': 'f2',
        'measurement_menu': 'shift f2',
        'add_measure_point': 'alt mouse 1',
        'quit': 'q',
        'toggle_fullscreen': 'f11',
    }

    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                loaded = json.load(f)
                default_bindings.update(loaded)
        except Exception as e: 
            print(f"Error loading config: {e}")
            pass
    return default_bindings

def save_config(bindings):
    config_path = os.path.join(os.getcwd(), 'map_editor_config.json')
    # Save config with string keys
    try:
        with open(config_path, 'w') as f:
            json.dump(bindings, f, indent=2)
    except: pass

def load_tiles():
    tiles_path = os.path.join(os.getcwd(), 'custom_tiles.json')
    if not os.path.exists(tiles_path):
        return []
    try:
        with open(tiles_path, 'r') as f:
            return json.load(f)
    except:
        return []

def save_tiles(tile_definitions):
    tiles_path = os.path.join(os.getcwd(), 'custom_tiles.json')
    try:
        # tile_definitions should be a list of dicts from TileDefinition.dict()
        with open(tiles_path, 'w') as f:
            json.dump(tile_definitions, f, indent=2)
    except Exception as e:
        print(f"Error saving tiles: {e}")

def export_to_image(map_data, _tile_colors, filename, tile_size=8):
    from PIL import Image
    height, width = map_data.shape

    rgb_map = np.zeros((height, width, 3), dtype=np.uint8)
    
    unique_ids = np.unique(map_data)
    for tid in unique_ids:
        tile = REGISTRY.get(tid)
        color = (0, 0, 0)
        if tile:
            c = tile.color
            if isinstance(c, str):
                color = COLOR_MAP.get(c.lower(), (255, 255, 255))
            else:
                color = c
        
        rgb_map[map_data == tid] = color

    img = Image.fromarray(rgb_map, 'RGB')
    if tile_size != 1:
        img = img.resize((width * tile_size, height * tile_size), Image.NEAREST)
    
    img.save(filename)

def autosave_map(map_obj, filename):
    try:
        with open(filename, 'w') as f:
            for row in map_obj.data:
                line_chars = []
                for tid in row:
                    t = REGISTRY.get(tid)
                    line_chars.append(t.char if t else ' ')
                f.write(''.join(line_chars) + '\n')
        return True
    except:
        return False
