from collections import Counter
import curses
import os
import random
import numpy as np
from utils import get_key_name, parse_color_name, get_user_input
from core import COLOR_MAP
from map_io import save_config, export_to_image
from ui import invalidate_cache
from generation import cellular_automata_cave, perlin_noise_generation, voronoi_generation

def build_key_map(bindings):
    key_map = {}
    for action, key in bindings.items():
        if key not in key_map:
            key_map[key] = []
        key_map[key].append(action)
    return key_map

def get_map_statistics(map_obj):
    return Counter(map_obj.data.flatten())

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
                from map_io import load_config
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

def menu_statistics(stdscr, map_obj):
    stats = get_map_statistics(map_obj)
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

def menu_save_map(stdscr, map_obj):
    max_y = stdscr.getmaxyx()[0]
    filename = get_user_input(stdscr, max_y-2, 0, "Save map as: ")

    if filename and os.path.exists(filename):
        stdscr.addstr(max_y-1, 0, f"File exists. Overwrite? (y/n): ")
        stdscr.clrtoeol()
        stdscr.refresh()
        confirm = stdscr.getch()
        if confirm not in (ord('y'), ord('Y')):
            return False

    success = False
    if filename:
        try:
            with open(filename, 'w') as f:
                for row in map_obj.data:
                    f.write(''.join(row) + '\n')
            stdscr.addstr(max_y-1, 0, f"Saved to {filename}. Press any key...")
            success = True
        except Exception as e:
            stdscr.addstr(max_y-1, 0, f"Error: {str(e)[:30]}. Press any key...")
        stdscr.clrtoeol()
        stdscr.refresh()
        stdscr.getch()
        invalidate_cache()

    return success

def menu_load_map(stdscr, view_width, view_height):
    from core import Map
    max_y = stdscr.getmaxyx()[0]
    filename = get_user_input(stdscr, max_y-2, 0, "Load map from: ")

    if not filename or not os.path.exists(filename):
        return None

    try:
        with open(filename, 'r') as f:
            lines = [line.rstrip('\n') for line in f]

        if not lines:
            return None

        width = max(len(line) for line in lines) if lines else view_width
        height = len(lines)

        if height < view_height: height = view_height
        if width < view_width: width = view_width

        map_obj = Map(width, height)

        for y, line in enumerate(lines):
            for x, ch in enumerate(line):
                map_obj.set(x, y, ch)

        map_obj.dirty = False
        return map_obj
    except:
        return None

def menu_export_image(stdscr, map_obj, tile_colors):
    max_y = stdscr.getmaxyx()[0]
    filename = get_user_input(stdscr, max_y-3, 0, "Export as (.png/.csv): ")

    if filename:
        if not filename.endswith('.png') and not filename.endswith('.csv'):
            filename += '.png'

        if filename.endswith('.png'):
            tile_size_input = get_user_input(stdscr, max_y-2, 0, "Tile size in pixels (default 8): ")
            tile_size = int(tile_size_input) if tile_size_input else 8

            try:
                export_to_image(map_obj.data, tile_colors, filename, tile_size)
                stdscr.addstr(max_y-1, 0, f"Exported PNG to {filename}. Press any key...")
            except Exception as e:
                stdscr.addstr(max_y-1, 0, f"Error: {str(e)[:30]}. Press any key...")
        elif filename.endswith('.csv'):
            try:
                with open(filename, 'w') as f:
                    for row in map_obj.data:
                        f.write(','.join(row) + '\n')
                stdscr.addstr(max_y-1, 0, f"Exported CSV to {filename}. Press any key...")
            except Exception as e:
                stdscr.addstr(max_y-1, 0, f"Error: {str(e)[:30]}. Press any key...")

        stdscr.clrtoeol()
        stdscr.refresh()
        stdscr.getch()
        invalidate_cache()


def menu_new_map(stdscr, view_width, view_height):
    from core import Map
    stdscr.clear()
    stdscr.addstr(0, 0, "New Map")

    w = view_width
    while True:
        inp = get_user_input(stdscr, 2, 0, f"Map width (min {view_width}): ")
        try:
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
        inp = get_user_input(stdscr, 3, 0, f"Map height (min {view_height}): ")
        try:
            if not inp:
                h = view_height
                break
            val = int(inp)
            if val >= view_height:
                h = val
                break
        except ValueError:
            pass

    border_input = get_user_input(stdscr, 4, 0, "Border char (default #, leave empty/'.' for none): ")

    if not border_input or border_input == '.':
        border_char = None
    else:
        border_char = border_input[0]

    map_obj = Map(w, h)

    if border_char:
        for x in range(w):
            map_obj.set(x, 0, border_char)
            map_obj.set(x, h-1, border_char)
        for y in range(h):
            map_obj.set(0, y, border_char)
            map_obj.set(w-1, y, border_char)
        map_obj.dirty = False

    return map_obj

def menu_define_tiles(stdscr, tile_chars, tile_colors):
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
            ch_in = get_user_input(stdscr, prompt_y + 2, 0, "Enter tile character: ")
            if len(ch_in) == 1:
                ch = ch_in
                col = get_user_input(stdscr, prompt_y + 2, 0, f"Color for '{ch}' (red, green, etc.): ").lower()
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
                col = get_user_input(stdscr, prompt_y + 2, 0, f"New color for '{ch}': ").lower()
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

    return

def menu_random_generation(stdscr, map_obj, seed=None):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.addstr(0, 0, "=== CELLULAR AUTOMATA GENERATION ===")

    try:
        inp = get_user_input(stdscr, 2, 0, "Iterations (3-10, default 5): ")
        iterations = int(inp or "5")
        iterations = max(3, min(10, iterations))
    except:
        iterations = 5

    wall_in = get_user_input(stdscr, 3, 0, "Wall char (default #): ")
    wall = wall_in[0] if wall_in else '#'

    floor_in = get_user_input(stdscr, 4, 0, "Floor char (default .): ")
    floor = floor_in[0] if floor_in else '.'

    cellular_automata_cave(map_obj, iterations, wall, floor, seed)
    return True

def menu_perlin_generation(stdscr, map_obj, tile_chars, seed=0):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.addstr(0, 0, "=== PERLIN NOISE GENERATION ===")

    try:
        inp = get_user_input(stdscr, 2, 0, "Scale (1-50, default 10): ")
        scale = float(inp or "10")
        scale = max(1, min(50, scale))
    except:
        scale = 10.0

    try:
        inp = get_user_input(stdscr, 3, 0, "Octaves (1-8, default 4): ")
        octaves = int(inp or "4")
        octaves = max(1, min(8, octaves))
    except:
        octaves = 4

    try:
        inp = get_user_input(stdscr, 4, 0, "Persistence (0.1-1.0, default 0.5): ")
        persistence = float(inp or "0.5")
        persistence = max(0.1, min(1.0, persistence))
    except:
        persistence = 0.5

    try:
        perlin_noise_generation(map_obj, tile_chars, scale, octaves, persistence, seed)
        return True
    except ImportError:
        stdscr.addstr(4, 0, "Error: 'noise' library not installed. Install with: pip install noise")
        stdscr.addstr(5, 0, "Press any key to continue...")
        stdscr.refresh()
        stdscr.getch()
        return False

def menu_voronoi_generation(stdscr, map_obj, tile_chars, seed=None):
    curses.curs_set(0)
    stdscr.clear()
    stdscr.addstr(0, 0, "=== VORONOI DIAGRAM GENERATION ===")

    try:
        inp = get_user_input(stdscr, 2, 0, "Number of regions (5-50, default 20): ")
        num_points = int(inp or "20")
        num_points = max(5, min(50, num_points))
    except:
        num_points = 20

    voronoi_generation(map_obj, tile_chars, num_points, seed)
    return True

def menu_resize_map(stdscr, map_obj, view_width, view_height):
    from core import Map
    stdscr.clear()
    stdscr.addstr(0, 0, "=== RESIZE MAP ===")

    w = map_obj.width
    while True:
        inp = get_user_input(stdscr, 2, 0, f"New width (current {map_obj.width}, min {view_width}): ")
        try:
            if not inp:
                w = map_obj.width
                break
            val = int(inp)
            if val >= view_width:
                w = val
                break
        except ValueError:
            pass

    h = map_obj.height
    while True:
        inp = get_user_input(stdscr, 3, 0, f"New height (current {map_obj.height}, min {view_height}): ")
        try:
            if not inp:
                h = map_obj.height
                break
            val = int(inp)
            if val >= view_height:
                h = val
                break
        except ValueError:
            pass

    fill_input = get_user_input(stdscr, 4, 0, "Fill char (default .): ")
    fill_char = fill_input[0] if fill_input else '.'

    if w == map_obj.width and h == map_obj.height:
        return None

    new_map = Map(w, h, fill_char=fill_char)
    
    # Copy old content into the top-left of the new map using numpy slicing
    copy_h = min(h, map_obj.height)
    copy_w = min(w, map_obj.width)
    new_map.data[:copy_h, :copy_w] = map_obj.data[:copy_h, :copy_w]

    return new_map

def menu_set_seed(stdscr, current_seed):
    stdscr.clear()
    stdscr.addstr(0, 0, "=== SET RANDOM SEED ===")
    stdscr.addstr(2, 0, f"Current seed: {current_seed}")
    
    inp = get_user_input(stdscr, 3, 0, "New seed (integer): ")

    new_seed = current_seed
    try:
        if inp:
            new_seed = int(inp)
    except:
        pass

    return new_seed

def menu_autosave_settings(stdscr, tool_state):
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
                val_str = get_user_input(stdscr, 9, 0, "Enter interval (minutes, 1-60): ")
                try:
                    val = int(val_str)
                    tool_state.autosave_interval = max(1, min(60, val))
                except: pass
            else:
                val_str = get_user_input(stdscr, 9, 0, "Enter edit threshold (1-500): ")
                try:
                    val = int(val_str)
                    tool_state.autosave_edits_threshold = max(1, min(500, val))
                except: pass
        elif key == ord('4'):
            name = get_user_input(stdscr, 9, 0, "Enter filename: ")
            if name: tool_state.autosave_filename = name

    return

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
            name = get_user_input(stdscr, max_y - 2, 0, "Enter macro name: ")
            if name:
                actions_str = get_user_input(stdscr, max_y - 1, 0, "Enter actions (comma separated, e.g. move_cursor_right,place_tile): ")
                if actions_str:
                    actions = [a.strip() for a in actions_str.split(',')]
                    tool_state.macros[name] = actions

        elif key in (ord('r'), ord('R')):
            name = get_user_input(stdscr, max_y - 2, 0, "Enter macro name to remove: ")
            if name in tool_state.macros:
                del tool_state.macros[name]

        elif key in (ord('l'), ord('L')):
            name = get_user_input(stdscr, max_y - 2, 0, "Enter macro name to list: ")
            if name in tool_state.macros:
                stdscr.clear()
                stdscr.addstr(0, 0, f"=== Actions for {name} ===")
                for i, act in enumerate(tool_state.macros[name]):
                    if i > max_y - 5: break
                    stdscr.addstr(i + 2, 2, act)
                stdscr.addstr(max_y - 1, 0, "Press any key...")
                stdscr.refresh()
                stdscr.getch()

    return

def menu_define_autotiling(stdscr, tool_state, tile_chars):
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
            base = get_user_input(stdscr, max_y - 2, 0, "Enter base tile character: ")
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
                    prompt = f"Mask {mask:2} ({binary} [LDRU]): Variant char (blank to skip): "
                    curr = tool_state.tiling_rules[base].get(mask, "")
                    if curr: prompt += f" (current: {curr})"
                    
                    variant = get_user_input(stdscr, row, 2, prompt)
                    if variant:
                        tool_state.tiling_rules[base][mask] = variant[0]

        elif key in (ord('r'), ord('R')):
            base = get_user_input(stdscr, max_y - 2, 0, "Enter base tile to remove: ")
            if base in tool_state.tiling_rules:
                del tool_state.tiling_rules[base]

    return

def menu_define_brush(stdscr):
    stdscr.clear()
    stdscr.addstr(0, 0, "=== DEFINE CUSTOM BRUSH ===")
    inp = get_user_input(stdscr, 2, 0, "Brush size (odd number, 1-7, default 3): ")
    try:
        size = int(inp) if inp else 3
    except:
        size = 3
    size = max(1, min(7, size))
    if size % 2 == 0: size += 1

    brush = [[False for _ in range(size)] for _ in range(size)]

    stdscr.addstr(4, 0, f"Design your {size}x{size} brush.")
    stdscr.addstr(5, 0, "Use Arrows to move, SPACE to toggle, ENTER to save, Q to cancel.")
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
            curses.curs_set(0)
            return brush
        elif key in (ord('q'), ord('Q'), 27):
            curses.curs_set(0)
            return None

def menu_define_pattern(stdscr, tile_chars, tile_colors):
    stdscr.clear()
    stdscr.addstr(0, 0, "=== DEFINE PATTERN ===")
    size_str = get_user_input(stdscr, 2, 0, "Pattern size (e.g. 2 for 2x2, 3 for 3x3, max 5): ")
    try:
        size = int(size_str) if size_str else 2
    except:
        size = 2

    size = max(1, min(5, size))
    pattern = [['.' for _ in range(size)] for _ in range(size)]

    for r in range(size):
        for c in range(size):
            ch = get_user_input(stdscr, 4 + r, 0, f"Char for ({r},{c}): ")
            pattern[r][c] = ch[0] if ch else '.'

    return pattern
