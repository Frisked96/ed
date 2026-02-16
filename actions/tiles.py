from tiles import REGISTRY
from .utils import check_autosave, show_message

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
