import sys
import os
import time
import argparse
import shutil
import pygame
from core import Map, ToolState, EditorSession, DEFAULT_TILE_COLORS
from utils import parse_color_name
from map_io import load_config
from ui import init_color_pairs, draw_map, draw_status, draw_tile_palette, invalidate_cache
from menus import build_key_map, menu_save_map, menu_load_map, menu_new_map
from actions import get_action_dispatcher
from pygame_support import PygameContext

def editor(context, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros=None, tiling_rules=None):
    invalidate_cache()
    session = EditorSession(map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
    session.color_pairs = tile_colors # We use tile_colors directly as "pairs"
    session.map_obj.undo_stack = session.undo_stack
    
    session.key_map = build_key_map(bindings)
    dispatcher = get_action_dispatcher()

    # Ensure view fits
    session.view_width = min(view_width, context.cols)
    session.view_height = min(view_height, context.rows - 5)

    while session.running:
        # 1. Process Events
        events = context.get_events()

        # Helper to process key action
        def process_key(key, unicode_char=None):
            # ESC check
            if key == pygame.K_ESCAPE:
                ts = session.tool_state
                if ts.start_point: ts.start_point = None
                elif session.selection_start: session.selection_start, session.selection_end = None, None
                elif ts.measure_start: ts.measure_start = None
                else: ts.mode = 'place'
                return

            pending_actions = list(session.key_map.get(key, []))

            # Also try ordinal if it's a character
            if not pending_actions and unicode_char and unicode_char.isprintable():
                pending_actions = list(session.key_map.get(ord(unicode_char), []))

            while pending_actions:
                action = pending_actions.pop(0)

                if session.tool_state.recording and action not in ('macro_record_toggle', 'macro_play', 'editor_menu'):
                    session.tool_state.current_macro_actions.append(action)

                if action in dispatcher:
                    dispatcher[action](session, context, action)

        for event in events:
            if event.type == pygame.QUIT:
                # Quit safely? Or just exit?
                # Using handle_quit logic if we want confirmation
                dispatcher['quit'](session, context, 'quit')
                if not session.running:
                    return # Exit editor
            elif event.type == pygame.VIDEORESIZE:
                context.update_dimensions()
                # Update view size
                session.view_width = min(view_width, context.cols)
                session.view_height = min(view_height, context.rows - 5) # Reserve space for UI
                # Clamp camera
                session.camera_x = max(0, min(session.camera_x, session.map_obj.width - session.view_width))
                session.camera_y = max(0, min(session.camera_y, session.map_obj.height - session.view_height))
                invalidate_cache()
            elif event.type == pygame.KEYDOWN:
                process_key(event.key, event.unicode)

        # 2. Logic Updates (Autosave, Action Queue)
        ts = session.tool_state
        if session.action_queue:
            action = session.action_queue.popleft()
            if action in dispatcher:
                dispatcher[action](session, context, action)

        if ts.autosave_enabled and session.map_obj.dirty:
             if ts.autosave_mode == 'time':
                if time.time() - ts.last_autosave_time > ts.autosave_interval * 60:
                    menu_save_map(context, session.map_obj)
                    ts.last_autosave_time, ts.edits_since_save = time.time(), 0
             elif ts.autosave_mode == 'edits':
                if ts.edits_since_save >= ts.autosave_edits_threshold:
                    menu_save_map(context, session.map_obj)
                    ts.last_autosave_time, ts.edits_since_save = time.time(), 0

        # 3. Drawing
        context.clear()
        
        session.status_y = draw_map(context, session.map_obj.data, session.camera_x, session.camera_y, session.view_width, session.view_height,
                                   session.cursor_x, session.cursor_y, session.selected_char, session.color_pairs,
                                   session.selection_start, session.selection_end, session.tool_state)

        draw_status(context, session.status_y, session.map_obj.width, session.map_obj.height, session.camera_x, session.camera_y,
                   session.cursor_x, session.cursor_y, session.selected_char, session.tool_state, session.undo_stack, session.bindings)

        if session.tool_state.show_palette:
            draw_tile_palette(context, session.tile_chars, session.color_pairs, session.selected_char)

        context.flip()

def menu_main(context):
    view_width = context.cols
    view_height = context.rows - 5

    tile_colors = {ch: parse_color_name(col) for ch, col in DEFAULT_TILE_COLORS.items()}
    tile_chars = list(tile_colors.keys())
    bindings = load_config()
    macros, tiling_rules = {}, {}

    options = [
        "1. New Map",
        "2. Load Map",
        "3. Define Custom Tiles",
        "4. Macro Manager",
        "5. Edit Controls",
        "6. Auto-Tiling Manager",
        "7. Quit"
    ]

    autosave_name = "autosave_map.txt"

    while True:
        # Check autosave
        current_options = list(options)
        if os.path.exists(autosave_name):
             current_options.insert(2, "R. Restore from Autosave")

        context.clear()

        screen = context.screen
        font = context.font
        tile_size = context.tile_size

        screen.blit(font.render("=== ADVANCED MAP EDITOR ===", True, (255, 255, 255)), (10, 10))

        y = 50
        for opt in current_options:
            screen.blit(font.render(opt, True, (200, 200, 200)), (20, y))
            y += tile_size + 5

        screen.blit(font.render("Select option key...", True, (150, 150, 150)), (20, y + 20))
        context.flip()

        # Input loop
        for event in context.get_events():
            if event.type == pygame.QUIT:
                context.quit()
            elif event.type == pygame.KEYDOWN:
                key = event.key
                unicode_char = event.unicode

                # We check keys based on menu
                if key == pygame.K_1:
                    map_obj = menu_new_map(context, view_width, view_height)
                    if map_obj: editor(context, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
                elif key == pygame.K_2:
                    map_obj = menu_load_map(context, view_width, view_height)
                    if map_obj: editor(context, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
                elif (key == pygame.K_r) and os.path.exists(autosave_name):
                    try:
                        with open(autosave_name, 'r') as f: lines = [l.rstrip('\n') for l in f]
                        if lines:
                            w, h = max(len(l) for l in lines), len(lines)
                            rw, rh = max(w, view_width), max(h, view_height)
                            map_obj = Map(rw, rh)
                            for y, line in enumerate(lines):
                                for x, ch in enumerate(line): map_obj.set(x, y, ch)
                            map_obj.dirty = False
                            editor(context, map_obj, view_width, view_height, tile_chars, tile_colors, bindings, macros, tiling_rules)
                    except: pass
                elif key == pygame.K_3:
                    from menus import menu_define_tiles
                    menu_define_tiles(context, tile_chars, tile_colors)
                elif key == pygame.K_4:
                    from menus import menu_macros
                    menu_macros(context, ToolState(macros=macros))
                elif key == pygame.K_5:
                    from menus import menu_controls
                    menu_controls(context, bindings)
                elif key == pygame.K_6:
                    from menus import menu_define_autotiling
                    menu_define_autotiling(context, ToolState(tiling_rules=tiling_rules), tile_chars)
                elif key == pygame.K_7 or key == pygame.K_q:
                    context.quit()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Advanced Pygame Map Editor')
    parser.add_argument('--view-width', type=int, default=60)
    parser.add_argument('--view-height', type=int, default=30)
    args = parser.parse_args()

    # Calculate window size based on view size + padding
    # 60 * 20 = 1200
    # 30 * 20 = 600
    # Add status bar space: 5 rows
    win_w = args.view_width * 20
    win_h = (args.view_height + 10) * 20 # Extra space for palette and status

    context = PygameContext(width=win_w, height=win_h, tile_size=20)

    try:
        menu_main(context)
    except KeyboardInterrupt:
        context.quit()
