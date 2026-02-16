import pygame
from menu import (
    menu_save_map, menu_autosave_settings, menu_statistics
)
from .utils import show_message

# We need to import handlers for the context menu.
# To avoid circular imports at module level (if any exist), we can import inside the function
# or assume the architecture is clean enough.
# Since ui.py is a consumer of other actions, it should be fine to import them if they don't consume ui.py.

def handle_editor_menu(session, manager, action=None):
    flow = manager.flow
    def on_choice(choice):
        if choice == "Save Map":
            if menu_save_map(manager, manager.flow.renderer, session.map_obj):
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
            menu_autosave_settings(manager, manager.flow.renderer, session.tool_state)
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

def handle_statistics(session, manager, action=None):
    menu_statistics(manager, manager.flow.renderer, session.map_obj)

def handle_show_help(session, manager, action=None):
    manager.flow.push_help(session.bindings)

def handle_edit_controls(session, manager, action=None):
    manager.flow.push_control_settings(session.bindings)

def handle_open_context_menu(session, manager, action=None):
    from menu.base import ContextMenuState

    # Delayed imports to avoid circular dependency issues during package initialization
    # and to ensure all modules are fully loaded.
    from .select import handle_selection, handle_rotate_selection_action
    from .draw import handle_flood_fill, handle_tool_select, handle_toggle_palette
    from .view import handle_goto_coords
    from .file import handle_file_ops, handle_undo_redo
    from .measure import handle_measurement_configure, handle_measurement_toggle
    from .tiles import handle_tile_management

    from .macro import (
        handle_macro_toggle, handle_macro_play, handle_macro_select,
        handle_macro_set_iterations, handle_macro_toggle_until_end, handle_macro_set_offset
    )

    mouse_pos = pygame.mouse.get_pos()
    ts = session.tool_state

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
            ("Macro: " + ("Stop Recording" if ts.recording else "Start Recording"), lambda: handle_macro_toggle(session, manager)),
            ("Macro: Select", lambda: handle_macro_select(session, manager)),
            ("Macro: Play" + (f" ({ts.selected_macro})" if ts.selected_macro else ""), lambda: handle_macro_play(session, manager)),
            ("Macro: Iterations (" + str(ts.macro_iterations) + ")", lambda: handle_macro_set_iterations(session, manager)),
            ("Macro: Until End (" + ("ON" if ts.macro_until_end else "OFF") + ")", lambda: handle_macro_toggle_until_end(session, manager)),
            ("Macro: Offset (Manual)", lambda: handle_macro_set_offset(session, manager)),
            ("Macro: Offset (Horizontal 1,0)", lambda: setattr(ts, 'macro_offset', (1, 0)) or show_message(manager, "Offset set to Horizontal", notify=True)),
            ("Macro: Offset (Vertical 0,1)", lambda: setattr(ts, 'macro_offset', (0, 1)) or show_message(manager, "Offset set to Vertical", notify=True)),
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

def handle_toggle_fullscreen(session, manager, action=None):
    try:
        pygame.display.toggle_fullscreen()
    except Exception as e:
        print(f"Fullscreen toggle failed: {e}")

