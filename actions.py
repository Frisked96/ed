import sys
import random
import time
import pygame
from map_io import autosave_map
from utils import get_distance, rotate_selection_90, flip_selection_horizontal, flip_selection_vertical, shift_map
from drawing import place_tile_at, flood_fill, draw_line, draw_rectangle, draw_circle
from menu import (
    menu_save_map, menu_autosave_settings, menu_editor_pause,
    menu_define_brush, menu_define_pattern, NewMapState, LoadMapState, ExportMapState, menu_resize_map,
    menu_statistics, menu_random_generation,
    menu_perlin_generation, menu_voronoi_generation,
    MessageState, ConfirmationState, TextInputState, HelpState
)
from core import Map
from tiles import REGISTRY

def check_autosave(session, manager):
    ts = session.tool_state
    if not ts.autosave_enabled: return

    do_save = False
    if ts.autosave_mode == 'edits':
        if ts.edits_since_save >= ts.autosave_edits_threshold:
            do_save = True
    elif ts.autosave_mode == 'time':
        if time.time() - ts.last_autosave_time >= ts.autosave_interval * 60:
            do_save = True

    if do_save:
        if autosave_map(session.map_obj, ts.autosave_filename):
            ts.edits_since_save = 0
            ts.last_autosave_time = time.time()
            show_message(manager, f"Autosaved to {ts.autosave_filename}", notify=True)

def show_message(manager, text, notify=False):
    if notify:
        manager.notify(text)
        return
    manager.flow.push_message(text)

def handle_quit(session, manager, action=None):
    flow = manager.flow
    if session.map_obj.dirty:
        def on_confirm(confirmed):
            if confirmed: flow.exit_to_menu()
        flow.push_confirmation("Unsaved! Quit anyway? (y/n): ", on_confirm)
    else:
        flow.exit_to_menu()

def handle_editor_menu(session, manager, action=None):
    flow = manager.flow
    def on_choice(choice):
        if choice == "Save Map":
            if menu_save_map(manager, session.map_obj):
                session.map_obj.dirty = False
        elif choice == "Load Map":
            def _on_loaded(m):
                if m:
                    session.map_obj.push_undo()
                    session.map_obj = m
                    session.map_obj.dirty = False
                    session.camera_x, session.camera_y = 0, 0
                    session.cursor_x, session.cursor_y = 0, 0
            flow.push_load_map_wizard(session.view_width, session.view_height, _on_loaded)
        elif choice == "Macro Manager":
            flow.push_macro_manager(session.tool_state)
        elif choice == "Auto-Tiling Manager":
            flow.push_autotile_manager(session.tool_state)
        elif choice == "Autosave Settings":
            menu_autosave_settings(manager, session.tool_state)
        elif choice == "Exit to Main Menu":
            if session.map_obj.dirty:
                def on_confirm(confirmed):
                    if confirmed: flow.exit_to_menu()
                flow.push_confirmation("Unsaved! Exit anyway? (y/n): ", on_confirm)
            else: 
                flow.exit_to_menu()
        elif choice == "Quit Editor":
            manager.running = False
            
    flow.push_pause_menu(on_choice)

def handle_move_view(session, manager, action=None):
    if action == 'move_view_up':
        session.camera_y = max(0, session.camera_y - 1)
    elif action == 'move_view_down':
        session.camera_y = max(0, min(session.map_obj.height - session.view_height, session.camera_y + 1))
    elif action == 'move_view_left':
        session.camera_x = max(0, session.camera_x - 1)
    elif action == 'move_view_right':
        session.camera_x = max(0, min(session.map_obj.width - session.view_width, session.camera_x + 1))

def handle_move_cursor(session, manager, action=None):
    snap = session.tool_state.snap_size
    if action == 'move_cursor_up':
        session.cursor_y = max(0, session.cursor_y - snap)
    elif action == 'move_cursor_down':
        session.cursor_y = min(session.map_obj.height - 1, session.cursor_y + snap)
    elif action == 'move_cursor_left':
        session.cursor_x = max(0, session.cursor_x - snap)
    elif action == 'move_cursor_right':
        session.cursor_x = min(session.map_obj.width - 1, session.cursor_x + snap)

    # Bind camera to cursor
    if session.cursor_x < session.camera_x:
        session.camera_x = session.cursor_x
    if session.cursor_x >= session.camera_x + session.view_width:
        session.camera_x = max(0, min(session.map_obj.width - session.view_width, session.cursor_x - session.view_width + 1))
    
    if session.cursor_y < session.camera_y:
        session.camera_y = session.cursor_y
    if session.cursor_y >= session.camera_y + session.view_height:
        session.camera_y = max(0, min(session.map_obj.height - session.view_height, session.cursor_y - session.view_height + 1))

def handle_place_tile(session, manager, action=None):
    ts = session.tool_state
    if ts.mode == 'place':
        old_val = session.map_obj.get(session.cursor_x, session.cursor_y)
        if old_val != session.selected_tile_id:
            session.map_obj.push_undo()
            place_tile_at(session.map_obj, session.cursor_x, session.cursor_y, session.selected_tile_id, ts.brush_size, ts.brush_shape, ts)
            ts.edits_since_save += 1
            check_autosave(session, manager)
    elif ts.mode in ('line', 'rect', 'circle', 'pattern', 'select'):
        if ts.start_point is None:
            ts.start_point = (session.cursor_x, session.cursor_y)
        else:
            if ts.mode == 'select':
                x0, y0 = ts.start_point
                x1, y1 = session.cursor_x, session.cursor_y
                session.selection_start = (min(x0, x1), min(y0, y1))
                session.selection_end = (max(x0, x1), max(y0, y1))
                ts.start_point = None
                show_message(manager, "Area Selected", notify=True)
            elif ts.mode == 'line':
                session.map_obj.push_undo()
                draw_line(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, session.selected_tile_id, ts.brush_size, ts.brush_shape, ts)
                ts.start_point = None
                ts.edits_since_save += 1
                check_autosave(session, manager)
            elif ts.mode == 'rect':
                def on_rect_confirm(filled):
                    session.map_obj.push_undo()
                    draw_rectangle(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, session.selected_tile_id, filled, ts.brush_size, ts.brush_shape, ts)
                    ts.start_point = None
                    ts.edits_since_save += 1
                    check_autosave(session, manager)
                
                if ts.shape_fill_mode == 'fill':
                    on_rect_confirm(True)
                elif ts.shape_fill_mode == 'outline':
                    on_rect_confirm(False)
                else:
                    manager.flow.push_confirmation("Filled? (y/n): ", on_rect_confirm)
            elif ts.mode == 'circle':
                def on_circle_confirm(filled):
                    session.map_obj.push_undo()
                    radius = int(get_distance(ts.start_point, (session.cursor_x, session.cursor_y)))
                    draw_circle(session.map_obj, ts.start_point[0], ts.start_point[1], radius, session.selected_tile_id, filled, ts.brush_size, ts.brush_shape, ts)
                    ts.start_point = None
                    ts.edits_since_save += 1
                    check_autosave(session, manager)

                if ts.shape_fill_mode == 'fill':
                    on_circle_confirm(True)
                elif ts.shape_fill_mode == 'outline':
                    on_circle_confirm(False)
                else:
                    manager.flow.push_confirmation("Filled? (y/n): ", on_circle_confirm)

def handle_flood_fill(session, manager, action=None):
    old_char = session.map_obj.get(session.cursor_x, session.cursor_y)
    if old_char != session.selected_tile_id:
        session.map_obj.push_undo()
        flood_fill(session.map_obj, session.cursor_x, session.cursor_y, session.selected_tile_id)
        session.tool_state.edits_since_save += 1
        check_autosave(session, manager)

def handle_undo_redo(session, manager, action=None):
    res = session.undo_stack.undo(session.map_obj.copy_data()) if action == 'undo' else session.undo_stack.redo(session.map_obj.copy_data())
    if res is not None:
        session.map_obj.data = res
        session.map_obj.dirty = True
        session.selection_start = session.selection_end = None
        check_autosave(session, manager)
        show_message(manager, f"{action.capitalize()} successful", notify=True)

def handle_selection(session, manager, action=None):
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
        show_message(manager, f"Copied {x1-x0+1}x{y1-y0+1} area", notify=True)
    elif action == 'paste_selection' and session.clipboard:
        session.map_obj.push_undo()
        for dy, row in enumerate(session.clipboard):
            for dx, ch in enumerate(row):
                session.map_obj.set(session.cursor_x + dx, session.cursor_y + dy, ch)
        session.tool_state.edits_since_save += 1
        check_autosave(session, manager)
        show_message(manager, "Pasted area", notify=True)
    elif action == 'clear_area' and session.selection_start and session.selection_end:
        session.map_obj.push_undo()
        for y in range(session.selection_start[1], session.selection_end[1]+1):
            for x in range(session.selection_start[0], session.selection_end[0]+1):
                session.map_obj.set(x, y, 0) # 0 is void
        session.tool_state.edits_since_save += 1
        check_autosave(session, manager)
        show_message(manager, "Area cleared", notify=True)

def handle_rotate_selection_action(session, manager, action=None):
    if not (session.selection_start and session.selection_end):
        if session.clipboard:
             session.clipboard = rotate_selection_90(session.clipboard)
             show_message(manager, "Clipboard Rotated (Paste to apply)", notify=True)
             return
        show_message(manager, "No selection to rotate")
        return

    # In-Place Rotation
    x0, y0 = session.selection_start
    x1, y1 = session.selection_end
    sx0, sx1 = min(x0, x1), max(x0, x1)
    sy0, sy1 = min(y0, y1), max(y0, y1)
    
    w = sx1 - sx0 + 1
    h = sy1 - sy0 + 1
    
    # Copy data
    data = [[session.map_obj.get(x, y) for x in range(sx0, sx1+1)] for y in range(sy0, sy1+1)]
    
    # Rotate
    rotated = rotate_selection_90(data)
    new_h = len(rotated)
    new_w = len(rotated[0])
    
    session.map_obj.push_undo()
    
    # Clear old area
    for y in range(sy0, sy1+1):
        for x in range(sx0, sx1+1):
            session.map_obj.set(x, y, 0) # Clear to void
            
    # Calculate center
    cx = sx0 + w / 2
    cy = sy0 + h / 2
    nx = int(cx - new_w / 2)
    ny = int(cy - new_h / 2)
    
    # Paste rotated
    for dy, row in enumerate(rotated):
        for dx, val in enumerate(row):
            session.map_obj.set(nx + dx, ny + dy, val)
            
    # Update selection
    session.selection_start = (nx, ny)
    session.selection_end = (nx + new_w - 1, ny + new_h - 1)
    
    session.tool_state.edits_since_save += 1
    check_autosave(session, manager)
    show_message(manager, "Selection Rotated", notify=True)

def handle_map_transform(session, manager, action=None):
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
    session.tool_state.edits_since_save += 1
    check_autosave(session, manager)

def handle_generation(session, manager, action=None):
    session.map_obj.push_undo()
    success = False
    if action == 'random_gen': success = menu_random_generation(manager, session.map_obj, session.tool_state.seed)
    elif action == 'perlin_noise': success = menu_perlin_generation(manager, session.map_obj, session.tool_state.seed)
    elif action == 'voronoi': success = menu_voronoi_generation(manager, session.map_obj, session.tool_state.seed)
    if success: 
        session.tool_state.edits_since_save += 1
        check_autosave(session, manager)

def handle_tile_management(session, manager, action=None):
    if action == 'cycle_tile':
        all_tiles = list(REGISTRY.get_all())
        if not all_tiles: return
        current_idx = 0
        for i, t in enumerate(all_tiles):
            if t.id == session.selected_tile_id:
                current_idx = i
                break
        next_idx = (current_idx + 1) % len(all_tiles)
        session.selected_tile_id = all_tiles[next_idx].id
        
    elif action == 'pick_tile':
        def _on_picked(picked_id):
            if picked_id is not None:
                session.selected_tile_id = picked_id
        manager.flow.push_tile_picker(_on_picked)
            
    elif action == 'define_tiles':
        manager.flow.push_tile_registry()

def handle_replace_all(session, manager, action=None):
    def on_old_char(old_c):
        if old_c and len(old_c) == 1:
            def on_new_char(new_c):
                if new_c and len(new_c) == 1:
                    old_id = REGISTRY.get_by_char(old_c)
                    new_id = REGISTRY.get_by_char(new_c)
                    if old_id != new_id:
                        session.map_obj.push_undo()
                        cnt = 0
                        for y in range(session.map_obj.height):
                            for x in range(session.map_obj.width):
                                if session.map_obj.get(x, y) == old_id:
                                    session.map_obj.set(x, y, new_id)
                                    cnt += 1
                        session.tool_state.edits_since_save += 1
                        check_autosave(session, manager)
                        show_message(manager, f"Replaced {cnt} tiles", notify=True)
            manager.flow.push_text_input("With tile char: ", on_new_char)
    manager.flow.push_text_input("Replace tile char: ", on_old_char)

def handle_brush_size(session, manager, action=None):
    if action == 'increase_brush':
        session.tool_state.brush_size = min(session.tool_state.brush_size + 1, 10)
    elif action == 'decrease_brush':
        session.tool_state.brush_size = max(session.tool_state.brush_size - 1, 1)

def handle_measurement(session, manager, action=None):
    session.tool_state.measure_start = (session.cursor_x, session.cursor_y)

def handle_tool_select(session, manager, action=None):
    ts = session.tool_state
    ts.mode = action.split('_')[0]
    ts.start_point = None

def handle_define_pattern(session, manager, action=None):
    def on_pattern(pattern):
        if pattern:
            session.tool_state.pattern = pattern
            show_message(manager, "Pattern defined", notify=True)
    menu_define_pattern(manager, on_pattern)

def handle_define_brush(session, manager, action=None):
    def on_brush(brush):
        if brush:
            session.tool_state.brush_shape = brush
            show_message(manager, "Brush defined", notify=True)
    menu_define_brush(manager, on_brush)

def handle_toggle_snap(session, manager, action=None):
    def on_snap(inp):
        try:
            session.tool_state.snap_size = int(inp or "1")
        except: pass
    manager.flow.push_text_input("Enter snap size: ", on_snap)

def handle_toggle_palette(session, manager, action=None):
    session.tool_state.show_palette = not session.tool_state.show_palette

def handle_toggle_autotile(session, manager, action=None):
    session.tool_state.auto_tiling = not session.tool_state.auto_tiling

def handle_resize_map(session, manager, action=None):
    def on_resized(new_map):
        if new_map:
            session.map_obj = new_map
            session.map_obj.dirty = False
    manager.flow.push_resize_wizard(session.map_obj, session.view_width, session.view_height, on_resized)

def handle_set_seed(session, manager, action=None):
    def on_seed(inp):
        if inp:
            if inp.lower() == 'random':
                session.tool_state.seed = None
            else:
                try: session.tool_state.seed = int(inp)
                except: pass
            import numpy as np
            random.seed(session.tool_state.seed)
            np.random.seed(session.tool_state.seed)
    prompt = f"New seed (current: {session.tool_state.seed if session.tool_state.seed is not None else 'random'}): "
    manager.flow.push_text_input(prompt, on_seed)

def handle_statistics(session, manager, action=None):
    menu_statistics(manager, session.map_obj)

def handle_show_help(session, manager, action=None):
    manager.flow.push_help(session.bindings)

def handle_edit_controls(session, manager, action=None):
    manager.flow.push_control_settings(session.bindings)

def handle_file_ops(session, manager, action=None):
    if action == 'save_map':
        if menu_save_map(manager, session.map_obj):
            session.map_obj.dirty = False
    elif action == 'load_map':
        def _on_loaded(m):
            if m:
                session.map_obj = m
                session.map_obj.dirty = False
                session.camera_x, session.camera_y = 0, 0
                session.cursor_x, session.cursor_y = 0, 0
        manager.flow.push_load_map_wizard(session.view_width, session.view_height, _on_loaded)
    elif action == 'new_map':
        def _on_new(m):
             if m:
                 session.map_obj = m
                 session.map_obj.dirty = False
                 session.camera_x, session.camera_y = 0, 0
                 session.cursor_x, session.cursor_y = 0, 0
        manager.flow.push_new_map_wizard(session.view_width, session.view_height, _on_new)
    elif action == 'export_image':
        manager.flow.push_export_wizard(session.map_obj)

def handle_macro_toggle(session, manager, action=None):
    ts = session.tool_state
    if ts.recording:
        ts.recording = False
        def on_name(name):
            if name: 
                ts.macros[name] = list(ts.current_macro_actions)
                show_message(manager, f"Macro '{name}' saved", notify=True)
        manager.flow.push_text_input("Enter name for macro: ", on_name)
    else:
        ts.recording = True
        ts.current_macro_actions = []
        show_message(manager, "Recording Macro...", notify=True)

def handle_macro_play(session, manager, action=None):
    ts = session.tool_state
    def on_play(name):
        if name in ts.macros:
            session.action_queue.extendleft(reversed(ts.macros[name]))
    manager.flow.push_text_input("Enter macro name to play: ", on_play)

def handle_open_context_menu(session, manager, action=None):
    from menu.base import ContextMenuState
    from menu.generation import AdvancedGenerationState
    
    mouse_pos = pygame.mouse.get_pos()
    
    def on_flood_fill():
        handle_flood_fill(session, manager, 'flood_fill')

    def set_tool(mode):
        session.tool_state.mode = mode
        session.tool_state.start_point = None
        show_message(manager, f"Switched to {mode.capitalize()} Tool", notify=True)

    has_selection = session.selection_start is not None and session.selection_end is not None

    if has_selection:
        options = [
            ("Copy Selection", lambda: handle_selection(session, manager, 'copy_selection')),
            ("Rotate Selection", lambda: handle_rotate_selection_action(session, manager)),
            ("Clear Area", lambda: handle_selection(session, manager, 'clear_area')),
            ("Advanced Gen", lambda: manager.flow.push_advanced_gen(session)),
            ("Deselect", lambda: handle_selection(session, manager, 'clear_selection')),
            ("---", None),
            ("Point Tool", lambda: set_tool('place')),
        ]
    else:
        def draw_long(direction):
            session.draw_long_line(direction, session.cursor_x, session.cursor_y)
            show_message(manager, f"Long {direction.capitalize()} Line Placed", notify=True)

        options = [
            ("Point Tool", lambda: set_tool('place')),
            ("Line Tool", lambda: set_tool('line')),
            ("Long Horiz. Line", lambda: draw_long('horizontal')),
            ("Long Vert. Line", lambda: draw_long('vertical')),
            ("Rect Tool", lambda: set_tool('rect')),
            ("Circle Tool", lambda: set_tool('circle')),
            ("Select Tool", lambda: set_tool('select')),
            ("Flood Fill", on_flood_fill),
            ("---", None),
            ("Toggle Measurement", lambda: handle_measurement_toggle(session, manager)),
            ("Measurement Settings", lambda: handle_measurement_configure(session, manager)),
            ("---", None),
            ("Go To Coordinates", lambda: handle_goto_coords(session, manager)),
            ("Pick Tile", lambda: handle_tile_management(session, manager, 'pick_tile')),
            ("Toggle Palette", lambda: handle_toggle_palette(session, manager)),
            ("Undo", lambda: handle_undo_redo(session, manager, 'undo')),
            ("Redo", lambda: handle_undo_redo(session, manager, 'redo')),
            ("Save Map", lambda: handle_file_ops(session, manager, 'save_map')),
        ]

    manager.push(ContextMenuState(manager, manager.flow.renderer, options, mouse_pos))

def handle_zoom(session, manager, action=None):
    renderer = manager.flow.renderer
    old_ts = renderer.tile_size
    if action == 'zoom_in':
        renderer.tile_size = min(100, renderer.tile_size + 2)
    elif action == 'zoom_out':
        renderer.tile_size = max(4, renderer.tile_size - 2)
    
    if old_ts != renderer.tile_size:
        # Recalculate view width and height based on new tile size and FIXED viewport pixel area
        session.view_width = session.viewport_px_w // renderer.tile_size
        session.view_height = session.viewport_px_h // renderer.tile_size
        
        # Ensure camera and cursor remain valid
        session.camera_x = max(0, min(session.camera_x, session.map_obj.width - session.view_width))
        session.camera_y = max(0, min(session.camera_y, session.map_obj.height - session.view_height))
        
        renderer.invalidate_cache()
        show_message(manager, f"Zoom: {renderer.tile_size}px", notify=True)

def handle_measurement_toggle(session, manager, action=None):
    session.tool_state.measurement_active = not session.tool_state.measurement_active
    status = "ON" if session.tool_state.measurement_active else "OFF"
    show_message(manager, f"Measurement Mode: {status}", notify=True)

def handle_add_measurement_point(session, manager, action=None):
    ts = session.tool_state
    if not ts.measurement_active: return
    
    ts.measurement_config['points'].append((session.cursor_x, session.cursor_y))
    if len(ts.measurement_config['points']) > 10:
        ts.measurement_config['points'].pop(0)
    show_message(manager, f"Point added: {session.cursor_x}, {session.cursor_y}", notify=True)

def handle_goto_coords(session, manager, action=None):
    def on_coords(inp):
        if not inp: return
        try:
            if ',' in inp:
                parts = inp.split(',')
            else:
                parts = inp.split()
            
            if len(parts) >= 2:
                tx = int(parts[0].strip())
                ty = int(parts[1].strip())
                
                # Clamp and jump
                session.cursor_x = max(0, min(session.map_obj.width - 1, tx))
                session.cursor_y = max(0, min(session.map_obj.height - 1, ty))
                
                # Center camera on cursor
                session.camera_x = max(0, min(session.map_obj.width - session.view_width, session.cursor_x - session.view_width // 2))
                session.camera_y = max(0, min(session.map_obj.height - session.view_height, session.cursor_y - session.view_height // 2))
                
                show_message(manager, f"Jumped to {session.cursor_x}, {session.cursor_y}", notify=True)
        except:
            show_message(manager, "Invalid coordinates. Use 'X, Y'", notify=True)

    manager.flow.push_text_input("Go to (X, Y): ", on_coords)

def handle_measurement_configure(session, manager, action=None):
    ts = session.tool_state
    
    # Prepare fields for FormState
    color = ts.measurement_config.get('color', (0, 255, 255))
    color_str = f"{color[0]},{color[1]},{color[2]}"

    fields = [
        ["Grid Size", str(ts.measurement_config.get('grid_size', 100)), 'grid_size'],
        ["Show Coords", str(ts.measurement_config.get('show_coords', True)), 'show_coords'],
        ["Grid Color (R,G,B)", color_str, 'color'],
        ["Clear Points (y/n)", "n", 'clear_points']
    ]
    
    def on_save(data):
        if data:
            try:
                val = int(data.get('grid_size', 100))
                if val > 0: ts.measurement_config['grid_size'] = val
            except: pass
            
            sc_str = str(data.get('show_coords', 'True')).strip().lower()
            ts.measurement_config['show_coords'] = (sc_str == 'true')
            
            # Color parsing
            try:
                c_str = data.get('color', '0,255,255')
                parts = [int(p.strip()) for p in c_str.split(',')]
                if len(parts) >= 3:
                    ts.measurement_config['color'] = (parts[0], parts[1], parts[2])
            except: pass

            cp_str = str(data.get('clear_points', 'n')).strip().lower()
            if cp_str == 'y' or cp_str == 'yes':
                ts.measurement_config['points'] = []
            
            show_message(manager, "Measurement Config Saved", notify=True)
            
    manager.flow.push_form("Measurement Settings", fields, on_save)

def get_action_dispatcher():
    return {
        'quit': handle_quit,
        'editor_menu': handle_editor_menu,
        'open_context_menu': handle_open_context_menu,
        'zoom_in': handle_zoom, 'zoom_out': handle_zoom,
        'move_view_up': handle_move_view, 'move_view_down': handle_move_view,
        'move_view_left': handle_move_view, 'move_view_right': handle_move_view,
        'move_cursor_up': handle_move_cursor, 'move_cursor_down': handle_move_cursor,
        'move_cursor_left': handle_move_cursor, 'move_cursor_right': handle_move_cursor,
        'place_tile': handle_place_tile,
        'flood_fill': handle_flood_fill,
        'undo': handle_undo_redo, 'redo': handle_undo_redo,
        'select_start': handle_selection, 'clear_selection': handle_selection,
        'copy_selection': handle_selection, 'paste_selection': handle_selection,
        'rotate_selection': handle_rotate_selection_action,
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
        'goto_coords': handle_goto_coords,
        'save_map': handle_file_ops, 'load_map': handle_file_ops,
        'new_map': handle_file_ops, 'export_image': handle_file_ops,
        'macro_record_toggle': handle_macro_toggle,
        'macro_play': handle_macro_play,
        'toggle_measurement': handle_measurement_toggle,
        'measurement_menu': handle_measurement_configure,
        'add_measure_point': handle_add_measurement_point,
    }
