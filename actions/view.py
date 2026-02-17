from .utils import show_message

def handle_move_view(session, manager, action=None):
    speed = getattr(session, 'camera_speed', 1)
    if action == 'move_view_up':
        session.camera_y = max(0, session.camera_y - speed)
    elif action == 'move_view_down':
        session.camera_y = max(0, min(session.map_obj.height - session.view_height, session.camera_y + speed))
    elif action == 'move_view_left':
        session.camera_x = max(0, session.camera_x - speed)
    elif action == 'move_view_right':
        session.camera_x = max(0, min(session.map_obj.width - session.view_width, session.camera_x + speed))

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
