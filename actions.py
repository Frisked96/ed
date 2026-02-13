import curses
import sys
import random
from utils import get_distance, rotate_selection_90, flip_selection_horizontal, flip_selection_vertical, shift_map, get_user_input, get_user_confirmation
from drawing import place_tile_at, flood_fill, draw_line, draw_rectangle, draw_circle, draw_pattern_rectangle
from menus import menu_save_map, menu_load_map, menu_macros, menu_define_autotiling, menu_autosave_settings, menu_editor_pause, menu_define_pattern, menu_define_brush, menu_pick_tile, menu_new_map, menu_resize_map, menu_set_seed, menu_statistics, menu_controls, menu_random_generation, menu_perlin_generation, menu_voronoi_generation, menu_define_tiles
from core import Map

def handle_quit(session, stdscr, action=None):
    if session.map_obj.dirty:
        if not get_user_confirmation(stdscr, session.status_y + 2, 0, "Unsaved! Quit anyway? (y/n): "):
            return
    session.running = False

def handle_editor_menu(session, stdscr, action=None):
    choice = menu_editor_pause(stdscr)
    if choice == "Save Map":
        if menu_save_map(stdscr, session.map_obj):
            session.map_obj.dirty = False
    elif choice == "Load Map":
        loaded = menu_load_map(stdscr, session.view_width, session.view_height)
        if loaded:
            session.map_obj.push_undo()
            session.map_obj = loaded
            session.camera_x, session.camera_y = 0, 0
            session.cursor_x, session.cursor_y = 0, 0
    elif choice == "Macro Manager":
        menu_macros(stdscr, session.tool_state)
    elif choice == "Auto-Tiling Manager":
        menu_define_autotiling(stdscr, session.tool_state, session.tile_chars)
    elif choice == "Autosave Settings":
        menu_autosave_settings(stdscr, session.tool_state)
    elif choice == "Exit to Main Menu":
        if session.map_obj.dirty:
            if get_user_confirmation(stdscr, session.status_y + 2, 0, "Unsaved! Exit anyway? (y/n): "):
                session.running = False
        else: session.running = False
    elif choice == "Quit Editor":
        sys.exit(0)

def handle_move_view(session, stdscr, action=None):
    if action == 'move_view_up': session.camera_y = max(0, session.camera_y - 1)
    elif action == 'move_view_down': session.camera_y = min(session.map_obj.height - session.view_height, session.camera_y + 1)
    elif action == 'move_view_left': session.camera_x = max(0, session.camera_x - 1)
    elif action == 'move_view_right': session.camera_x = min(session.map_obj.width - session.view_width, session.camera_x + 1)

def handle_move_cursor(session, stdscr, action=None):
    snap = session.tool_state.snap_size
    if action == 'move_cursor_up':
        session.cursor_y = max(0, session.cursor_y - snap)
        if session.cursor_y < session.camera_y: session.camera_y = session.cursor_y
    elif action == 'move_cursor_down':
        session.cursor_y = min(session.map_obj.height - 1, session.cursor_y + snap)
        if session.cursor_y >= session.camera_y + session.view_height: session.camera_y = session.cursor_y - session.view_height + 1
    elif action == 'move_cursor_left':
        session.cursor_x = max(0, session.cursor_x - snap)
        if session.cursor_x < session.camera_x: session.camera_x = session.cursor_x
    elif action == 'move_cursor_right':
        session.cursor_x = min(session.map_obj.width - 1, session.cursor_x + snap)
        if session.cursor_x >= session.camera_x + session.view_width: session.camera_x = session.cursor_x - session.view_width + 1

def handle_place_tile(session, stdscr, action=None):
    ts = session.tool_state
    if ts.mode == 'place':
        # Only push undo if the tile actually changes
        old_val = session.map_obj.get(session.cursor_x, session.cursor_y)
        if old_val != session.selected_char:
            session.map_obj.push_undo()
            place_tile_at(session.map_obj, session.cursor_x, session.cursor_y, session.selected_char, ts.brush_size, ts.brush_shape, ts)
            ts.edits_since_save += 1
    elif ts.mode in ('line', 'rect', 'circle', 'pattern'):
        if ts.start_point is None:
            ts.start_point = (session.cursor_x, session.cursor_y)
        else:
            session.map_obj.push_undo()
            if ts.mode == 'line':
                draw_line(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, session.selected_char, ts.brush_size, ts.brush_shape, ts)
            elif ts.mode == 'rect':
                filled = get_user_confirmation(stdscr, session.status_y + 2, 0, "Filled? (y/n): ")
                draw_rectangle(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, session.selected_char, filled, ts.brush_size, ts.brush_shape, ts)
            elif ts.mode == 'circle':
                radius = int(get_distance(ts.start_point, (session.cursor_x, session.cursor_y)))
                filled = get_user_confirmation(stdscr, session.status_y + 2, 0, "Filled? (y/n): ")
                draw_circle(session.map_obj, ts.start_point[0], ts.start_point[1], radius, session.selected_char, filled, ts.brush_size, ts.brush_shape, ts)
            elif ts.mode == 'pattern' and ts.pattern:
                draw_pattern_rectangle(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, ts.pattern)
            ts.start_point = None
            ts.edits_since_save += 1

def handle_flood_fill(session, stdscr, action=None):
    old_char = session.map_obj.get(session.cursor_x, session.cursor_y)
    if old_char != session.selected_char:
        session.map_obj.push_undo()
        flood_fill(session.map_obj, session.cursor_x, session.cursor_y, session.selected_char)
        session.tool_state.edits_since_save += 1

def handle_undo_redo(session, stdscr, action=None):
    res = session.undo_stack.undo(session.map_obj.copy_data()) if action == 'undo' else session.undo_stack.redo(session.map_obj.copy_data())
    if res:
        session.map_obj.data = res
        session.map_obj.dirty = True
        session.selection_start = session.selection_end = None

def handle_selection(session, stdscr, action=None):
    if action == 'select_start':
        if session.selection_start is None: session.selection_start, session.selection_end = (session.cursor_x, session.cursor_y), None
        elif session.selection_end is None:
            x0, y0 = session.selection_start
            session.selection_start = (min(x0, session.cursor_x), min(y0, session.cursor_y))
            session.selection_end = (max(x0, session.cursor_x), max(y0, session.cursor_y))
        else: session.selection_start, session.selection_end = (session.cursor_x, session.cursor_y), None
    elif action == 'clear_selection':
        session.selection_start = session.selection_end = None
    elif action == 'copy_selection' and session.selection_start and session.selection_end:
        x0, y0 = session.selection_start
        x1, y1 = session.selection_end
        session.clipboard = [[session.map_obj.get(x, y) for x in range(x0, x1+1)] for y in range(y0, y1+1)]
    elif action == 'paste_selection' and session.clipboard:
        session.map_obj.push_undo()
        for dy, row in enumerate(session.clipboard):
            for dx, ch in enumerate(row):
                session.map_obj.set(session.cursor_x + dx, session.cursor_y + dy, ch)
    elif action == 'clear_area' and session.selection_start and session.selection_end:
        session.map_obj.push_undo()
        for y in range(session.selection_start[1], session.selection_end[1]+1):
            for x in range(session.selection_start[0], session.selection_end[0]+1):
                session.map_obj.set(x, y, '.')

def handle_map_transform(session, stdscr, action=None):
    session.map_obj.push_undo()
    if action == 'map_rotate':
        new_data = rotate_selection_90(session.map_obj.data)
        session.map_obj = Map(session.map_obj.height, session.map_obj.width, new_data, undo_stack=session.undo_stack)
        session.camera_x = session.camera_y = 0
    elif action == 'map_flip_h': session.map_obj.data = flip_selection_horizontal(session.map_obj.data)
    elif action == 'map_flip_v': session.map_obj.data = flip_selection_vertical(session.map_obj.data)
    elif action.startswith('map_shift_'):
        dx, dy = 0, 0
        if 'up' in action: dy = -1
        elif 'down' in action: dy = 1
        elif 'left' in action: dx = -1
        elif 'right' in action: dx = 1
        session.map_obj.data = shift_map(session.map_obj.data, dx, dy)

def handle_generation(session, stdscr, action=None):
    session.map_obj.push_undo()
    success = False
    if action == 'random_gen': success = menu_random_generation(stdscr, session.map_obj, session.tool_state.seed)
    elif action == 'perlin_noise': success = menu_perlin_generation(stdscr, session.map_obj, session.tile_chars, session.tool_state.seed)
    elif action == 'voronoi': success = menu_voronoi_generation(stdscr, session.map_obj, session.tile_chars, session.tool_state.seed)
    if success: session.tool_state.edits_since_save += 1

def handle_tile_management(session, stdscr, action=None):
    if action == 'cycle_tile':
        session.selected_idx = (session.selected_idx + 1) % len(session.tile_chars)
        session.selected_char = session.tile_chars[session.selected_idx]
    elif action == 'pick_tile':
        from ui import init_color_pairs
        picked = menu_pick_tile(stdscr, session.tile_chars, session.tile_colors, session.color_pairs)
        if picked:
            session.selected_char = picked
            session.selected_idx = session.tile_chars.index(picked)
    elif action == 'define_tiles':
        from ui import init_color_pairs
        menu_define_tiles(stdscr, session.tile_chars, session.tile_colors)
        session.color_pairs = init_color_pairs(session.tile_colors)
        session.selected_idx = min(session.selected_idx, len(session.tile_chars) - 1)
        session.selected_char = session.tile_chars[session.selected_idx]

def handle_replace_all(session, stdscr, action=None):
    old_c = get_user_input(stdscr, session.status_y + 2, 0, "Replace tile: ")
    if len(old_c) == 1:
        new_c = get_user_input(stdscr, session.status_y + 2, 0, "With tile: ")
        if len(new_c) == 1 and old_c != new_c:
            session.map_obj.push_undo()
            cnt = 0
            for y in range(session.map_obj.height):
                for x in range(session.map_obj.width):
                    if session.map_obj.get(x, y) == old_c:
                        session.map_obj.set(x, y, new_c)
                        cnt += 1
            stdscr.addstr(session.status_y + 2, 0, f"Replaced {cnt}. Press key...")
            stdscr.timeout(-1)
            stdscr.getch()
            stdscr.timeout(1000)

def get_action_dispatcher():
    return {
        'quit': handle_quit,
        'editor_menu': handle_editor_menu,
        'move_view_up': handle_move_view, 'move_view_down': handle_move_view,
        'move_view_left': handle_move_view, 'move_view_right': handle_move_view,
        'move_cursor_up': handle_move_cursor, 'move_cursor_down': handle_move_cursor,
        'move_cursor_left': handle_move_cursor, 'move_cursor_right': handle_move_cursor,
        'place_tile': handle_place_tile,
        'flood_fill': handle_flood_fill,
        'undo': handle_undo_redo, 'redo': handle_undo_redo,
        'select_start': handle_selection, 'clear_selection': handle_selection,
        'copy_selection': handle_selection, 'paste_selection': handle_selection,
        'clear_area': handle_selection,
        'map_rotate': handle_map_transform, 'map_flip_h': handle_map_transform, 'map_flip_v': handle_map_transform,
        'map_shift_up': handle_map_transform, 'map_shift_down': handle_map_transform,
        'map_shift_left': handle_map_transform, 'map_shift_right': handle_map_transform,
        'random_gen': handle_generation, 'perlin_noise': handle_generation, 'voronoi': handle_generation,
        'cycle_tile': handle_tile_management, 'pick_tile': handle_tile_management, 'define_tiles': handle_tile_management,
        'replace_all': handle_replace_all,
    }
