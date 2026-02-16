from menu import menu_save_map
from .utils import check_autosave, show_message

def handle_quit(session, manager, action=None):
    flow = manager.flow
    if session.map_obj.dirty:
        def on_confirm(confirmed):
            if confirmed: flow.exit_to_menu()
        flow.push_confirmation("Unsaved! Quit anyway? (y/n): ", on_confirm)
    else:
        flow.exit_to_menu()

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
                if hasattr(manager.current_state, 'renderer'):
                    manager.current_state.renderer.invalidate_cache()
        manager.flow.push_load_map_wizard(session.view_width, session.view_height, _on_loaded)
    elif action == 'new_map':
        def _on_new(m):
             if m:
                 session.map_obj = m
                 session.map_obj.dirty = False
                 session.camera_x, session.camera_y = 0, 0
                 session.cursor_x, session.cursor_y = 0, 0
                 if hasattr(manager.current_state, 'renderer'):
                    manager.current_state.renderer.invalidate_cache()
        manager.flow.push_new_map_wizard(session.view_width, session.view_height, _on_new)
    elif action == 'export_image':
        manager.flow.push_export_wizard(session.map_obj)

def handle_undo_redo(session, manager, action=None):
    res = session.undo_stack.undo(session.map_obj.copy_data()) if action == 'undo' else session.undo_stack.redo(session.map_obj.copy_data())
    if res is not None:
        session.map_obj.data = res
        session.map_obj.dirty = True
        session.map_obj.trigger_full_update()
        session.selection_start = session.selection_end = None
        check_autosave(session, manager)
        show_message(manager, f"{action.capitalize()} successful", notify=True)
