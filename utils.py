import time
import pygame
import sys
import json
import os
import math
from colors import Colors

def get_all_colors():
    return Colors.all()

def parse_color_name(name):
    # Returns an RGB tuple
    if not isinstance(name, str):
        return name
    
    # Handle RGB string format "255,0,0"
    if "," in name:
        try:
            return tuple(map(int, name.split(',')))
        except: pass

    return Colors.get(name.lower(), Colors.WHITE)

def get_color_name(rgb):
    if isinstance(rgb, str):
        return rgb
    
    try:
        colors = Colors.all()
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

    if isinstance(key, list):
        return "/".join(get_key_name(k) for k in key)

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

def test_unicode_support(font):
    """Checks if the given font can render box drawing and shade characters properly."""
    if not font: return False
    test_chars = ["│", "─", "┌", "░"]
    try:
        # Most fonts that don't support these will render them as the same width
        # as a missing glyph rectangle or space.
        # We can compare with a definitely missing character.
        # But a simpler test is just checking if they have non-zero width and differ from a space.
        space_width = font.size(" ")[0]
        for char in test_chars:
            w, h = font.size(char)
            if w <= 1: return False
            # If it's the exact same width as a space, it MIGHT be a placeholder (not always, but suspicious for boxes)
            # Better check: render it and see if it's all empty? No, that's expensive.
        return True
    except:
        return False
