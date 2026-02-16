from .utils import show_message
from map_io import save_macros

def handle_macro_toggle(session, manager, action=None):
    ts = session.tool_state
    if ts.recording:
        ts.recording = False
        session.map_obj.on_tile_changed_callback = None
        
        if not ts.current_macro_tiles:
            show_message(manager, "Macro empty, cancelled", notify=True)
            return

        def on_name(name):
            if name:
                # Find bounding box or just use relative to first tile
                ts.macros[name] = {
                    'tiles': list(ts.current_macro_tiles),
                    'offset': ts.macro_offset # User might want to customize this
                }
                save_macros(ts.macros)
                show_message(manager, f"Macro '{name}' saved ({len(ts.current_macro_tiles)} tiles)", notify=True)
        manager.flow.push_text_input("Enter name for macro: ", on_name)
    else:
        ts.recording = True
        ts.current_macro_tiles = []
        ts.macro_origin = None
        
        def recording_cb(x, y, tid):
            if ts.macro_origin is None:
                ts.macro_origin = (x, y)
            
            dx = x - ts.macro_origin[0]
            dy = y - ts.macro_origin[1]
            # Avoid duplicates if multiple tools hit same tile? 
            # Actually just append, playback will just overwrite.
            ts.current_macro_tiles.append((dx, dy, tid))

        session.map_obj.on_tile_changed_callback = recording_cb
        show_message(manager, "Recording Macro (Relative)...", notify=True)

def handle_macro_play(session, manager, action=None):
    ts = session.tool_state
    if not ts.selected_macro or ts.selected_macro not in ts.macros:
        show_message(manager, "No macro selected", notify=True)
        return

    macro = ts.macros[ts.selected_macro]
    tiles = macro['tiles']
    
    start_x, start_y = session.cursor_x, session.cursor_y
    
    iterations = ts.macro_iterations
    if ts.macro_until_end:
        ox, oy = ts.macro_offset
        if ox == 0 and oy == 0:
            iterations = 1
        else:
            # Calculate steps to hit any boundary in the direction of the offset
            steps = []
            if ox > 0: steps.append((session.map_obj.width - 1 - start_x) // ox)
            elif ox < 0: steps.append(start_x // abs(ox))
            
            if oy > 0: steps.append((session.map_obj.height - 1 - start_y) // oy)
            elif oy < 0: steps.append(start_y // abs(oy))
            
            if steps:
                iterations = min(steps) + 1
            else:
                iterations = 1

    session.map_obj.push_undo()
    for i in range(iterations):
        base_x = start_x + i * ts.macro_offset[0]
        base_y = start_y + i * ts.macro_offset[1]
        
        for dx, dy, tid in tiles:
            session.map_obj.set(base_x + dx, base_y + dy, tid)
    
    show_message(manager, f"Macro '{ts.selected_macro}' played {iterations} times", notify=True)

def handle_macro_select(session, manager, action=None):
    ts = session.tool_state
    def on_select(name):
        if name in ts.macros:
            ts.selected_macro = name
            ts.mode = 'macro' # Switch to macro mode for preview/placement
            show_message(manager, f"Selected macro: {name}", notify=True)
    
    options = list(ts.macros.keys())
    if not options:
        show_message(manager, "No macros available", notify=True)
        return
        
    manager.flow.push_choice_selector("Select Macro", options, on_select)

def handle_macro_set_iterations(session, manager, action=None):
    def on_val(val):
        try:
            session.tool_state.macro_iterations = max(1, int(val))
        except: pass
    manager.flow.push_text_input("Iterations: ", on_val)

def handle_macro_toggle_until_end(session, manager, action=None):
    session.tool_state.macro_until_end = not session.tool_state.macro_until_end
    show_message(manager, f"Macro Until End: {session.tool_state.macro_until_end}", notify=True)

def handle_macro_set_offset(session, manager, action=None):
    def on_val(val):
        try:
            parts = val.split(',')
            session.tool_state.macro_offset = (int(parts[0]), int(parts[1]))
        except: pass
    manager.flow.push_text_input("Offset (dx, dy): ", on_val)
