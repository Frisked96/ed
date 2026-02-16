from core import Map
from utils import rotate_selection_90, flip_selection_horizontal, flip_selection_vertical, shift_map
from .utils import check_autosave

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

def handle_resize_map(session, manager, action=None):
    def on_resized(new_map):
        if new_map:
            session.map_obj = new_map
            session.map_obj.dirty = False
    manager.flow.push_resize_wizard(session.map_obj, session.view_width, session.view_height, on_resized)
