import curses
import sys
import os
import json
import time
import random
import argparse
from collections import deque
import shutil
import textwrap
import numpy as np
from PIL import Image

# --- CONSTANTS ---
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

# --- END CONSTANTS ---

def parse_color_name(name):
    return COLOR_MAP.get(name.lower(), curses.COLOR_WHITE)

def init_color_pairs(tile_colors):
    curses.start_color()
    curses.use_default_colors()
    pairs = {}
    pair_num = 1
    for ch, col in tile_colors.items():
        curses.init_pair(pair_num, col, -1)
        pairs[ch] = pair_num
        pair_num += 1
    curses.init_pair(pair_num, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    pairs['__SELECTION__'] = pair_num
    return pairs

def get_key_name(key):
    if key == ord(' '): return 'SPACE'
    elif key == 27: return 'ESC'
    elif key == 127 or key == curses.KEY_BACKSPACE: return 'BKSP'
    else:
        try:
            name = curses.keyname(key)
            if name:
                decoded = name.decode('utf-8', 'ignore').upper()
                if decoded.startswith('KEY_'):
                    decoded = decoded[4:]
                return decoded
        except: pass
        if 32 <= key <= 126: return chr(key).upper()
        return f'KEY_{key}'

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
        'define_tiles': ord('d'), 'save_map': ord('g'), 'load_map': ord('l'),
        'export_image': ord('x'), 'random_gen': ord('1'), 'perlin_noise': ord('2'),
        'voronoi': ord('3'), 'replace_all': ord('h'), 'clear_area': ord('0'),
        'statistics': ord('9'), 'show_help': ord('?'), 'edit_controls': ord('o'),
        'increase_brush': ord(']'), 'decrease_brush': ord('['),
        'resize_map': ord('R'), 'set_seed': ord('S'),
        'pattern_tool': ord('P'), 'define_pattern': ord('T'),
        'define_brush': ord('B'),
        'map_rotate': ord('M'), 'map_flip_h': ord('J'), 'map_flip_v': ord('K'),
        'map_shift_up': 259, 'map_shift_down': 258,
        'map_shift_left': 260, 'map_shift_right': 261,
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

def build_key_map(bindings):
    key_map = {}
    for action, key in bindings.items():
        if key not in key_map:
            key_map[key] = []
        key_map[key].append(action)
    return key_map

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

def place_tile_at(map_data, x, y, char, width, height, brush_size=1, brush_shape=None, tool_state=None):
    def final_char(cx, cy, base):
        if tool_state and tool_state.auto_tiling:
            return apply_autotiling(map_data, cx, cy, base, tool_state.tiling_rules, width, height)
        return base

    if brush_shape:
        h = len(brush_shape)
        w = len(brush_shape[0])
        off_y = h // 2
        off_x = w // 2
        for dy in range(h):
            for dx in range(w):
                if brush_shape[dy][dx]:
                    nx, ny = x + dx - off_x, y + dy - off_y
                    if 0 <= nx < width and 0 <= ny < height:
                        map_data[ny][nx] = final_char(nx, ny, char)
    elif brush_size <= 1:
        if 0 <= x < width and 0 <= y < height:
            map_data[y][x] = final_char(x, y, char)
    else:
        offset = brush_size // 2
        for by in range(y - offset, y + offset + 1):
            for bx in range(x - offset, x + offset + 1):
                if 0 <= by < height and 0 <= bx < width:
                    map_data[by][bx] = final_char(bx, by, char)

def flood_fill(map_data, x, y, old_char, new_char, width, height):
    if old_char == new_char: return
    if x < 0 or x >= width or y < 0 or y >= height: return
    if map_data[y][x] != old_char: return

    queue = deque([(x, y)])
    visited = set([(x, y)])

    while queue:
        cx, cy = queue.popleft()
        map_data[cy][cx] = new_char

        for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
            if 0 <= nx < width and 0 <= ny < height:
                if (nx, ny) not in visited and map_data[ny][nx] == old_char:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

def draw_line(map_data, x0, y0, x1, y1, char, width, height, brush_size=1, brush_shape=None, tool_state=None):
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    x, y = x0, y0
    while True:
        place_tile_at(map_data, x, y, char, width, height, brush_size, brush_shape, tool_state)
        if x == x1 and y == y1: break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy

def draw_rectangle(map_data, x0, y0, x1, y1, char, filled, width, height, brush_size=1, brush_shape=None, tool_state=None):
    min_x = max(0, min(x0, x1))
    max_x = min(width - 1, max(x0, x1))
    min_y = max(0, min(y0, y1))
    max_y = min(height - 1, max(y0, y1))

    if filled:
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                map_data[y][x] = char
    else:
        for x in range(min_x, max_x + 1):
            place_tile_at(map_data, x, min_y, char, width, height, brush_size, brush_shape, tool_state)
            place_tile_at(map_data, x, max_y, char, width, height, brush_size, brush_shape, tool_state)
        for y in range(min_y, max_y + 1):
            place_tile_at(map_data, min_x, y, char, width, height, brush_size, brush_shape, tool_state)
            place_tile_at(map_data, max_x, y, char, width, height, brush_size, brush_shape, tool_state)

def draw_circle(map_data, cx, cy, radius, char, filled, width, height, brush_size=1, brush_shape=None, tool_state=None):
    if filled:
        for y in range(max(0, cy - radius), min(height, cy + radius + 1)):
            for x in range(max(0, cx - radius), min(width, cx + radius + 1)):
                if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 <= radius:
                    map_data[y][x] = char
    else:
        x = radius
        y = 0
        err = 0

        while x >= y:
            points = [
                (cx + x, cy + y), (cx + y, cy + x),
                (cx - y, cy + x), (cx - x, cy + y),
                (cx - x, cy - y), (cx - y, cy - x),
                (cx + y, cy - x), (cx + x, cy - y)
            ]
            for px, py in points:
                place_tile_at(map_data, px, py, char, width, height, brush_size, brush_shape, tool_state)

            y += 1
            if err <= 0:
                err += 2*y + 1
            else:
                x -= 1
                err += 2*(y - x) + 1

def cellular_automata_cave(map_data, width, height, iterations=5, wall_char='#', floor_char='.', seed=None):
    if seed is not None:
        random.seed(seed)
    for y in range(height):
        for x in range(width):
            if x == 0 or x == width-1 or y == 0 or y == height-1:
                map_data[y][x] = wall_char
            else:
                map_data[y][x] = wall_char if random.random() < 0.45 else floor_char

    for _ in range(iterations):
        new_map = [row[:] for row in map_data]
        for y in range(1, height-1):
            for x in range(1, width-1):
                wall_count = sum(
                    1 for dy in [-1, 0, 1] for dx in [-1, 0, 1]
                    if (dx != 0 or dy != 0) and map_data[y+dy][x+dx] == wall_char
                )
                if wall_count >= 5:
                    new_map[y][x] = wall_char
                else:
                    new_map[y][x] = floor_char
        map_data[:] = new_map

def perlin_noise_generation(map_data, tile_chars, width, height, scale=10.0, octaves=4, persistence=0.5, seed=0):
    from noise import pnoise2

    noise_map = np.zeros((height, width))
    for y in range(height):
        for x in range(width):
            noise_map[y][x] = pnoise2(x / scale, y / scale, octaves=octaves, persistence=persistence, lacunarity=2.0, base=seed)

    min_val = noise_map.min()
    max_val = noise_map.max()
    noise_map = (noise_map - min_val) / (max_val - min_val)

    for y in range(height):
        for x in range(width):
            idx = int(noise_map[y][x] * len(tile_chars))
            idx = min(idx, len(tile_chars) - 1)
            map_data[y][x] = tile_chars[idx]

def voronoi_generation(map_data, tile_chars, width, height, num_points=20, seed=None):
    if seed is not None:
        random.seed(seed)
    points = [(random.randint(0, width-1), random.randint(0, height-1)) for _ in range(num_points)]
    point_chars = [random.choice(tile_chars) for _ in range(num_points)]

    for y in range(height):
        for x in range(width):
            min_dist = float('inf')
            closest_idx = 0
            for i, (px, py) in enumerate(points):
                dist = ((x - px) ** 2 + (y - py) ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    closest_idx = i
            map_data[y][x] = point_chars[closest_idx]

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

def get_map_statistics(map_data, width, height):
    tile_counts = {}
    for y in range(height):
        for x in range(width):
            ch = map_data[y][x]
            tile_counts[ch] = tile_counts.get(ch, 0) + 1
    return tile_counts

def draw_map(stdscr, map_data, camera_x, camera_y, view_width, view_height,
             cursor_x, cursor_y, selected_char, color_pairs,
             selection_start=None, selection_end=None, tool_state=None):
    max_y, max_x = stdscr.getmaxyx()
    view_width = min(view_width, max_x)
    view_height = min(view_height, max_y - 3)

    sel_coords = set()
    if selection_start and selection_end:
        x0, y0 = selection_start
        x1, y1 = selection_end
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                sel_coords.add((x, y))

    for vy in range(view_height):
        my = camera_y + vy
        if my >= len(map_data): break
        for vx in range(view_width):
            mx = camera_x + vx
            if mx >= len(map_data[0]): break

            ch = map_data[my][mx]
            pair = color_pairs.get(ch, 1)
            attr = curses.color_pair(pair)

            if (mx, my) in sel_coords:
                attr = curses.color_pair(color_pairs.get('__SELECTION__', 1))

            if my == cursor_y and mx == cursor_x:
                attr |= curses.A_REVERSE

            if tool_state and tool_state.start_point and tool_state.start_point[0] == mx and tool_state.start_point[1] == my:
                attr |= curses.A_BOLD | curses.A_UNDERLINE

            if tool_state and tool_state.measure_start and tool_state.measure_start[0] == mx and tool_state.measure_start[1] == my:
                attr |= curses.A_BOLD | curses.A_UNDERLINE

            try:
                stdscr.addch(vy, vx, ch, attr)
            except curses.error:
                pass

    return view_height

def draw_status(stdscr, y, map_width, map_height, camera_x, camera_y,
                cursor_x, cursor_y, selected_char, tool_state, undo_stack, bindings):
    max_y, max_x = stdscr.getmaxyx()

    status1 = f'Map:{map_width}x{map_height} Cam:({camera_x},{camera_y}) Cursor:({cursor_x},{cursor_y}) Tool:{tool_state.mode}'
    if tool_state.brush_size > 1:
        status1 += f' Brush:{tool_state.brush_size}'
    status1 += f' Seed:{tool_state.seed}'
    if tool_state.snap_size > 1:
        status1 += f' Snap:{tool_state.snap_size}'
    if tool_state.auto_tiling:
        status1 += f' AutoTile:On'
    if tool_state.measure_start:
        dist = get_distance(tool_state.measure_start, (cursor_x, cursor_y))
        status1 += f' Dist:{dist:.1f}'
    stdscr.addstr(y, 0, status1[:max_x-1])

    undo_str = f'Undo:{len(undo_stack.undo_stack)}' if undo_stack.can_undo() else ''
    redo_str = f'Redo:{len(undo_stack.redo_stack)}' if undo_stack.can_redo() else ''
    status2 = f'Tile:{selected_char} {undo_str} {redo_str} [{get_key_name(bindings["show_help"])}]=Help [{get_key_name(bindings["quit"])}]=Quit'
    stdscr.addstr(y+1, 0, status2[:max_x-1])

def draw_help_overlay(stdscr, bindings):
    max_y, max_x = stdscr.getmaxyx()

    help_sections = [
        ("MOVEMENT", [
            f"View: {get_key_name(bindings['move_view_up'])}/{get_key_name(bindings['move_view_down'])}/{get_key_name(bindings['move_view_left'])}/{get_key_name(bindings['move_view_right'])} (WASD) | Cursor: Arrow Keys"
        ]),
        ("DRAWING TOOLS", [
            f"{get_key_name(bindings['place_tile'])}=Place tile at cursor | {get_key_name(bindings['cycle_tile'])}=Cycle tiles | {get_key_name(bindings['pick_tile'])}=Pick from menu",
            f"{get_key_name(bindings['toggle_palette'])}=Quick Tile Palette",
            f"{get_key_name(bindings['flood_fill'])}=Flood fill area | {get_key_name(bindings['line_tool'])}=Line tool | {get_key_name(bindings['rect_tool'])}=Rectangle | {get_key_name(bindings['circle_tool'])}=Circle",
            f"Pattern Fill: {get_key_name(bindings['pattern_tool'])}=Pattern mode | {get_key_name(bindings['define_pattern'])}=Define pattern",
            f"Custom Brush: {get_key_name(bindings['define_brush'])}=Define brush shape",
            f"Brush size: {get_key_name(bindings['decrease_brush'])}/{get_key_name(bindings['increase_brush'])}"
        ]),
        ("SELECTION & CLIPBOARD", [
            f"{get_key_name(bindings['select_start'])}=Start/End selection | {get_key_name(bindings['clear_selection'])}=Clear selection",
            f"{get_key_name(bindings['copy_selection'])}=Copy | {get_key_name(bindings['paste_selection'])}=Paste",
            f"{get_key_name(bindings['rotate_selection'])}=Rotate 90° | {get_key_name(bindings['flip_h'])}=Flip horizontal | {get_key_name(bindings['flip_v'])}=Flip vertical"
        ]),
        ("EDIT OPERATIONS", [
            f"{get_key_name(bindings['undo'])}=Undo (100 levels) | {get_key_name(bindings['redo'])}=Redo | {get_key_name(bindings['replace_all'])}=Replace all tiles",
            f"{get_key_name(bindings['clear_area'])}=Clear selected area | {get_key_name(bindings['statistics'])}=Show tile statistics"
        ]),
        ("MAP TRANSFORMATIONS", [
            f"{get_key_name(bindings['map_rotate'])}=Rotate map 90° | {get_key_name(bindings['map_flip_h'])}=Flip H | {get_key_name(bindings['map_flip_v'])}=Flip V",
            f"Shift Map: Arrows (mapped keys) to shift entire map contents"
        ]),
        ("PROCEDURAL GENERATION", [
            f"{get_key_name(bindings['random_gen'])}=Cellular automata caves | {get_key_name(bindings['perlin_noise'])}=Perlin noise terrain",
            f"{get_key_name(bindings['voronoi'])}=Voronoi diagram regions | {get_key_name(bindings['set_seed'])}=Set random seed"
        ]),
        ("FILE OPERATIONS", [
            f"{get_key_name(bindings['new_map'])}=New map | {get_key_name(bindings['load_map'])}=Load | {get_key_name(bindings['save_map'])}=Save",
            f"{get_key_name(bindings['resize_map'])}=Resize map | {get_key_name(bindings['export_image'])}=Export PNG/CSV"
        ]),
        ("CONFIGURATION", [
            f"{get_key_name(bindings['define_tiles'])}=Define custom tiles | {get_key_name(bindings['edit_controls'])}=Edit keybindings"
        ]),
        ("MACROS & AUTOMATION", [
            f"{get_key_name(bindings['macro_record_toggle'])}=Toggle Macro Recording | {get_key_name(bindings['macro_play'])}=Play Macro",
            f"Macros record action names. Use the Macro Manager in the menu to define/edit."
        ]),
        ("MEASUREMENT & SNAPPING", [
            f"{get_key_name(bindings['toggle_snap'])}=Set Grid Snap Size | {get_key_name(bindings['set_measure'])}=Set/Clear Measurement Start",
            f"Distance is shown in the status bar from the measurement start to the cursor."
        ]),
        ("AUTO-TILING", [
            f"{get_key_name(bindings['toggle_autotile'])}=Toggle Auto-Tiling",
            f"Use the Auto-Tiling Manager in the main menu or editor menu (F1) to define rules."
        ]),
        ("EDITOR MENU", [
            f"{get_key_name(bindings['editor_menu'])}=Open Editor Pause Menu (F1)",
            f"The menu allows saving, loading, and managing macros without quitting."
        ])
    ]

    all_lines = ["=== MAP EDITOR HELP (ESC to close) ===", ""]
    for section_name, section_lines in help_sections:
        all_lines.append(f"--- {section_name} ---")
        for line in section_lines:
            wrapped = textwrap.wrap(line, max_x - 6)
            all_lines.extend(wrapped)
        all_lines.append("")

    height = min(len(all_lines) + 2, max_y - 4)
    width = min(max_x - 4, max_x - 4)
    start_y = (max_y - height) // 2
    start_x = 2

    win = curses.newwin(height, width, start_y, start_x)
    win.border()

    scroll_offset = 0
    max_scroll = max(0, len(all_lines) - (height - 2))

    while True:
        win.clear()
        win.border()

        for i in range(height - 2):
            line_idx = scroll_offset + i
            if line_idx < len(all_lines):
                try:
                    win.addstr(i + 1, 2, all_lines[line_idx][:width-4])
                except:
                    pass

        win.refresh()
        key = win.getch()

        if key == 27:
            break
        elif key == curses.KEY_UP and scroll_offset > 0:
            scroll_offset -= 1
        elif key == curses.KEY_DOWN and scroll_offset < max_scroll:
            scroll_offset += 1
        elif key == curses.KEY_PPAGE:
            scroll_offset = max(0, scroll_offset - 10)
        elif key == curses.KEY_NPAGE:
            scroll_offset = min(max_scroll, scroll_offset + 10)

def menu_controls(stdscr, bindings):
    curses.curs_set(0)
    actions = list(bindings.keys())
    actions.sort()
    selected_idx = 0

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addstr(0, 0, "=== EDIT CONTROLS ===")
        stdscr.addstr(2, 0, "Action                          Key")
        stdscr.addstr(3, 0, "-" * min(50, max_x - 1))

        visible_actions = max_y - 12
        if visible_actions < 5: visible_actions = 5

        scroll_offset = 0
        if selected_idx >= visible_actions:
            scroll_offset = selected_idx - visible_actions + 1

        y = 4
        for i in range(visible_actions):
            idx = scroll_offset + i
            if idx >= len(actions): break
            action = actions[idx]
            key_val = bindings[action]
            key_name = get_key_name(key_val)
            line = f"{action:<30} {key_name}"
            attr = curses.A_REVERSE if idx == selected_idx else 0
            try:
                stdscr.addstr(y + i, 0, line[:max_x-1], attr)
            except: pass

        stdscr.addstr(max_y - 4, 0, "Up/Down: select | PgUp/PgDn: scroll fast | Enter: change")
        stdscr.addstr(max_y - 3, 0, "[D] reset to defaults | [Q] back")
        stdscr.refresh()

        key = stdscr.getch()
        if key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(actions)-1:
            selected_idx += 1
        elif key == curses.KEY_PPAGE:
            selected_idx = max(0, selected_idx - 10)
        elif key == curses.KEY_NPAGE:
            selected_idx = min(len(actions) - 1, selected_idx + 10)
        elif key in (ord('d'), ord('D')):
            stdscr.addstr(max_y - 1, 0, "Reset ALL keys to defaults? (y/n): ")
            stdscr.clrtoeol()
            stdscr.refresh()
            if stdscr.getch() in (ord('y'), ord('Y')):
                config_path = os.path.join(os.getcwd(), 'map_editor_config.json')
                if os.path.exists(config_path):
                    os.remove(config_path)
                new_defaults = load_config()
                bindings.clear()
                bindings.update(new_defaults)
                actions = list(bindings.keys())
                actions.sort()
        elif key in (curses.KEY_ENTER, 10, 13):
            action = actions[selected_idx]
            stdscr.addstr(max_y - 1, 0, f"Press new key for '{action[:20]}' (ESC=cancel): ")
            stdscr.clrtoeol()
            stdscr.refresh()
            new_key = stdscr.getch()
            if new_key != 27:
                conflict = [a for a, k in bindings.items() if k == new_key and a != action]
                if conflict:
                    msg = f"Key used by {conflict[0][:15]}. Overwrite? (y/n): "
                    stdscr.addstr(max_y - 1, 0, msg)
                    stdscr.clrtoeol()
                    stdscr.refresh()
                    confirm = stdscr.getch()
                    if confirm not in (ord('y'), ord('Y')):
                        continue
                bindings[action] = new_key
                save_config(bindings)
        elif key in (ord('q'), ord('Q'), 27):
            break

    return bindings

def menu_pick_tile(stdscr, tile_chars, tile_colors, color_pairs):
    curses.curs_set(0)
    max_y, max_x = stdscr.getmaxyx()
    height = min(len(tile_chars) + 4, max_y - 2)
    height = max(height, 8)
    height = min(height, max_y - 2)

    width = 35
    start_y = (max_y - height) // 2
    start_x = (max_x - width) // 2

    win = curses.newwin(height, width, start_y, start_x)
    win.keypad(True)
    win.nodelay(False)
    win.border()
    win.addstr(0, 2, " Select Tile ")

    selected_idx = 0
    visible_items = height - 4

    while True:
        scroll_offset = 0
        if selected_idx >= visible_items:
            scroll_offset = selected_idx - visible_items + 1

        win.clear()
        win.border()
        win.addstr(0, 2, " Select Tile ")

        for i in range(visible_items):
            idx = scroll_offset + i
            if idx >= len(tile_chars): break

            ch = tile_chars[idx]
            attr = curses.color_pair(color_pairs[ch])
            if idx == selected_idx:
                attr |= curses.A_REVERSE

            try:
                win.addstr(2 + i, 2, f"{ch} ", attr)
                col_name = [k for k,v in vars(curses).items()
                           if v == tile_colors[ch] and k.startswith('COLOR_')]
                col_name = col_name[0].replace('COLOR_', '').lower() if col_name else 'white'
                win.addstr(2 + i, 4, f"({col_name})", attr)
            except: pass

        win.refresh()
        key = win.getch()

        if key == curses.KEY_UP and selected_idx > 0:
            selected_idx -= 1
        elif key == curses.KEY_DOWN and selected_idx < len(tile_chars) - 1:
            selected_idx += 1
        elif key in (curses.KEY_ENTER, 10, 13, ord(' ')):
            return tile_chars[selected_idx]
        elif key == 27:
            return None
        elif 32 <= key <= 126 and chr(key) in tile_chars:
            return chr(key)

def menu_statistics(stdscr, map_data, map_width, map_height):
    stats = get_map_statistics(map_data, map_width, map_height)
    total = sum(stats.values())

    curses.curs_set(0)
    max_y, max_x = stdscr.getmaxyx()

    lines = ["=== MAP STATISTICS ===", ""]
    lines.append(f"Total tiles: {total}")
    lines.append("")

    for tile, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"'{tile}': {count} ({pct:.1f}%)")

    lines.append("")
    lines.append("Press any key to continue...")

    height = min(len(lines) + 2, max_y - 4)
    width = min(40, max_x - 4)
    start_y = (max_y - height) // 2
    start_x = (max_x - width) // 2

    win = curses.newwin(height, width, start_y, start_x)
    win.border()

    for i, line in enumerate(lines[:height-2]):
        try:
            win.addstr(i + 1, 2, line[:width-4])
        except: pass

    win.refresh()
    win.getch()

def menu_save_map(stdscr, map_data):
    curses.echo()
    curses.curs_set(1)
    max_y = stdscr.getmaxyx()[0]
    stdscr.addstr(max_y-2, 0, "Save map as: ")
    stdscr.clrtoeol()
    stdscr.refresh()
    filename = stdscr.getstr().decode().strip()

    if filename and os.path.exists(filename):
        stdscr.addstr(max_y-1, 0, f"File exists. Overwrite? (y/n): ")
        stdscr.clrtoeol()
        stdscr.refresh()
        confirm = stdscr.getch()
        if confirm not in (ord('y'), ord('Y')):
            curses.noecho()
            curses.curs_set(0)
            return False

    success = False
    if filename:
        try:
            with open(filename, 'w') as f:
                for row in map_data:
                    f.write(''.join(row) + '\n')
            stdscr.addstr(max_y-1, 0, f"Saved to {filename}. Press any key...")
            success = True
        except Exception as e:
            stdscr.addstr(max_y-1, 0, f"Error: {str(e)[:30]}. Press any key...")
        stdscr.clrtoeol()
        stdscr.refresh()
        stdscr.getch()

    curses.noecho()
    curses.curs_set(0)
    return success

def menu_export_image(stdscr, map_data, tile_colors):
    curses.echo()
    curses.curs_set(1)
    max_y = stdscr.getmaxyx()[0]
    stdscr.addstr(max_y-3, 0, "Export as (.png/.csv): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    filename = stdscr.getstr().decode().strip()

    if filename:
        if not filename.endswith('.png') and not filename.endswith('.csv'):
            filename += '.png'

        if filename.endswith('.png'):
            stdscr.addstr(max_y-2, 0, "Tile size in pixels (default 8): ")
            stdscr.clrtoeol()
            stdscr.refresh()
            tile_size_input = stdscr.getstr().decode().strip()
            tile_size = int(tile_size_input) if tile_size_input else 8

            try:
                export_to_image(map_data, tile_colors, filename, tile_size)
                stdscr.addstr(max_y-1, 0, f"Exported PNG to {filename}. Press any key...")
            except Exception as e:
                stdscr.addstr(max_y-1, 0, f"Error: {str(e)[:30]}. Press any key...")
        elif filename.endswith('.csv'):
            try:
                with open(filename, 'w') as f:
                    for row in map_data:
                        f.write(','.join(row) + '\n')
                stdscr.addstr(max_y-1, 0, f"Exported CSV to {filename}. Press any key...")
            except Exception as e:
                stdscr.addstr(max_y-1, 0, f"Error: {str(e)[:30]}. Press any key...")

        stdscr.clrtoeol()
        stdscr.refresh()
        stdscr.getch()

    curses.noecho()
    curses.curs_set(0)

def menu_load_map(stdscr, view_width, view_height):
    curses.echo()
    curses.curs_set(1)
    max_y = stdscr.getmaxyx()[0]
    stdscr.addstr(max_y-2, 0, "Load map from: ")
    stdscr.clrtoeol()
    stdscr.refresh()
    filename = stdscr.getstr().decode().strip()

    if not filename or not os.path.exists(filename):
        curses.noecho()
        curses.curs_set(0)
        return None, 0, 0

    try:
        with open(filename, 'r') as f:
            lines = [line.rstrip('\n') for line in f]

        if not lines:
            curses.noecho()
            curses.curs_set(0)
            return None, 0, 0

        width = max(len(line) for line in lines) if lines else view_width
        height = len(lines)

        if height < view_height: height = view_height
        if width < view_width: width = view_width

        map_data = [['.' for _ in range(width)] for _ in range(height)]

        for y, line in enumerate(lines):
            for x, ch in enumerate(line):
                if y < height and x < width:
                    map_data[y][x] = ch

        curses.noecho()
        curses.curs_set(0)
        return map_data, width, height
    except:
        curses.noecho()
        curses.curs_set(0)
        return None, 0, 0

def menu_new_map(stdscr, view_width, view_height):
    curses.echo()
    curses.curs_set(1)
    stdscr.clear()
    stdscr.addstr(0, 0, "New Map")

    w = view_width
    while True:
        stdscr.addstr(2, 0, f"Map width (min {view_width}): ")
        stdscr.clrtoeol()
        stdscr.refresh()
        try:
            inp = stdscr.getstr().decode().strip()
            if not inp:
                w = view_width
                break
            val = int(inp)
            if val >= view_width:
                w = val
                break
        except ValueError:
            pass

    h = view_height
    while True:
        stdscr.addstr(3, 0, f"Map height (min {view_height}): ")
        stdscr.clrtoeol()
        stdscr.refresh()
        try:
            inp = stdscr.getstr().decode().strip()
            if not inp:
                h = view_height
                break
            val = int(inp)
            if val >= view_height:
                h = val
                break
        except ValueError:
            pass

    stdscr.addstr(4, 0, "Border char (default #, leave empty/'.' for none): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    border_input = stdscr.getstr().decode().strip()

    if not border_input or border_input == '.':
        border_char = None
    else:
        border_char = border_input[0]

    curses.noecho()
    curses.curs_set(0)

    map_data = [['.' for _ in range(w)] for _ in range(h)]

    if border_char:
        for x in range(w):
            map_data[0][x] = border_char
            map_data[h-1][x] = border_char
        for y in range(h):
            map_data[y][0] = border_char
            map_data[y][w-1] = border_char

    return map_data, w, h

def menu_define_tiles(stdscr, tile_chars, tile_colors):
    curses.echo()
    curses.curs_set(1)
    scroll_offset = 0
    selected_idx = 0

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addstr(0, 0, "=== DEFINE TILES ===")
        stdscr.addstr(2, 0, "Current tiles (char:color):")

        visible_rows = max_y - 10
        if visible_rows < 5: visible_rows = 5

        if scroll_offset > max(0, len(tile_chars) - visible_rows):
            scroll_offset = max(0, len(tile_chars) - visible_rows)

        y = 3
        for i in range(visible_rows):
            idx = scroll_offset + i
            if idx >= len(tile_chars): break
            ch = tile_chars[idx]
            col_val = tile_colors[ch]
            col_name = 'white'
            for name, val in COLOR_MAP.items():
                if val == col_val:
                    col_name = name
                    break

            attr = curses.A_REVERSE if idx == selected_idx else 0
            try:
                stdscr.addstr(y + i, 2, f"{ch} : {col_name:<10}", attr)
            except: pass

        prompt_y = max_y - 4
        stdscr.addstr(prompt_y, 0, "Options: [A] add | [E] edit color | [R] remove | [Q] back")
        stdscr.addstr(prompt_y + 1, 0, "Use Arrows to navigate and scroll.")
        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP:
            if selected_idx > 0:
                selected_idx -= 1
                if selected_idx < scroll_offset:
                    scroll_offset = selected_idx
        elif key == curses.KEY_DOWN:
            if selected_idx < len(tile_chars) - 1:
                selected_idx += 1
                if selected_idx >= scroll_offset + visible_rows:
                    scroll_offset = selected_idx - visible_rows + 1
        elif key in (ord('q'), ord('Q'), 27):
            break
        elif key in (ord('a'), ord('A')):
            stdscr.addstr(prompt_y + 2, 0, "Enter tile character: ")
            stdscr.clrtoeol()
            ch_in = stdscr.getstr().decode().strip()
            if len(ch_in) == 1:
                ch = ch_in
                stdscr.addstr(prompt_y + 2, 0, f"Color for '{ch}' (red, green, etc.): ")
                stdscr.clrtoeol()
                col = stdscr.getstr().decode().strip().lower()
                if col not in COLOR_MAP:
                    stdscr.addstr(prompt_y + 3, 0, "Unknown color, using white. Press any key...")
                    stdscr.clrtoeol()
                    stdscr.refresh()
                    stdscr.getch()
                color_val = parse_color_name(col)
                tile_colors[ch] = color_val
                if ch not in tile_chars:
                    tile_chars.append(ch)
                    selected_idx = len(tile_chars) - 1
        elif key in (ord('e'), ord('E')):
            if 0 <= selected_idx < len(tile_chars):
                ch = tile_chars[selected_idx]
                stdscr.addstr(prompt_y + 2, 0, f"New color for '{ch}': ")
                stdscr.clrtoeol()
                col = stdscr.getstr().decode().strip().lower()
                if col:
                    if col not in COLOR_MAP:
                        stdscr.addstr(prompt_y + 3, 0, "Unknown color, using white. Press any key...")
                        stdscr.clrtoeol()
                        stdscr.refresh()
                        stdscr.getch()
                    tile_colors[ch] = parse_color_name(col)
        elif key in (ord('r'), ord('R')):
            if len(tile_chars) > 1 and 0 <= selected_idx < len(tile_chars):
                ch = tile_chars[selected_idx]
                del tile_colors[ch]
                tile_chars.remove(ch)
                if selected_idx >= len(tile_chars):
                    selected_idx = len(tile_chars) - 1

    curses.noecho()
    curses.curs_set(0)

def menu_random_generation(stdscr, map_data, map_width, map_height, tile_chars, seed=None):
    curses.curs_set(0)

    stdscr.clear()
    stdscr.addstr(0, 0, "=== CELLULAR AUTOMATA GENERATION ===")
    curses.echo()
    curses.curs_set(1)

    stdscr.addstr(2, 0, "Iterations (3-10, default 5): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    try:
        iterations = int(stdscr.getstr().decode().strip() or "5")
        iterations = max(3, min(10, iterations))
    except:
        iterations = 5

    stdscr.addstr(3, 0, "Wall char (default #): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    wall = stdscr.getstr().decode().strip() or "#"
    wall = wall[0] if wall else '#'

    stdscr.addstr(4, 0, "Floor char (default .): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    floor = stdscr.getstr().decode().strip() or "."
    floor = floor[0] if floor else '.'

    curses.noecho()
    curses.curs_set(0)

    cellular_automata_cave(map_data, map_width, map_height, iterations, wall, floor, seed)
    return True

def menu_perlin_generation(stdscr, map_data, map_width, map_height, tile_chars, seed=0):
    curses.curs_set(0)

    stdscr.clear()
    stdscr.addstr(0, 0, "=== PERLIN NOISE GENERATION ===")
    curses.echo()
    curses.curs_set(1)

    stdscr.addstr(2, 0, "Scale (1-50, default 10): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    try:
        scale = float(stdscr.getstr().decode().strip() or "10")
        scale = max(1, min(50, scale))
    except:
        scale = 10.0

    stdscr.addstr(3, 0, "Octaves (1-8, default 4): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    try:
        octaves = int(stdscr.getstr().decode().strip() or "4")
        octaves = max(1, min(8, octaves))
    except:
        octaves = 4

    stdscr.addstr(4, 0, "Persistence (0.1-1.0, default 0.5): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    try:
        persistence = float(stdscr.getstr().decode().strip() or "0.5")
        persistence = max(0.1, min(1.0, persistence))
    except:
        persistence = 0.5

    curses.noecho()
    curses.curs_set(0)

    try:
        perlin_noise_generation(map_data, tile_chars, map_width, map_height, scale, octaves, persistence, seed)
        return True
    except ImportError:
        stdscr.addstr(4, 0, "Error: 'noise' library not installed. Install with: pip install noise")
        stdscr.addstr(5, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False

def menu_voronoi_generation(stdscr, map_data, map_width, map_height, tile_chars, seed=None):
    curses.curs_set(0)

    stdscr.clear()
    stdscr.addstr(0, 0, "=== VORONOI DIAGRAM GENERATION ===")
    curses.echo()
    curses.curs_set(1)

    stdscr.addstr(2, 0, "Number of regions (5-50, default 20): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    try:
        num_points = int(stdscr.getstr().decode().strip() or "20")
        num_points = max(5, min(50, num_points))
    except:
        num_points = 20

    curses.noecho()
    curses.curs_set(0)

    voronoi_generation(map_data, tile_chars, map_width, map_height, num_points, seed)
    return True

def menu_resize_map(stdscr, map_data, width, height, view_width, view_height):
    curses.echo()
    curses.curs_set(1)
    stdscr.clear()
    stdscr.addstr(0, 0, "=== RESIZE MAP ===")

    w = width
    while True:
        stdscr.addstr(2, 0, f"New width (current {width}, min {view_width}): ")
        stdscr.clrtoeol()
        stdscr.refresh()
        try:
            inp = stdscr.getstr().decode().strip()
            if not inp:
                w = width
                break
            val = int(inp)
            if val >= view_width:
                w = val
                break
        except ValueError:
            pass

    h = height
    while True:
        stdscr.addstr(3, 0, f"New height (current {height}, min {view_height}): ")
        stdscr.clrtoeol()
        stdscr.refresh()
        try:
            inp = stdscr.getstr().decode().strip()
            if not inp:
                h = height
                break
            val = int(inp)
            if val >= view_height:
                h = val
                break
        except ValueError:
            pass

    stdscr.addstr(4, 0, "Fill char (default .): ")
    stdscr.clrtoeol()
    stdscr.refresh()
    fill_input = stdscr.getstr().decode().strip()
    fill_char = fill_input[0] if fill_input else '.'

    curses.noecho()
    curses.curs_set(0)

    if w == width and h == height:
        return None, width, height

    new_map = [[fill_char for _ in range(w)] for _ in range(h)]
    for y in range(min(h, height)):
        for x in range(min(w, width)):
            new_map[y][x] = map_data[y][x]

    return new_map, w, h

def menu_set_seed(stdscr, current_seed):
    curses.echo()
    curses.curs_set(1)
    stdscr.clear()
    stdscr.addstr(0, 0, "=== SET RANDOM SEED ===")
    stdscr.addstr(2, 0, f"Current seed: {current_seed}")
    stdscr.addstr(3, 0, "New seed (integer): ")
    stdscr.refresh()

    new_seed = current_seed
    try:
        inp = stdscr.getstr().decode().strip()
        if inp:
            new_seed = int(inp)
    except:
        pass

    curses.noecho()
    curses.curs_set(0)
    return new_seed

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

def get_distance(p1, p2):
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

def apply_autotiling(map_data, x, y, base_char, rules, width, height):
    if base_char not in rules: return base_char
    mask = 0
    target_set = set(rules[base_char].values()) | {base_char}
    if y > 0 and map_data[y-1][x] in target_set: mask |= 1
    if x < width - 1 and map_data[y][x+1] in target_set: mask |= 2
    if y < height - 1 and map_data[y+1][x] in target_set: mask |= 4
    if x > 0 and map_data[y][x-1] in target_set: mask |= 8
    return rules[base_char].get(mask, base_char)

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

def draw_tile_palette(stdscr, tile_chars, color_pairs, selected_char):
    max_y, max_x = stdscr.getmaxyx()
    cols_count = max_x - 10
    rows = (len(tile_chars) // cols_count) + 1
    win_h = rows + 2
    win_w = max_x - 4

    win = curses.newwin(win_h, win_w, max_y - win_h - 3, 2)
    win.border()
    win.addstr(0, 2, " Tile Palette ")

    for i, ch in enumerate(tile_chars):
        attr = curses.color_pair(color_pairs.get(ch, 1))
        if ch == selected_char:
            attr |= curses.A_REVERSE | curses.A_BOLD

        try:
            win.addch(1 + (i // (win_w - 4)), 2 + (i % (win_w - 4)), ch, attr)
        except: pass

    win.refresh()

def menu_autosave_settings(stdscr, tool_state):
    curses.echo()
    curses.curs_set(1)
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "=== AUTOSAVE SETTINGS ===", curses.A_BOLD)
        stdscr.addstr(2, 0, f"1. Autosave Enabled: {'Yes' if tool_state.autosave_enabled else 'No'}")
        stdscr.addstr(3, 0, f"2. Autosave Mode: {tool_state.autosave_mode.capitalize()}")
        if tool_state.autosave_mode == 'time':
            stdscr.addstr(4, 0, f"3. Save Interval: {tool_state.autosave_interval} minutes")
        else:
            stdscr.addstr(4, 0, f"3. Edit Threshold: {tool_state.autosave_edits_threshold} edits")
        stdscr.addstr(5, 0, f"4. Filename: {tool_state.autosave_filename}")
        stdscr.addstr(7, 0, "Select option (1-4) or [Q] to back: ")
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27): break
        elif key == ord('1'):
            tool_state.autosave_enabled = not tool_state.autosave_enabled
        elif key == ord('2'):
            tool_state.autosave_mode = 'edits' if tool_state.autosave_mode == 'time' else 'time'
        elif key == ord('3'):
            if tool_state.autosave_mode == 'time':
                stdscr.addstr(9, 0, "Enter interval (minutes, 1-60): ")
                stdscr.clrtoeol()
                try:
                    val = int(stdscr.getstr().decode().strip())
                    tool_state.autosave_interval = max(1, min(60, val))
                except: pass
            else:
                stdscr.addstr(9, 0, "Enter edit threshold (1-500): ")
                stdscr.clrtoeol()
                try:
                    val = int(stdscr.getstr().decode().strip())
                    tool_state.autosave_edits_threshold = max(1, min(500, val))
                except: pass
        elif key == ord('4'):
            stdscr.addstr(9, 0, "Enter filename: ")
            stdscr.clrtoeol()
            name = stdscr.getstr().decode().strip()
            if name: tool_state.autosave_filename = name

    curses.noecho()
    curses.curs_set(0)

def menu_editor_pause(stdscr):
    curses.curs_set(0)
    options = ["Resume", "Save Map", "Load Map", "Macro Manager", "Auto-Tiling Manager", "Autosave Settings", "Exit to Main Menu", "Quit Editor"]
    selected = 0

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addstr(2, 2, "=== EDITOR MENU ===", curses.A_BOLD)

        for i, opt in enumerate(options):
            attr = curses.A_REVERSE if i == selected else 0
            stdscr.addstr(4 + i, 4, opt, attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP and selected > 0: selected -= 1
        elif key == curses.KEY_DOWN and selected < len(options) - 1: selected += 1
        elif key in (10, 13, ord(' ')):
            return options[selected]
        elif key == 27:
            return "Resume"

def menu_macros(stdscr, tool_state):
    curses.echo()
    curses.curs_set(1)

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addstr(0, 0, "=== MACRO MANAGER ===", curses.A_BOLD)
        stdscr.addstr(2, 0, "Macros allow you to automate sequences of actions.")
        stdscr.addstr(3, 0, "Current Macros:")

        y = 5
        macro_names = list(tool_state.macros.keys())
        for name in macro_names:
            stdscr.addstr(y, 2, f"- {name} ({len(tool_state.macros[name])} actions)")
            y += 1

        stdscr.addstr(max_y - 4, 0, "[A] Add/Define | [R] Remove | [L] List Actions | [Q] Back")
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27): break

        elif key in (ord('a'), ord('A')):
            stdscr.addstr(max_y - 2, 0, "Enter macro name: ")
            name = stdscr.getstr().decode().strip()
            if name:
                stdscr.addstr(max_y - 1, 0, "Enter actions (comma separated, e.g. move_cursor_right,place_tile): ")
                actions_str = stdscr.getstr().decode().strip()
                if actions_str:
                    actions = [a.strip() for a in actions_str.split(',')]
                    tool_state.macros[name] = actions

        elif key in (ord('r'), ord('R')):
            stdscr.addstr(max_y - 2, 0, "Enter macro name to remove: ")
            name = stdscr.getstr().decode().strip()
            if name in tool_state.macros:
                del tool_state.macros[name]

        elif key in (ord('l'), ord('L')):
            stdscr.addstr(max_y - 2, 0, "Enter macro name to list: ")
            name = stdscr.getstr().decode().strip()
            if name in tool_state.macros:
                stdscr.clear()
                stdscr.addstr(0, 0, f"=== Actions for {name} ===")
                for i, act in enumerate(tool_state.macros[name]):
                    if i > max_y - 5: break
                    stdscr.addstr(i + 2, 2, act)
                stdscr.addstr(max_y - 1, 0, "Press any key...")
                stdscr.refresh()
                curses.noecho()
                stdscr.getch()
                curses.echo()

    curses.noecho()
    curses.curs_set(0)

def menu_define_autotiling(stdscr, tool_state, tile_chars):
    curses.echo()
    curses.curs_set(1)

    while True:
        stdscr.clear()
        max_y, max_x = stdscr.getmaxyx()
        stdscr.addstr(0, 0, "=== AUTO-TILING MANAGER ===", curses.A_BOLD)
        stdscr.addstr(2, 0, "Current Rules (Base Tile -> Variants):")

        y = 4
        for base in tool_state.tiling_rules:
            count = len(tool_state.tiling_rules[base])
            stdscr.addstr(y, 2, f"- '{base}': {count} variants defined")
            y += 1

        stdscr.addstr(max_y - 4, 0, "[A] Add/Edit Rules | [R] Remove Rules | [Q] Back")
        stdscr.refresh()

        key = stdscr.getch()
        if key in (ord('q'), ord('Q'), 27): break

        elif key in (ord('a'), ord('A')):
            stdscr.addstr(max_y - 2, 0, "Enter base tile character: ")
            base = stdscr.getstr().decode().strip()
            if len(base) == 1:
                if base not in tool_state.tiling_rules:
                    tool_state.tiling_rules[base] = {}

                stdscr.clear()
                stdscr.addstr(0, 0, f"=== Rules for '{base}' (Bitmask: 1=U, 2=R, 4=D, 8=L) ===")
                stdscr.addstr(2, 0, "Example: Mask 1 is only Up neighbor, Mask 15 is all neighbors.")

                for mask in range(1, 16):
                    row = 4 + (mask - 1)
                    if row >= max_y - 2: break

                    binary = bin(mask)[2:].zfill(4)
                    stdscr.addstr(row, 2, f"Mask {mask:2} ({binary} [LDRU]): Variant char (blank to skip): ")
                    curr = tool_state.tiling_rules[base].get(mask, "")
                    if curr: stdscr.addstr(f" (current: {curr})")
                    stdscr.refresh()

                    variant = stdscr.getstr().decode().strip()
                    if variant:
                        tool_state.tiling_rules[base][mask] = variant[0]

        elif key in (ord('r'), ord('R')):
            stdscr.addstr(max_y - 2, 0, "Enter base tile to remove: ")
            base = stdscr.getstr().decode().strip()
            if base in tool_state.tiling_rules:
                del tool_state.tiling_rules[base]

    curses.noecho()
    curses.curs_set(0)

def menu_define_brush(stdscr):
    curses.echo()
    curses.curs_set(1)
    stdscr.clear()
    stdscr.addstr(0, 0, "=== DEFINE CUSTOM BRUSH ===")
    stdscr.addstr(2, 0, "Brush size (odd number, 1-7, default 3): ")
    try:
        inp = stdscr.getstr().decode().strip()
        size = int(inp) if inp else 3
    except:
        size = 3
    size = max(1, min(7, size))
    if size % 2 == 0: size += 1

    brush = [[False for _ in range(size)] for _ in range(size)]

    stdscr.addstr(4, 0, f"Design your {size}x{size} brush.")
    stdscr.addstr(5, 0, "Use Arrows to move, SPACE to toggle, ENTER to save, Q to cancel.")
    curses.noecho()
    curses.curs_set(1)

    by, bx = 0, 0
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "=== DEFINE CUSTOM BRUSH ===")
        stdscr.addstr(4, 0, f"Design your {size}x{size} brush.")
        stdscr.addstr(5, 0, "Use Arrows to move, SPACE to toggle, ENTER to save, Q to cancel.")

        for ry in range(size):
            for rx in range(size):
                char = 'X' if brush[ry][rx] else '.'
                attr = curses.A_REVERSE if (ry == by and rx == bx) else 0
                try:
                    stdscr.addch(7 + ry, rx * 2, char, attr)
                except: pass

        stdscr.refresh()
        key = stdscr.getch()
        if key == curses.KEY_UP and by > 0: by -= 1
        elif key == curses.KEY_DOWN and by < size - 1: by += 1
        elif key == curses.KEY_LEFT and bx > 0: bx -= 1
        elif key == curses.KEY_RIGHT and bx < size - 1: bx += 1
        elif key == ord(' '): brush[by][bx] = not brush[by][bx]
        elif key in (10, 13):
            curses.noecho()
            curses.curs_set(0)
            return brush
        elif key in (ord('q'), ord('Q'), 27):
            curses.noecho()
            curses.curs_set(0)
            return None

def menu_define_pattern(stdscr, tile_chars, tile_colors):
    curses.echo()
    curses.curs_set(1)
    stdscr.clear()
    stdscr.addstr(0, 0, "=== DEFINE PATTERN ===")
    stdscr.addstr(2, 0, "Pattern size (e.g. 2 for 2x2, 3 for 3x3, max 5): ")
    try:
        size_str = stdscr.getstr().decode().strip()
        size = int(size_str) if size_str else 2
    except:
        size = 2

    size = max(1, min(5, size))
    pattern = [['.' for _ in range(size)] for _ in range(size)]

    for r in range(size):
        for c in range(size):
            stdscr.addstr(4 + r, 0, f"Char for ({r},{c}): ")
            ch = stdscr.getstr().decode().strip()
            pattern[r][c] = ch[0] if ch else '.'

    curses.noecho()
    curses.curs_set(0)
    return pattern

def draw_pattern_rectangle(map_data, x0, y0, x1, y1, pattern, width, height):
    if not pattern: return
    p_h = len(pattern)
    p_w = len(pattern[0])

    min_x = max(0, min(x0, x1))
    max_x = min(width - 1, max(x0, x1))
    min_y = max(0, min(y0, y1))
    max_y = min(height - 1, max(y0, y1))

    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            map_data[y][x] = pattern[(y - min_y) % p_h][(x - min_x) % p_w]

def editor(stdscr, map_data, map_width, map_height, view_width, view_height,
           tile_chars, tile_colors, bindings, macros=None, tiling_rules=None):
    curses.curs_set(0)
    stdscr.nodelay(False)
    stdscr.timeout(1000)
    stdscr.keypad(True)

    key_map = build_key_map(bindings)
    camera_x = 0
    camera_y = 0
    cursor_x = 0
    cursor_y = 0
    selected_idx = 0
    selected_char = tile_chars[selected_idx]
    color_pairs = init_color_pairs(tile_colors)

    tool_state = ToolState(macros=macros, tiling_rules=tiling_rules)

    selection_start = None
    selection_end = None
    clipboard = None

    undo_stack = UndoStack()

    max_y, max_x = stdscr.getmaxyx()
    while True:
        if curses.is_term_resized(max_y, max_x):
            try:
                cols, lines = shutil.get_terminal_size()
                curses.resizeterm(lines, cols)
            except:
                pass
            max_y, max_x = stdscr.getmaxyx()
            view_width = min(view_width, max_x)
            view_height = min(view_height, max_y - 3)
            camera_x = max(0, min(camera_x, map_width - view_width))
            camera_y = max(0, min(camera_y, map_height - view_height))
            stdscr.clear()
            stdscr.refresh()

        stdscr.clear()

        status_y = draw_map(stdscr, map_data, camera_x, camera_y, view_width, view_height,
                           cursor_x, cursor_y, selected_char, color_pairs,
                           selection_start, selection_end, tool_state)

        draw_status(stdscr, status_y, map_width, map_height, camera_x, camera_y,
                   cursor_x, cursor_y, selected_char, tool_state, undo_stack, bindings)

        if tool_state.show_palette:
            draw_tile_palette(stdscr, tile_chars, color_pairs, selected_char)

        stdscr.refresh()
        key = stdscr.getch()

        # Autosave check
        if tool_state.autosave_enabled and tool_state.dirty:
            should_save = False
            if tool_state.autosave_mode == 'time':
                if time.time() - tool_state.last_autosave_time > tool_state.autosave_interval * 60:
                    should_save = True
            elif tool_state.autosave_mode == 'edits':
                if tool_state.edits_since_save >= tool_state.autosave_edits_threshold:
                    should_save = True

            if should_save:
                try:
                    with open(tool_state.autosave_filename, 'w') as f:
                        for row in map_data:
                            f.write(''.join(row) + '\n')
                    tool_state.last_autosave_time = time.time()
                    tool_state.edits_since_save = 0
                except: pass

        if key == -1: continue

        # ESC handling
        if key == 27:
            if tool_state.start_point:
                tool_state.start_point = None
            elif selection_start:
                selection_start = None
                selection_end = None
            else:
                tool_state.mode = 'place'
            continue

        pending_actions = []
        if key in key_map:
            pending_actions.extend(key_map[key])

        while pending_actions:
            action = pending_actions.pop(0)

            # Recording logic
            if tool_state.recording and action not in ('macro_record_toggle', 'macro_play', 'editor_menu'):
                tool_state.current_macro_actions.append(action)

            if action == 'quit':
                if tool_state.dirty:
                    stdscr.addstr(status_y + 2, 0, "Unsaved changes! Quit anyway? (y/n): ")
                    stdscr.clrtoeol()
                    stdscr.refresh()
                    if stdscr.getch() not in (ord('y'), ord('Y')):
                        continue
                return

            elif action == 'editor_menu':
                choice = menu_editor_pause(stdscr)
                if choice == "Resume": pass
                elif choice == "Save Map":
                    if menu_save_map(stdscr, map_data):
                        tool_state.dirty = False
                elif choice == "Load Map":
                    loaded, w, h = menu_load_map(stdscr, view_width, view_height)
                    if loaded:
                        undo_stack.push(map_data)
                        map_data[:] = loaded
                        map_width, map_height = w, h
                        camera_x, camera_y = 0, 0
                        cursor_x, cursor_y = 0, 0
                        selection_start, selection_end = None, None
                        tool_state.dirty = False
                elif choice == "Macro Manager":
                    menu_macros(stdscr, tool_state)
                elif choice == "Auto-Tiling Manager":
                    menu_define_autotiling(stdscr, tool_state, tile_chars)
                elif choice == "Autosave Settings":
                    menu_autosave_settings(stdscr, tool_state)
                elif choice == "Exit to Main Menu":
                    if tool_state.dirty:
                        stdscr.addstr(status_y + 2, 0, "Unsaved changes! Exit anyway? (y/n): ")
                        stdscr.clrtoeol()
                        stdscr.refresh()
                        if stdscr.getch() in (ord('y'), ord('Y')): return
                    else: return
                elif choice == "Quit Editor":
                    if tool_state.dirty:
                        stdscr.addstr(status_y + 2, 0, "Unsaved changes! Quit anyway? (y/n): ")
                        stdscr.clrtoeol()
                        stdscr.refresh()
                        if stdscr.getch() in (ord('y'), ord('Y')): sys.exit(0)
                    else: sys.exit(0)

            elif action == 'macro_record_toggle':
                if tool_state.recording:
                    tool_state.recording = False
                    stdscr.addstr(status_y + 2, 0, "Enter name for this macro: ")
                    stdscr.clrtoeol()
                    curses.echo()
                    name = stdscr.getstr().decode().strip()
                    curses.noecho()
                    if name:
                        tool_state.macros[name] = list(tool_state.current_macro_actions)
                    tool_state.current_macro_actions = []
                else:
                    tool_state.recording = True
                    tool_state.current_macro_actions = []

            elif action == 'macro_play':
                stdscr.addstr(status_y + 2, 0, "Enter macro name to play: ")
                stdscr.clrtoeol()
                curses.echo()
                name = stdscr.getstr().decode().strip()
                curses.noecho()
                if name in tool_state.macros:
                    pending_actions = list(tool_state.macros[name]) + pending_actions

            elif action == 'toggle_snap':
                stdscr.addstr(status_y + 2, 0, "Enter snap size (1=none, 2, 4, etc.): ")
                stdscr.clrtoeol()
                curses.echo()
                try:
                    tool_state.snap_size = int(stdscr.getstr().decode().strip() or "1")
                except: pass
                curses.noecho()

            elif action == 'set_measure':
                if tool_state.measure_start is None:
                    tool_state.measure_start = (cursor_x, cursor_y)
                else:
                    tool_state.measure_start = None

            elif action == 'toggle_palette':
                tool_state.show_palette = not tool_state.show_palette

            elif action == 'toggle_autotile':
                if tool_state.auto_tiling:
                    tool_state.auto_tiling = False
                else:
                    if selected_char not in tool_state.tiling_rules:
                        stdscr.addstr(status_y + 2, 0, f"No tiling rules for '{selected_char}'! Press any key...")
                        stdscr.clrtoeol()
                        stdscr.refresh()
                        stdscr.getch()
                    else:
                        tool_state.auto_tiling = True

            elif action == 'move_view_up' and camera_y > 0:
                camera_y -= 1
            elif action == 'move_view_down' and camera_y < map_height - view_height:
                camera_y += 1
            elif action == 'move_view_left' and camera_x > 0:
                camera_x -= 1
            elif action == 'move_view_right' and camera_x < map_width - view_width:
                camera_x += 1

            elif action == 'move_cursor_up' and cursor_y > 0:
                cursor_y -= tool_state.snap_size
                cursor_y = max(0, cursor_y)
                if cursor_y < camera_y:
                    camera_y = cursor_y
            elif action == 'move_cursor_down' and cursor_y < map_height - 1:
                cursor_y += tool_state.snap_size
                cursor_y = min(map_height - 1, cursor_y)
                if cursor_y >= camera_y + view_height:
                    camera_y = cursor_y - view_height + 1
            elif action == 'move_cursor_left' and cursor_x > 0:
                cursor_x -= tool_state.snap_size
                cursor_x = max(0, cursor_x)
                if cursor_x < camera_x:
                    camera_x = cursor_x
            elif action == 'move_cursor_right' and cursor_x < map_width - 1:
                cursor_x += tool_state.snap_size
                cursor_x = min(map_width - 1, cursor_x)
                if cursor_x >= camera_x + view_width:
                    camera_x = cursor_x - view_width + 1

            elif action == 'increase_brush':
                tool_state.brush_size = min(tool_state.brush_size + 1, 10)

            elif action == 'decrease_brush':
                tool_state.brush_size = max(tool_state.brush_size - 1, 1)

            elif action == 'place_tile':
                if tool_state.mode == 'place':
                    undo_stack.push(map_data)
                    place_tile_at(map_data, cursor_x, cursor_y, selected_char, map_width, map_height, tool_state.brush_size, tool_state.brush_shape, tool_state)
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1

                elif tool_state.mode == 'line':
                    if tool_state.start_point is None:
                        tool_state.start_point = (cursor_x, cursor_y)
                    else:
                        undo_stack.push(map_data)
                        draw_line(map_data, tool_state.start_point[0], tool_state.start_point[1],
                                cursor_x, cursor_y, selected_char, map_width, map_height, tool_state.brush_size, tool_state.brush_shape, tool_state)
                        tool_state.start_point = None
                        tool_state.dirty = True
                        tool_state.edits_since_save += 1

                elif tool_state.mode == 'rect':
                    if tool_state.start_point is None:
                        tool_state.start_point = (cursor_x, cursor_y)
                    else:
                        undo_stack.push(map_data)
                        stdscr.addstr(status_y + 2, 0, "Filled? (y/n): ")
                        stdscr.clrtoeol()
                        stdscr.refresh()
                        filled_key = stdscr.getch()
                        filled = filled_key in (ord('y'), ord('Y'))
                        draw_rectangle(map_data, tool_state.start_point[0], tool_state.start_point[1],
                                     cursor_x, cursor_y, selected_char, filled, map_width, map_height, tool_state.brush_size, tool_state.brush_shape, tool_state)
                        tool_state.start_point = None
                        tool_state.dirty = True
                        tool_state.edits_since_save += 1

                elif tool_state.mode == 'circle':
                    if tool_state.start_point is None:
                        tool_state.start_point = (cursor_x, cursor_y)
                    else:
                        undo_stack.push(map_data)
                        radius = int(((cursor_x - tool_state.start_point[0]) ** 2 +
                                    (cursor_y - tool_state.start_point[1]) ** 2) ** 0.5)
                        stdscr.addstr(status_y + 2, 0, "Filled? (y/n): ")
                        stdscr.clrtoeol()
                        stdscr.refresh()
                        filled_key = stdscr.getch()
                        filled = filled_key in (ord('y'), ord('Y'))
                        draw_circle(map_data, tool_state.start_point[0], tool_state.start_point[1],
                                  radius, selected_char, filled, map_width, map_height, tool_state.brush_size, tool_state.brush_shape, tool_state)
                        tool_state.start_point = None
                        tool_state.dirty = True
                        tool_state.edits_since_save += 1

                elif tool_state.mode == 'pattern':
                    if tool_state.start_point is None:
                        tool_state.start_point = (cursor_x, cursor_y)
                    else:
                        if tool_state.pattern:
                            undo_stack.push(map_data)
                            draw_pattern_rectangle(map_data, tool_state.start_point[0], tool_state.start_point[1],
                                                 cursor_x, cursor_y, tool_state.pattern, map_width, map_height)
                            tool_state.dirty = True
                            tool_state.edits_since_save += 1
                        tool_state.start_point = None

            elif action == 'flood_fill':
                undo_stack.push(map_data)
                old_char = map_data[cursor_y][cursor_x]
                flood_fill(map_data, cursor_x, cursor_y, old_char, selected_char, map_width, map_height)
                tool_state.start_point = None
                tool_state.dirty = True
                tool_state.edits_since_save += 1

            elif action == 'line_tool':
                tool_state.mode = 'line'
                tool_state.start_point = None

            elif action == 'rect_tool':
                tool_state.mode = 'rect'
                tool_state.start_point = None

            elif action == 'circle_tool':
                tool_state.mode = 'circle'
                tool_state.start_point = None

            elif action == 'pattern_tool':
                tool_state.mode = 'pattern'
                tool_state.start_point = None
                if tool_state.pattern is None:
                    tool_state.pattern = menu_define_pattern(stdscr, tile_chars, tile_colors)

            elif action == 'define_pattern':
                tool_state.pattern = menu_define_pattern(stdscr, tile_chars, tile_colors)

            elif action == 'define_brush':
                tool_state.brush_shape = menu_define_brush(stdscr)

            elif action == 'cycle_tile':
                selected_idx = (selected_idx + 1) % len(tile_chars)
                selected_char = tile_chars[selected_idx]

            elif action == 'pick_tile':
                picked = menu_pick_tile(stdscr, tile_chars, tile_colors, color_pairs)
                if picked is not None:
                    selected_char = picked
                    selected_idx = tile_chars.index(picked)

            elif action == 'select_start':
                if selection_start is None:
                    selection_start = (cursor_x, cursor_y)
                    selection_end = None
                elif selection_end is None:
                    selection_end = (cursor_x, cursor_y)
                    x0, y0 = selection_start
                    x1, y1 = selection_end
                    selection_start = (min(x0, x1), min(y0, y1))
                    selection_end = (max(x0, x1), max(y0, y1))
                else:
                    selection_start = (cursor_x, cursor_y)
                    selection_end = None

            elif action == 'clear_selection':
                selection_start = None
                selection_end = None

            elif action == 'copy_selection':
                if selection_start and selection_end:
                    x0, y0 = selection_start
                    x1, y1 = selection_end
                    clipboard = []
                    for y in range(y0, y1 + 1):
                        row = []
                        for x in range(x0, x1 + 1):
                            row.append(map_data[y][x])
                        clipboard.append(row)

            elif action == 'paste_selection':
                if clipboard:
                    undo_stack.push(map_data)
                    overflow = False
                    for dy, row in enumerate(clipboard):
                        for dx, ch in enumerate(row):
                            ny = cursor_y + dy
                            nx = cursor_x + dx
                            if 0 <= ny < map_height and 0 <= nx < map_width:
                                map_data[ny][nx] = ch
                            else:
                                overflow = True
                    if overflow:
                        stdscr.addstr(status_y + 2, 0, "Part of paste was outside map. Press any key...")
                        stdscr.clrtoeol()
                        stdscr.refresh()
                        stdscr.getch()
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1

            elif action == 'rotate_selection':
                if clipboard:
                    clipboard = rotate_selection_90(clipboard)

            elif action == 'flip_h':
                if clipboard:
                    clipboard = flip_selection_horizontal(clipboard)

            elif action == 'flip_v':
                if clipboard:
                    clipboard = flip_selection_vertical(clipboard)

            elif action == 'clear_area':
                if selection_start and selection_end:
                    undo_stack.push(map_data)
                    x0, y0 = selection_start
                    x1, y1 = selection_end
                    for y in range(y0, y1 + 1):
                        for x in range(x0, x1 + 1):
                            map_data[y][x] = '.'
                    selection_start = None
                    selection_end = None
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1

            elif action == 'undo':
                result = undo_stack.undo(map_data)
                if result:
                    map_data[:] = result
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1
                    selection_start = None
                    selection_end = None

            elif action == 'redo':
                result = undo_stack.redo(map_data)
                if result:
                    map_data[:] = result
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1
                    selection_start = None
                    selection_end = None

            elif action == 'new_map':
                new_data, new_w, new_h = menu_new_map(stdscr, view_width, view_height)
                if new_data:
                    undo_stack.push(map_data)
                    map_data[:] = new_data
                    map_width, map_height = new_w, new_h
                    camera_x = max(0, min(camera_x, map_width - view_width))
                    camera_y = max(0, min(camera_y, map_height - view_height))
                    cursor_x = max(0, min(cursor_x, map_width - 1))
                    cursor_y = max(0, min(cursor_y, map_height - 1))
                    selection_start = None
                    selection_end = None
                    tool_state.dirty = False

            elif action == 'save_map':
                if menu_save_map(stdscr, map_data):
                    tool_state.dirty = False

            elif action == 'load_map':
                loaded, w, h = menu_load_map(stdscr, view_width, view_height)
                if loaded:
                    undo_stack.push(map_data)
                    map_data[:] = loaded
                    map_width, map_height = w, h
                    camera_x = max(0, min(camera_x, map_width - view_width))
                    camera_y = max(0, min(camera_y, map_height - view_height))
                    cursor_x = max(0, min(cursor_x, map_width - 1))
                    cursor_y = max(0, min(cursor_y, map_height - 1))
                    selection_start = None
                    selection_end = None
                    tool_state.dirty = False

            elif action == 'resize_map':
                nm, nw, nh = menu_resize_map(stdscr, map_data, map_width, map_height, view_width, view_height)
                if nm:
                    undo_stack.push(map_data)
                    map_data[:] = nm
                    map_width, map_height = nw, nh
                    camera_x = max(0, min(camera_x, map_width - view_width))
                    camera_y = max(0, min(camera_y, map_height - view_height))
                    cursor_x = max(0, min(cursor_x, map_width - 1))
                    cursor_y = max(0, min(cursor_y, map_height - 1))
                    selection_start = None
                    selection_end = None
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1

            elif action == 'map_rotate':
                undo_stack.push(map_data)
                new_data = rotate_selection_90(map_data)
                map_data[:] = new_data
                map_width, map_height = map_height, map_width
                camera_x = max(0, min(camera_x, map_width - view_width))
                camera_y = max(0, min(camera_y, map_height - view_height))
                cursor_x = max(0, min(cursor_x, map_width - 1))
                cursor_y = max(0, min(cursor_y, map_height - 1))
                tool_state.dirty = True
                tool_state.edits_since_save += 1

            elif action == 'map_flip_h':
                undo_stack.push(map_data)
                map_data[:] = flip_selection_horizontal(map_data)
                tool_state.dirty = True
                tool_state.edits_since_save += 1

            elif action == 'map_flip_v':
                undo_stack.push(map_data)
                map_data[:] = flip_selection_vertical(map_data)
                tool_state.dirty = True
                tool_state.edits_since_save += 1

            elif action == 'map_shift_up':
                undo_stack.push(map_data)
                map_data[:] = shift_map(map_data, 0, -1)
                tool_state.dirty = True
                tool_state.edits_since_save += 1

            elif action == 'map_shift_down':
                undo_stack.push(map_data)
                map_data[:] = shift_map(map_data, 0, 1)
                tool_state.dirty = True
                tool_state.edits_since_save += 1

            elif action == 'map_shift_left':
                undo_stack.push(map_data)
                map_data[:] = shift_map(map_data, -1, 0)
                tool_state.dirty = True
                tool_state.edits_since_save += 1

            elif action == 'map_shift_right':
                undo_stack.push(map_data)
                map_data[:] = shift_map(map_data, 1, 0)
                tool_state.dirty = True
                tool_state.edits_since_save += 1

            elif action == 'set_seed':
                tool_state.seed = menu_set_seed(stdscr, tool_state.seed)
                random.seed(tool_state.seed)

            elif action == 'export_image':
                menu_export_image(stdscr, map_data, tile_colors)

            elif action == 'define_tiles':
                menu_define_tiles(stdscr, tile_chars, tile_colors)
                color_pairs = init_color_pairs(tile_colors)
                if selected_idx >= len(tile_chars):
                    selected_idx = 0
                selected_char = tile_chars[selected_idx]

            elif action == 'random_gen':
                if menu_random_generation(stdscr, map_data, map_width, map_height, tile_chars, tool_state.seed):
                    undo_stack.push(map_data)
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1

            elif action == 'perlin_noise':
                if menu_perlin_generation(stdscr, map_data, map_width, map_height, tile_chars, tool_state.seed):
                    undo_stack.push(map_data)
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1

            elif action == 'voronoi':
                if menu_voronoi_generation(stdscr, map_data, map_width, map_height, tile_chars, tool_state.seed):
                    undo_stack.push(map_data)
                    tool_state.dirty = True
                    tool_state.edits_since_save += 1

            elif action == 'replace_all':
                curses.echo()
                curses.curs_set(1)
                stdscr.addstr(status_y + 2, 0, "Replace tile: ")
                stdscr.clrtoeol()
                stdscr.refresh()
                old_char = stdscr.getstr().decode().strip()

                if len(old_char) == 1:
                    stdscr.addstr(status_y + 2, 0, "With tile: ")
                    stdscr.clrtoeol()
                    stdscr.refresh()
                    new_char = stdscr.getstr().decode().strip()

                    if len(new_char) == 1:
                        undo_stack.push(map_data)
                        count = 0
                        for y in range(map_height):
                            for x in range(map_width):
                                if map_data[y][x] == old_char[0]:
                                    map_data[y][x] = new_char[0]
                                    count += 1
                        stdscr.addstr(status_y + 2, 0, f"Replaced {count} tiles. Press any key...")
                        stdscr.clrtoeol()
                        stdscr.refresh()
                        stdscr.getch()
                        tool_state.dirty = True
                        tool_state.edits_since_save += 1

                curses.noecho()
                curses.curs_set(0)

            elif action == 'statistics':
                menu_statistics(stdscr, map_data, map_width, map_height)

            elif action == 'show_help':
                draw_help_overlay(stdscr, bindings)

            elif action == 'edit_controls':
                menu_controls(stdscr, bindings)
                key_map = build_key_map(bindings)

            break

def menu_main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.nodelay(False)

    parser = argparse.ArgumentParser(description='Advanced Terminal Map Editor')
    parser.add_argument('--view-width', type=int, default=60)
    parser.add_argument('--view-height', type=int, default=30)
    args = parser.parse_args()

    max_y, max_x = stdscr.getmaxyx()
    view_width = min(args.view_width, max_x)
    view_height = min(args.view_height, max_y - 3)

    default_tile_colors = {
        '.': 'white', '#': 'red', '~': 'cyan', 'T': 'green',
        'G': 'yellow', '+': 'yellow', '*': 'magenta', '@': 'blue',
    }

    tile_colors = {ch: parse_color_name(col) for ch, col in default_tile_colors.items()}
    tile_chars = list(tile_colors.keys())
    bindings = load_config()

    macros = {}
    tiling_rules = {}

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "=== ADVANCED MAP EDITOR ===")
        stdscr.addstr(2, 0, "1. New Map")
        stdscr.addstr(3, 0, "2. Load Map")

        autosave_name = "autosave_map.txt"
        has_autosave = os.path.exists(autosave_name)
        if has_autosave:
            stdscr.addstr(4, 0, "R. Restore from Autosave", curses.A_BOLD)

        stdscr.addstr(5, 0, "3. Define Custom Tiles")
        stdscr.addstr(6, 0, "4. Macro Manager")
        stdscr.addstr(7, 0, "5. Edit Controls")
        stdscr.addstr(8, 0, "6. Auto-Tiling Manager")
        stdscr.addstr(9, 0, "7. Quit")
        stdscr.addstr(11, 0, "Features: Fill, Line, Rect, Circle, Undo/Redo, Copy/Paste,")
        stdscr.addstr(12, 0, "          Rotate, Flip, Random Gen, Perlin Noise, Voronoi,")
        stdscr.addstr(13, 0, "          Macro Recording, Custom Brushes, PNG Export")
        stdscr.addstr(15, 0, "Select option (1-7): ")
        stdscr.refresh()

        key = stdscr.getch()

        if key == ord('1'):
            map_data, map_width, map_height = menu_new_map(stdscr, view_width, view_height)
            if map_data:
                editor(stdscr, map_data, map_width, map_height, view_width, view_height,
                       tile_chars, tile_colors, bindings, macros=macros, tiling_rules=tiling_rules)

        elif key == ord('2'):
            map_data, map_width, map_height = menu_load_map(stdscr, view_width, view_height)
            if map_data:
                editor(stdscr, map_data, map_width, map_height, view_width, view_height,
                       tile_chars, tile_colors, bindings, macros=macros, tiling_rules=tiling_rules)

        elif key in (ord('r'), ord('R')) and has_autosave:
            try:
                with open(autosave_name, 'r') as f:
                    lines = [line.rstrip('\n') for line in f]
                if lines:
                    w = max(len(line) for line in lines)
                    h = len(lines)
                    rw = max(w, view_width)
                    rh = max(h, view_height)
                    map_data = [['.' for _ in range(rw)] for _ in range(rh)]
                    for y, line in enumerate(lines):
                        for x, ch in enumerate(line):
                            map_data[y][x] = ch

                    editor(stdscr, map_data, rw, rh, view_width, view_height,
                           tile_chars, tile_colors, bindings, macros=macros, tiling_rules=tiling_rules)
            except:
                stdscr.addstr(15, 0, "Failed to restore autosave. Press any key...")
                stdscr.getch()

        elif key == ord('3'):
            menu_define_tiles(stdscr, tile_chars, tile_colors)

        elif key == ord('4'):
            dummy_state = ToolState(macros=macros)
            menu_macros(stdscr, dummy_state)

        elif key == ord('5'):
            menu_controls(stdscr, bindings)

        elif key == ord('6'):
            dummy_state = ToolState(tiling_rules=tiling_rules)
            menu_define_autotiling(stdscr, dummy_state, tile_chars)

        elif key in (ord('7'), ord('q'), ord('Q')):
            break

if __name__ == '__main__':
    try:
        curses.wrapper(menu_main)
    except KeyboardInterrupt:
        pass
