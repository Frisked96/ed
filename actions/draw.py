from drawing import place_tile_at, flood_fill, draw_line, draw_rectangle, draw_circle
from utils import get_distance
from menu import menu_define_brush, menu_define_pattern
from .utils import check_autosave, show_message

def handle_place_tile(session, manager, action=None):
    ts = session.tool_state
    if ts.mode == 'place':
        old_val = session.map_obj.get(session.cursor_x, session.cursor_y)
        if old_val != session.selected_tile_id:
            session.map_obj.push_undo()
            place_tile_at(session.map_obj, session.cursor_x, session.cursor_y, session.selected_tile_id, ts.brush_size, ts.brush_shape, ts)
            ts.edits_since_save += 1
            check_autosave(session, manager)
    elif ts.mode in ('line', 'rect', 'circle', 'pattern', 'select'):
        if ts.start_point is None:
            ts.start_point = (session.cursor_x, session.cursor_y)
        else:
            if ts.mode == 'select':
                x0, y0 = ts.start_point
                x1, y1 = session.cursor_x, session.cursor_y
                session.selection_start = (min(x0, x1), min(y0, y1))
                session.selection_end = (max(x0, x1), max(y0, y1))
                ts.start_point = None
                show_message(manager, "Area Selected", notify=True)
            elif ts.mode == 'line':
                session.map_obj.push_undo()
                draw_line(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, session.selected_tile_id, ts.brush_size, ts.brush_shape, ts)
                ts.start_point = None
                ts.edits_since_save += 1
                check_autosave(session, manager)
            elif ts.mode == 'rect':
                def on_rect_confirm(filled):
                    session.map_obj.push_undo()
                    draw_rectangle(session.map_obj, ts.start_point[0], ts.start_point[1], session.cursor_x, session.cursor_y, session.selected_tile_id, filled, ts.brush_size, ts.brush_shape, ts)
                    ts.start_point = None
                    ts.edits_since_save += 1
                    check_autosave(session, manager)

                if ts.shape_fill_mode == 'fill':
                    on_rect_confirm(True)
                elif ts.shape_fill_mode == 'outline':
                    on_rect_confirm(False)
                else:
                    manager.flow.push_confirmation("Filled? (y/n): ", on_rect_confirm)
            elif ts.mode == 'circle':
                def on_circle_confirm(filled):
                    session.map_obj.push_undo()
                    radius = int(get_distance(ts.start_point, (session.cursor_x, session.cursor_y)))
                    draw_circle(session.map_obj, ts.start_point[0], ts.start_point[1], radius, session.selected_tile_id, filled, ts.brush_size, ts.brush_shape, ts)
                    ts.start_point = None
                    ts.edits_since_save += 1
                    check_autosave(session, manager)

                if ts.shape_fill_mode == 'fill':
                    on_circle_confirm(True)
                elif ts.shape_fill_mode == 'outline':
                    on_circle_confirm(False)
                else:
                    manager.flow.push_confirmation("Filled? (y/n): ", on_circle_confirm)

def handle_flood_fill(session, manager, action=None):
    old_char = session.map_obj.get(session.cursor_x, session.cursor_y)
    if old_char != session.selected_tile_id:
        session.map_obj.push_undo()
        flood_fill(session.map_obj, session.cursor_x, session.cursor_y, session.selected_tile_id)
        session.tool_state.edits_since_save += 1
        check_autosave(session, manager)

def handle_brush_size(session, manager, action=None):
    if action == 'increase_brush':
        session.tool_state.brush_size = min(session.tool_state.brush_size + 1, 10)
    elif action == 'decrease_brush':
        session.tool_state.brush_size = max(session.tool_state.brush_size - 1, 1)

def handle_tool_select(session, manager, action=None):
    ts = session.tool_state
    ts.mode = action.split('_')[0]
    ts.start_point = None

def handle_define_pattern(session, manager, action=None):
    def on_pattern(pattern):
        if pattern:
            session.tool_state.pattern = pattern
            show_message(manager, "Pattern defined", notify=True)
    menu_define_pattern(manager, on_pattern)

def handle_define_brush(session, manager, action=None):
    def on_brush(brush):
        if brush:
            session.tool_state.brush_shape = brush
            show_message(manager, "Brush defined", notify=True)
    menu_define_brush(manager, on_brush)

def handle_toggle_snap(session, manager, action=None):
    def on_snap(inp):
        try:
            session.tool_state.snap_size = int(inp or "1")
        except: pass
    manager.flow.push_text_input("Enter snap size: ", on_snap)

def handle_toggle_palette(session, manager, action=None):
    session.tool_state.show_palette = not session.tool_state.show_palette

def handle_toggle_autotile(session, manager, action=None):
    session.tool_state.auto_tiling = not session.tool_state.auto_tiling
