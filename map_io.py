import os
import json
import pygame
import numpy as np
from tiles import REGISTRY
from colors import Colors

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
        'layer_up': 'page up', 'layer_down': 'page down',
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
    custom_tiles = []

    # Animated tiles (Base defaults)
    anim_path = os.path.join(os.getcwd(), 'tiles', 'animated_tiles.json')
    if os.path.exists(anim_path):
        try:
            with open(anim_path, 'r') as f:
                anim_tiles = json.load(f)
                custom_tiles.extend(anim_tiles)
        except:
            pass

    # Primary custom tiles (User overrides)
    tiles_path = os.path.join(os.getcwd(), 'tiles', 'custom_tiles.json')
    if os.path.exists(tiles_path):
        try:
            with open(tiles_path, 'r') as f:
                user_tiles = json.load(f)
                custom_tiles.extend(user_tiles)
        except:
            pass

    return custom_tiles

def save_tiles(tile_definitions):
    # Ensure directory exists
    tiles_dir = os.path.join(os.getcwd(), 'tiles')
    os.makedirs(tiles_dir, exist_ok=True)

    tiles_path = os.path.join(tiles_dir, 'custom_tiles.json')

    # Filter out animated tiles that belong to animated_tiles.json if we want separation?
    # For simplicity, we save all user-defined/edited tiles to custom_tiles.json for now,
    # or we can try to respect the source.
    # Given the prompt, let's just save everything to custom_tiles.json for persistence
    # unless we want to split them. The prompt asked for a separate dir, which we made.
    # We will save all 'persist=True' tiles here.

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
        color = Colors.BLACK
        if tile:
            c = tile.color
            if isinstance(c, str):
                color = Colors.get(c.lower(), Colors.WHITE)
            else:
                color = c
        
        rgb_map[map_data == tid] = color

    img = Image.fromarray(rgb_map, 'RGB')
    if tile_size != 1:
        img = img.resize((width * tile_size, height * tile_size), Image.NEAREST)
    
    img.save(filename)

def autosave_map(map_obj, filename):
    try:
        if filename.endswith('.json'):
            save_map_json(map_obj, filename)
        else:
            save_map_text_layers(map_obj, filename)
        return True
    except Exception as e:
        print(f"Autosave failed: {e}")
        return False

def save_map_json(map_obj, filename):
    data = {
        "width": map_obj.width,
        "height": map_obj.height,
        "layers": {}
    }
    for z, layer in map_obj.layers.items():
        data["layers"][str(z)] = layer.tolist()

    with open(filename, 'w') as f:
        json.dump(data, f)

def save_map_text_layers(map_obj, filename):
    with open(filename, 'w') as f:
        sorted_z = sorted(map_obj.layers.keys())
        # If only layer 0 and no others, use legacy format (no header)
        if len(sorted_z) == 1 and sorted_z[0] == 0:
            for row in map_obj.layers[0]:
                line_chars = []
                for tid in row:
                    t = REGISTRY.get(tid)
                    line_chars.append(t.char if t else ' ')
                f.write(''.join(line_chars) + '\n')
        else:
            for z in sorted_z:
                f.write(f"[Layer {z}]\n")
                layer = map_obj.layers[z]
                for row in layer:
                    line_chars = []
                    for tid in row:
                        t = REGISTRY.get(tid)
                        line_chars.append(t.char if t else ' ')
                    f.write(''.join(line_chars) + '\n')

def load_map_from_file(filename):
    if filename.endswith('.json'):
        return load_map_json(filename)
    return load_map_text(filename)

def load_map_json(filename):
    with open(filename, 'r') as f:
        data = json.load(f)

    w = data.get('width', 10)
    h = data.get('height', 10)
    from core import Map
    m = Map(w, h)

    layers = data.get('layers', {})
    for z_str, layer_data in layers.items():
        z = int(z_str)
        m.layers[z] = np.array(layer_data, dtype=np.uint16)
    return m

def load_map_text(filename):
    with open(filename, 'r') as f:
        lines = [line.rstrip('\n') for line in f]

    import re
    layer_header_re = re.compile(r"^\[Layer (\d+)\]$")

    from core import Map

    # Detect multi-layer
    if lines and layer_header_re.match(lines[0]):
        layers_data = {}
        current_z = 0
        current_lines = []

        for line in lines:
            m = layer_header_re.match(line)
            if m:
                if current_lines:
                    layers_data[current_z] = current_lines
                current_z = int(m.group(1))
                current_lines = []
            else:
                current_lines.append(line)
        if current_lines:
            layers_data[current_z] = current_lines

        max_w = 0
        max_h = 0
        for z, l_lines in layers_data.items():
            max_h = max(max_h, len(l_lines))
            for l in l_lines:
                max_w = max(max_w, len(l))

        map_obj = Map(max_w, max_h)
        for z, l_lines in layers_data.items():
            map_obj.ensure_layer(z)
            for y, line in enumerate(l_lines):
                for x, char in enumerate(line):
                    tid = REGISTRY.get_by_char(char)
                    if tid:
                        map_obj.layers[z][y, x] = tid
        return map_obj
    else:
        # Legacy single layer
        w = max(len(l) for l in lines) if lines else 0
        h = len(lines)
        m = Map(w, h)
        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                m.set(x, y, REGISTRY.get_by_char(char))
        return m

def save_macros(macros):
    path = os.path.join(os.getcwd(), 'macros.json')
    try:
        with open(path, 'w') as f:
            json.dump(macros, f, indent=2)
    except: pass

def load_macros():
    path = os.path.join(os.getcwd(), 'macros.json')
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except:
        return {}
