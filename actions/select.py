from utils import rotate_selection_90
from .utils import check_autosave, show_message

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
        z = session.active_z_level
        session.clipboard = [[session.map_obj.get(x, y, z=z) for x in range(x0, x1+1)] for y in range(y0, y1+1)]
        show_message(manager, f"Copied {x1-x0+1}x{y1-y0+1} area", notify=True)
    elif action == 'paste_selection' and session.clipboard:
        session.map_obj.push_undo()
        z = session.active_z_level
        for dy, row in enumerate(session.clipboard):
            for dx, ch in enumerate(row):
                session.map_obj.set(session.cursor_x + dx, session.cursor_y + dy, ch, z=z)
        session.tool_state.edits_since_save += 1
        check_autosave(session, manager)
        show_message(manager, "Pasted area", notify=True)
    elif action == 'clear_area' and session.selection_start and session.selection_end:
        session.map_obj.push_undo()
        z = session.active_z_level
        for y in range(session.selection_start[1], session.selection_end[1]+1):
            for x in range(session.selection_start[0], session.selection_end[0]+1):
                session.map_obj.set(x, y, 0, z=z) # 0 is void
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
    z = session.active_z_level
    data = [[session.map_obj.get(x, y, z=z) for x in range(sx0, sx1+1)] for y in range(sy0, sy1+1)]

    # Rotate
    rotated = rotate_selection_90(data)
    new_h = len(rotated)
    new_w = len(rotated[0])

    session.map_obj.push_undo()

    # Clear old area
    for y in range(sy0, sy1+1):
        for x in range(sx0, sx1+1):
            session.map_obj.set(x, y, 0, z=z) # Clear to void

    # Calculate center
    cx = sx0 + w / 2
    cy = sy0 + h / 2
    nx = int(cx - new_w / 2)
    ny = int(cy - new_h / 2)

    # Paste rotated
    for dy, row in enumerate(rotated):
        for dx, val in enumerate(row):
            session.map_obj.set(nx + dx, ny + dy, val, z=z)

    # Update selection
    session.selection_start = (nx, ny)
    session.selection_end = (nx + new_w - 1, ny + new_h - 1)

    session.tool_state.edits_since_save += 1
    check_autosave(session, manager)
    show_message(manager, "Selection Rotated", notify=True)
