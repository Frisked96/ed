from core import Map
from utils import rotate_selection_90, flip_selection_horizontal, flip_selection_vertical, shift_map
from .utils import check_autosave

def handle_map_transform(session, manager, action=None):
    session.map_obj.push_undo()
    if action == 'map_rotate':
        # Rotate all layers
        new_layers = {}
        for z, layer in session.map_obj.layers.items():
            new_layers[z] = rotate_selection_90(layer)

        new_map = Map(session.map_obj.height, session.map_obj.width, undo_stack=session.undo_stack)
        new_map.layers = new_layers
        session.map_obj = new_map
        session.camera_x = session.camera_y = 0
    elif action == 'map_flip_h':
        for z, layer in session.map_obj.layers.items():
            session.map_obj.layers[z] = flip_selection_horizontal(layer)
    elif action == 'map_flip_v':
        for z, layer in session.map_obj.layers.items():
            session.map_obj.layers[z] = flip_selection_vertical(layer)
    elif action.startswith('map_shift_'):
        dx, dy = 0, 0
        if 'up' in action: dy = -1
        elif 'down' in action: dy = 1
        elif 'left' in action: dx = -1
        elif 'right' in action: dx = 1
        for z, layer in session.map_obj.layers.items():
            session.map_obj.layers[z] = shift_map(layer, dx, dy)

    session.tool_state.edits_since_save += 1
    check_autosave(session, manager)

def handle_resize_map(session, manager, action=None):
    def on_resized(new_map):
        if new_map:
            session.map_obj = new_map
            session.map_obj.dirty = False
    manager.flow.push_resize_wizard(session.map_obj, session.view_width, session.view_height, on_resized)
