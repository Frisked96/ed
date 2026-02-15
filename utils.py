import time
import pygame
import sys
import json
import os
from core import COLOR_MAP

def get_all_colors():
    combined = dict(COLOR_MAP)
    colors_path = os.path.join(os.getcwd(), 'colors.json')
    if os.path.exists(colors_path):
        try:
            with open(colors_path, 'r') as f:
                loaded = json.load(f)
                combined.update(loaded)
        except: pass
    return combined

def parse_color_name(name):
    # Returns an RGB tuple
    if not isinstance(name, str):
        return name
    
    # Handle RGB string format "255,0,0"
    if "," in name:
        try:
            return tuple(map(int, name.split(',')))
        except: pass

    colors = get_all_colors()
    return tuple(colors.get(name.lower(), (255, 255, 255)))

def get_color_name(rgb):
    if isinstance(rgb, str):
        return rgb
    
    try:
        colors = get_all_colors()
        # Convert to list for comparison
        target = list(rgb)
        for name, val in colors.items():
            if list(val) == target:
                return name
    except: pass
    
    if isinstance(rgb, (list, tuple)) and len(rgb) >= 3:
        return f"{rgb[0]},{rgb[1]},{rgb[2]}"
    return str(rgb)

def get_key_name(key):
    # Handles both new string names and legacy integer codes
    if key is None:
        return "NONE"

    if isinstance(key, str):
        return key.upper()

    if key == 32: return 'SPACE'
    elif key == 27: return 'ESC'
    elif key == 8: return 'BKSP'
    elif key == 13: return 'ENTER'
    elif key == 9: return 'TAB'

    # Check ASCII printable characters first for case-sensitivity
    if 33 <= key <= 126:
        return chr(key)

    # Fallback to pygame for other keys (arrows, F-keys, etc.)
    try:
        name = pygame.key.name(key)
        if name and name != 'unknown key':
            return name.upper()
    except: pass

    return f'KEY_{key}'

def get_distance(p1, p2):
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

def rotate_selection_90(selection_data):
    if not selection_data: return None
    height = len(selection_data)
    width = len(selection_data[0])
    rotated = [['' for _ in range(height)] for _ in range(width)]
    for y in range(height):
        for x in range(width):
            rotated[x][height - 1 - y] = selection_data[y][x]
    return rotated

def flip_selection_horizontal(selection_data):
    if not selection_data: return None
    return [row[::-1] for row in selection_data]

def flip_selection_vertical(selection_data):
    if not selection_data: return None
    return selection_data[::-1]

def shift_map(map_data, dx, dy):
    height = len(map_data)
    width = len(map_data[0])
    new_map = [['' for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            new_map[(y + dy) % height][(x + dx) % width] = map_data[y][x]
    return new_map
