import sys
import random
import pygame
from utils import get_distance, rotate_selection_90, flip_selection_horizontal, flip_selection_vertical, shift_map, get_user_input, get_user_confirmation
from drawing import place_tile_at, flood_fill, draw_line, draw_rectangle, draw_circle, draw_pattern_rectangle
from menus import (
    menu_save_map, menu_load_map, menu_macros, menu_define_autotiling,
    menu_autosave_settings, menu_editor_pause, menu_define_pattern,
    menu_define_brush, menu_pick_tile, menu_new_map, menu_resize_map,
    menu_set_seed, menu_statistics, menu_controls, menu_random_generation,
    menu_perlin_generation, menu_voronoi_generation, menu_define_tiles,
    menu_export_image, build_key_map
)
from ui import init_color_pairs, draw_help_overlay, invalidate_cache
from core import Map

def show_message(context, text):
    # Quick helper to show a message and wait for key
    screen = context.screen
    font = context.font

    # Draw a box in center
    text_surf = font.render(text, True, (255, 255, 255))
    rect = text_surf.get_rect(center=(context.width // 2, context.height // 2))
    bg_rect = rect.inflate(20, 20)

    pygame.draw.rect(screen, (0, 0, 0), bg_rect)
    pygame.draw.rect(screen, (255, 255, 255), bg_rect, 1)
    screen.blit(text_surf, rect)
    pygame.display.flip()

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN or event.type == pygame.QUIT:
                waiting = False
        context.clock.tick(10)

def handle_quit(session, context, action=None):
    if session.map_obj.dirty:
        if not get_user_confirmation(context, 10, 2, "Unsaved! Quit anyway? (y/n): "):
            return
    session.running = False

def handle_editor_menu(session, context, action=None):
    choice = menu_editor_pause(context)
    if choice == "Save Map":
        if menu_save_map(context, session.map_obj):
            session.map_obj.dirty = False
    elif choice == "Load Map":
        loaded = menu_load_map(context, session.view_width, session.view_height)
        if loaded:
            session.map_obj.push_undo()
            session.map_obj = loaded
            session.map_obj.dirty = False
            session.camera_x, session.camera_y = 0, 0
            session.cursor_x, session.cursor_y = 0, 0
            invalidate_cache()
    elif choice == "Macro Manager":
        menu_macros(context, session.tool_state)
    elif choice == "Auto-Tiling Manager":
        menu_define_autotiling(context, session.tool_state, session.tile_chars)
    elif choice == "Autosave Settings":
        menu_autosave_settings(context, session.tool_state)
    elif choice == "Exit to Main Menu":
        if session.map_obj.dirty:
            if get_user_confirmation(context, 10, 2, "Unsaved! Exit anyway? (y/n): "):
                session.running = False
        else: session.running = False
    elif choice == "Quit Editor":
        sys.exit(0)

def handle_move_view(session, context, action=None):
    if action == 'move_view_up': session.camera_y = max(0, session.camera_y - 1)
    elif action == 'move_view_down': session.camera_y = min(session.map_obj.height - session.view_height, session.camera_y + 1)
    elif action == 'move_view_left': session.camera_x = max(0, session.camera_x - 1)
    elif action == 'move_view_right': session.camera_x = min(session.map_obj.width - session.view_width, session.camera_x + 1)

def handle_move_cursor(session, context, action=None):
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

def handle_place_tile(session, context, action=None):
    ts = session.tool_state
    if ts.mode == 'place':
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
                filled = get_user_confirmation(context, 10, 2, "Filled? (y/n): ")
                draw_rectangle(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, session.selected_char, filled, ts.brush_size, ts.brush_shape, ts)
            elif ts.mode == 'circle':
                radius = int(get_distance(ts.start_point, (session.cursor_x, session.cursor_y)))
                filled = get_user_confirmation(context, 10, 2, "Filled? (y/n): ")
                draw_circle(session.map_obj, ts.start_point[0], ts.start_point[1], radius, session.selected_char, filled, ts.brush_size, ts.brush_shape, ts)
            elif ts.mode == 'pattern' and ts.pattern:
                draw_pattern_rectangle(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, ts.pattern)
            ts.start_point = None
            ts.edits_since_save += 1

def handle_flood_fill(session, context, action=None):
    old_char = session.map_obj.get(session.cursor_x, session.cursor_y)
    if old_char != session.selected_char:
        session.map_obj.push_undo()
        flood_fill(session.map_obj, session.cursor_x, session.cursor_y, session.selected_char)
        session.tool_state.edits_since_save += 1

def handle_undo_redo(session, context, action=None):
    res = session.undo_stack.undo(session.map_obj.copy_data()) if action == 'undo' else session.undo_stack.redo(session.map_obj.copy_data())
    if res is not None:
        session.map_obj.data = res
        session.map_obj.dirty = True
        session.selection_start = session.selection_end = None
        invalidate_cache()

def handle_selection(session, context, action=None):
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

def handle_map_transform(session, context, action=None):
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
    invalidate_cache()

def handle_generation(session, context, action=None):
    session.map_obj.push_undo()
    success = False
    if action == 'random_gen': success = menu_random_generation(context, session.map_obj, session.tool_state.seed)
    elif action == 'perlin_noise': success = menu_perlin_generation(context, session.map_obj, session.tile_chars, session.tool_state.seed)
    elif action == 'voronoi': success = menu_voronoi_generation(context, session.map_obj, session.tile_chars, session.tool_state.seed)
    if success: 
        session.tool_state.edits_since_save += 1
        invalidate_cache()

def handle_tile_management(session, context, action=None):
    if action == 'cycle_tile':
        session.selected_idx = (session.selected_idx + 1) % len(session.tile_chars)
        session.selected_char = session.tile_chars[session.selected_idx]
    elif action == 'pick_tile':
        picked = menu_pick_tile(context, session.tile_chars, session.tile_colors, session.color_pairs)
        if picked:
            session.selected_char = picked
            session.selected_idx = session.tile_chars.index(picked)
    elif action == 'define_tiles':
        menu_define_tiles(context, session.tile_chars, session.tile_colors)
        session.color_pairs = init_color_pairs(session.tile_colors)
        session.selected_idx = min(session.selected_idx, len(session.tile_chars) - 1)
        session.selected_char = session.tile_chars[session.selected_idx]

def handle_replace_all(session, context, action=None):
    old_c = get_user_input(context, 10, 2, "Replace tile: ")
    if len(old_c) == 1:
        new_c = get_user_input(context, 11, 2, "With tile: ")
        if len(new_c) == 1 and old_c != new_c:
            session.map_obj.push_undo()
            cnt = 0
            for y in range(session.map_obj.height):
                for x in range(session.map_obj.width):
                    if session.map_obj.get(x, y) == old_c:
                        session.map_obj.set(x, y, new_c)
                        cnt += 1
            invalidate_cache()
            show_message(context, f"Replaced {cnt}. Press key...")

def handle_brush_size(session, context, action=None):
    if action == 'increase_brush':
        session.tool_state.brush_size = min(session.tool_state.brush_size + 1, 10)
    elif action == 'decrease_brush':
        session.tool_state.brush_size = max(session.tool_state.brush_size - 1, 1)

def handle_measurement(session, context, action=None):
    session.tool_state.measure_start = (session.cursor_x, session.cursor_y)

def handle_tool_select(session, context, action=None):
    ts = session.tool_state
    ts.mode = action.split('_')[0]
    ts.start_point = None
    if action == 'pattern_tool' and ts.pattern is None:
        ts.pattern = menu_define_pattern(context, session.tile_chars, session.tile_colors)

def handle_define_pattern(session, context, action=None):
    session.tool_state.pattern = menu_define_pattern(context, session.tile_chars, session.tile_colors)

def handle_define_brush(session, context, action=None):
    session.tool_state.brush_shape = menu_define_brush(context)

def handle_toggle_snap(session, context, action=None):
    inp = get_user_input(context, 10, 2, "Enter snap size: ")
    try:
        session.tool_state.snap_size = int(inp or "1")
    except: pass

def handle_toggle_palette(session, context, action=None):
    session.tool_state.show_palette = not session.tool_state.show_palette

def handle_toggle_autotile(session, context, action=None):
    if session.tool_state.auto_tiling:
        session.tool_state.auto_tiling = False
    elif session.selected_char in session.tool_state.tiling_rules:
        session.tool_state.auto_tiling = True
    else:
        show_message(context, f"No rules for '{session.selected_char}'!")

def handle_resize_map(session, context, action=None):
    res = menu_resize_map(context, session.map_obj, session.view_width, session.view_height)
    if res is not None:
        session.map_obj = res
        session.map_obj.undo_stack = session.undo_stack
        invalidate_cache()

def handle_set_seed(session, context, action=None):
    session.tool_state.seed = menu_set_seed(context, session.tool_state.seed)
    random.seed(session.tool_state.seed)

def handle_statistics(session, context, action=None):
    menu_statistics(context, session.map_obj)

def handle_show_help(session, context, action=None):
    draw_help_overlay(context, session.bindings)

def handle_edit_controls(session, context, action=None):
    menu_controls(context, session.bindings)
    session.key_map = build_key_map(session.bindings)

def handle_file_ops(session, context, action=None):
    if action == 'save_map':
        if menu_save_map(context, session.map_obj):
            session.map_obj.dirty = False
    elif action == 'load_map':
        loaded = menu_load_map(context, session.view_width, session.view_height)
        if loaded:
            session.map_obj.push_undo()
            session.map_obj = loaded
            session.map_obj.dirty = False
            session.camera_x, session.camera_y = 0, 0
            session.cursor_x, session.cursor_y = 0, 0
            invalidate_cache()
    elif action == 'new_map':
        new_m = menu_new_map(context, session.view_width, session.view_height)
        if new_m:
             session.map_obj = new_m
             session.map_obj.undo_stack = session.undo_stack
             session.map_obj.dirty = False
             session.camera_x, session.camera_y = 0, 0
             session.cursor_x, session.cursor_y = 0, 0
             invalidate_cache()
    elif action == 'export_image':
        menu_export_image(context, session.map_obj, session.tile_colors)

def handle_macro_toggle(session, context, action=None):
    ts = session.tool_state
    if ts.recording:
        ts.recording = False
        name = get_user_input(context, 10, 2, "Enter name for macro: ")
        if name: ts.macros[name] = list(ts.current_macro_actions)
    else:
        ts.recording = True
        ts.current_macro_actions = []

def handle_macro_play(session, context, action=None):
    ts = session.tool_state
    name = get_user_input(context, 10, 2, "Enter macro name to play: ")
    if name in ts.macros:
        session.action_queue.extendleft(reversed(ts.macros[name]))

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
        'increase_brush': handle_brush_size, 'decrease_brush': handle_brush_size,
        'set_measure': handle_measurement,
        'line_tool': handle_tool_select, 'rect_tool': handle_tool_select,
        'circle_tool': handle_tool_select, 'pattern_tool': handle_tool_select,
        'define_pattern': handle_define_pattern, 'define_brush': handle_define_brush,
        'toggle_snap': handle_toggle_snap, 'toggle_palette': handle_toggle_palette,
        'toggle_autotile': handle_toggle_autotile,
        'resize_map': handle_resize_map, 'set_seed': handle_set_seed,
        'statistics': handle_statistics, 'show_help': handle_show_help,
        'edit_controls': handle_edit_controls,
        'save_map': handle_file_ops, 'load_map': handle_file_ops,
        'new_map': handle_file_ops, 'export_image': handle_file_ops,
        'macro_record_toggle': handle_macro_toggle,
        'macro_play': handle_macro_play,
    }
