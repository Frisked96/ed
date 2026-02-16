from .utils import show_message

def handle_measurement(session, manager, action=None):
    session.tool_state.measure_start = (session.cursor_x, session.cursor_y)

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
