from .file import handle_quit, handle_file_ops, handle_undo_redo
from .ui import (
    handle_editor_menu, handle_open_context_menu, handle_statistics,
    handle_show_help, handle_edit_controls, handle_toggle_fullscreen
)
from .view import handle_zoom, handle_move_view, handle_move_cursor, handle_goto_coords
from .draw import (
    handle_place_tile, handle_flood_fill, handle_brush_size, handle_tool_select,
    handle_define_pattern, handle_define_brush, handle_toggle_snap,
    handle_toggle_palette, handle_toggle_autotile
)
from .select import handle_selection, handle_rotate_selection_action
from .transform import handle_map_transform, handle_resize_map
from .generate import handle_generation, handle_set_seed
from .tiles import handle_tile_management, handle_replace_all
from .macro import (
    handle_macro_toggle, handle_macro_play, handle_macro_select,
    handle_macro_set_iterations, handle_macro_toggle_until_end, handle_macro_set_offset,
    handle_macro_auto_offset
)
from .measure import (
    handle_measurement, handle_measurement_toggle,
    handle_measurement_configure, handle_add_measurement_point
)

def get_action_dispatcher():
    return {
        'quit': handle_quit,
        'editor_menu': handle_editor_menu,
        'open_context_menu': handle_open_context_menu,
        'zoom_in': handle_zoom, 'zoom_out': handle_zoom,
        'move_view_up': handle_move_view, 'move_view_down': handle_move_view,
        'move_view_left': handle_move_view, 'move_view_right': handle_move_view,
        'move_cursor_up': handle_move_cursor, 'move_cursor_down': handle_move_cursor,
        'move_cursor_left': handle_move_cursor, 'move_cursor_right': handle_move_cursor,
        'place_tile': handle_place_tile,
        'flood_fill': handle_flood_fill,
        'undo': handle_undo_redo, 'redo': handle_undo_redo,
        'select_start': handle_selection, 'clear_selection': handle_selection,
        'copy_selection': handle_selection, 'paste_selection': handle_selection,
        'rotate_selection': handle_rotate_selection_action,
        'clear_area': handle_selection,
        'map_rotate': handle_map_transform, 'map_flip_h': handle_map_transform, 'map_flip_v': handle_map_transform,
        'map_shift_up': handle_map_transform, 'map_shift_down': handle_map_transform,
        'map_shift_left': handle_map_transform, 'map_shift_right': handle_map_transform,
        'random_gen': handle_generation, 'perlin_noise': handle_generation, 'voronoi': handle_generation,
        'cycle_tile': handle_tile_management, 'pick_tile': handle_tile_management, 'define_tiles': handle_tile_management,
        'replace_all': handle_replace_all,
        'increase_brush': handle_brush_size, 'decrease_brush': handle_brush_size,
        'set_measure': handle_measurement,
        'line_tool': handle_tool_select, 'rect_tool': handle_tool_select,
        'circle_tool': handle_tool_select, 'pattern_tool': handle_tool_select,
        'define_pattern': handle_define_pattern, 'define_brush': handle_define_brush,
        'toggle_snap': handle_toggle_snap, 'toggle_palette': handle_toggle_palette,
        'toggle_autotile': handle_toggle_autotile,
        'resize_map': handle_resize_map, 'set_seed': handle_set_seed,
        'statistics': handle_statistics, 'show_help': handle_show_help,
        'edit_controls': handle_edit_controls,
        'goto_coords': handle_goto_coords,
        'save_map': handle_file_ops, 'load_map': handle_file_ops,
        'new_map': handle_file_ops, 'export_image': handle_file_ops,
        'macro_record_toggle': handle_macro_toggle,
        'macro_play': handle_macro_play,
        'macro_select': handle_macro_select,
        'macro_set_iterations': handle_macro_set_iterations,
        'macro_toggle_until_end': handle_macro_toggle_until_end,
        'macro_set_offset': handle_macro_set_offset,
        'macro_auto_offset': handle_macro_auto_offset,
        'toggle_measurement': handle_measurement_toggle,
        'measurement_menu': handle_measurement_configure,
        'add_measure_point': handle_add_measurement_point,
        'toggle_fullscreen': handle_toggle_fullscreen,
    }
