import curses
import sys
import os
import time
import random
import argparse
import shutil
from core import Map, UndoStack, ToolState, EditorSession, DEFAULT_VIEW_WIDTH, DEFAULT_VIEW_HEIGHT, DEFAULT_TILE_COLORS
from utils import parse_color_name, get_distance, get_user_input
from map_io import load_config
from ui import init_color_pairs, draw_map, draw_status, draw_help_overlay, draw_tile_palette
from drawing import place_tile_at, flood_fill, draw_line, draw_rectangle, draw_circle, draw_pattern_rectangle
from menus import build_key_map, menu_controls, menu_pick_tile, menu_statistics, menu_save_map, menu_load_map, menu_export_image, menu_new_map, menu_define_tiles, menu_random_generation, menu_perlin_generation, menu_voronoi_generation, menu_resize_map, menu_set_seed, menu_autosave_settings, menu_editor_pause, menu_macros, menu_define_autotiling, menu_define_brush, menu_define_pattern
from actions import get_action_dispatcher

def editor(stdscr, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros=None, tiling_rules=None):
    session = EditorSession(map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
    session.color_pairs = init_color_pairs(tile_colors)
    session.map_obj.undo_stack = session.undo_stack
    
    key_map = build_key_map(bindings)
    dispatcher = get_action_dispatcher()

    while session.running:
        max_y, max_x = stdscr.getmaxyx()
        if curses.is_term_resized(max_y, max_x):
            try:
                cols, lines = shutil.get_terminal_size()
                curses.resizeterm(lines, cols)
            except: pass
            session.view_width, session.view_height = min(view_width, max_x), min(view_height, max_y - 3)
            session.camera_x = max(0, min(session.camera_x, session.map_obj.width - session.view_width))
            session.camera_y = max(0, min(session.camera_y, session.map_obj.height - session.view_height))
            stdscr.clear()
            stdscr.refresh()

        stdscr.clear()
        session.status_y = draw_map(stdscr, session.map_obj.data, session.camera_x, session.camera_y, session.view_width, session.view_height,
                                   session.cursor_x, session.cursor_y, session.selected_char, session.color_pairs,
                                   session.selection_start, session.selection_end, session.tool_state)

        draw_status(stdscr, session.status_y, session.map_obj.width, session.map_obj.height, session.camera_x, session.camera_y,
                   session.cursor_x, session.cursor_y, session.selected_char, session.tool_state, session.undo_stack, session.bindings)

        if session.tool_state.show_palette:
            draw_tile_palette(stdscr, session.tile_chars, session.color_pairs, session.selected_char)

        stdscr.refresh()
        
        ts = session.tool_state
        timeout_ms = -1
        if ts.autosave_enabled and ts.autosave_mode == 'time':
            remaining = (ts.autosave_interval * 60) - (time.time() - ts.last_autosave_time)
            if remaining <= 0: timeout_ms = 0
            else: timeout_ms = int(remaining * 1000)
            
        stdscr.timeout(timeout_ms)
        key = stdscr.getch()

        # Handle autosave
        if ts.autosave_enabled and session.map_obj.dirty:
            if ts.autosave_mode == 'time':
                if time.time() - ts.last_autosave_time > ts.autosave_interval * 60:
                    menu_save_map(stdscr, session.map_obj) # Use menu save for simplicity
                    ts.last_autosave_time, ts.edits_since_save = time.time(), 0
                    stdscr.timeout(-1) # Reset timeout
            elif ts.autosave_mode == 'edits':
                if ts.edits_since_save >= ts.autosave_edits_threshold:
                    menu_save_map(stdscr, session.map_obj)
                    ts.last_autosave_time, ts.edits_since_save = time.time(), 0

        if key == -1: continue
        
        # ESC clears tool state
        if key == 27:
            if ts.start_point: ts.start_point = None
            elif session.selection_start: session.selection_start, session.selection_end = None, None
            else: ts.mode = 'place'
            continue

        # Get actions for this key (COPY the list to avoid dictionary corruption)
        pending_actions = list(key_map.get(key, []))
        
        while pending_actions:
            action = pending_actions.pop(0)
            
            if ts.recording and action not in ('macro_record_toggle', 'macro_play', 'editor_menu'):
                ts.current_macro_actions.append(action)

            # Dispatch known actions
            if action in dispatcher:
                dispatcher[action](session, stdscr, action)
            
            # Special actions not yet fully dispatched
            elif action == 'macro_record_toggle':
                if ts.recording:
                    ts.recording = False
                    name = get_user_input(stdscr, session.status_y + 2, 0, "Enter name for macro: ")
                    if name: ts.macros[name] = list(ts.current_macro_actions)
                else:
                    ts.recording, ts.current_macro_actions = True, []
            elif action == 'macro_play':
                name = get_user_input(stdscr, session.status_y + 2, 0, "Enter macro name to play: ")
                if name in ts.macros:
                    # Prepend macro actions to current queue
                    pending_actions = list(ts.macros[name]) + pending_actions
            elif action == 'toggle_snap':
                inp = get_user_input(stdscr, session.status_y + 2, 0, "Enter snap size: ")
                try: ts.snap_size = int(inp or "1")
                except: pass
            elif action == 'toggle_palette': ts.show_palette = not ts.show_palette
            elif action == 'toggle_autotile':
                if ts.auto_tiling: ts.auto_tiling = False
                elif session.selected_char in ts.tiling_rules: ts.auto_tiling = True
                else:
                    stdscr.addstr(session.status_y + 2, 0, f"No rules for '{session.selected_char}'!")
                    stdscr.getch()
            elif action == 'resize_map':
                res = menu_resize_map(stdscr, session.map_obj, session.view_width, session.view_height)
                if res:
                    session.map_obj = res
                    session.map_obj.undo_stack = session.undo_stack # Carry over stack
            elif action == 'set_seed':
                ts.seed = menu_set_seed(stdscr, ts.seed)
                random.seed(ts.seed)
            elif action == 'replace_all':
                if 'replace_all' in dispatcher:
                    dispatcher['replace_all'](session, stdscr, action)
            elif action == 'statistics': menu_statistics(stdscr, session.map_obj)
            elif action == 'show_help': draw_help_overlay(stdscr, session.bindings)
            elif action == 'edit_controls':
                menu_controls(stdscr, session.bindings)
                key_map = build_key_map(session.bindings) # Refresh keymap
            elif action == 'export_image':
                from menus import menu_export_image
                menu_export_image(stdscr, session.map_obj, session.tile_colors)
            elif action in ('line_tool', 'rect_tool', 'circle_tool', 'pattern_tool'):
                ts.mode, ts.start_point = action.split('_')[0], None
                if action == 'pattern_tool' and ts.pattern is None:
                    ts.pattern = menu_define_pattern(stdscr, session.tile_chars, session.tile_colors)
            elif action == 'define_pattern':
                ts.pattern = menu_define_pattern(stdscr, session.tile_chars, session.tile_colors)
            elif action == 'define_brush':
                ts.brush_shape = menu_define_brush(stdscr)

def menu_main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    stdscr.nodelay(False)

    parser = argparse.ArgumentParser(description='Advanced Terminal Map Editor')
    parser.add_argument('--view-width', type=int, default=60)
    parser.add_argument('--view-height', type=int, default=30)
    args = parser.parse_args()

    max_y, max_x = stdscr.getmaxyx()
    view_width, view_height = min(args.view_width, max_x), min(args.view_height, max_y - 3)
    tile_colors = {ch: parse_color_name(col) for ch, col in DEFAULT_TILE_COLORS.items()}
    tile_chars, bindings = list(tile_colors.keys()), load_config()
    macros, tiling_rules = {}, {}

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "=== ADVANCED MAP EDITOR ===")
        stdscr.addstr(2, 0, "1. New Map")
        stdscr.addstr(3, 0, "2. Load Map")
        autosave_name = "autosave_map.txt"
        if os.path.exists(autosave_name): stdscr.addstr(4, 0, "R. Restore from Autosave", curses.A_BOLD)
        stdscr.addstr(5, 0, "3. Define Custom Tiles")
        stdscr.addstr(6, 0, "4. Macro Manager")
        stdscr.addstr(7, 0, "5. Edit Controls")
        stdscr.addstr(8, 0, "6. Auto-Tiling Manager")
        stdscr.addstr(9, 0, "7. Quit")
        stdscr.addstr(15, 0, "Select option (1-7): ")
        stdscr.refresh()

        key = stdscr.getch()
        if key == ord('1'):
            map_obj = menu_new_map(stdscr, view_width, view_height)
            if map_obj: editor(stdscr, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
        elif key == ord('2'):
            map_obj = menu_load_map(stdscr, view_width, view_height)
            if map_obj: editor(stdscr, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
        elif key in (ord('r'), ord('R')) and os.path.exists(autosave_name):
            try:
                with open(autosave_name, 'r') as f: lines = [l.rstrip('\n') for l in f]
                if lines:
                    w, h = max(len(l) for l in lines), len(lines)
                    rw, rh = max(w, view_width), max(h, view_height)
                    map_obj = Map(rw, rh)
                    for y, line in enumerate(lines):
                        for x, ch in enumerate(line): map_obj.set(x, y, ch)
                    editor(stdscr, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
            except: pass
        elif key == ord('3'): menu_define_tiles(stdscr, tile_chars, tile_colors)
        elif key == ord('4'): menu_macros(stdscr, ToolState(macros=macros))
        elif key == ord('5'): menu_controls(stdscr, bindings)
        elif key == ord('6'): menu_define_autotiling(stdscr, ToolState(tiling_rules=tiling_rules), tile_chars)
        elif key in (ord('7'), ord('q'), ord('Q')): break

if __name__ == '__main__':
    try: curses.wrapper(menu_main)
    except KeyboardInterrupt: pass
