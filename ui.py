import curses
import textwrap
from utils import get_key_name, get_distance

def init_color_pairs(tile_colors):
    curses.start_color()
    curses.use_default_colors()
    pairs = {}
    pair_num = 1
    for ch, col in tile_colors.items():
        curses.init_pair(pair_num, col, -1)
        pairs[ch] = pair_num
        pair_num += 1
    curses.init_pair(pair_num, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    pairs['__SELECTION__'] = pair_num
    return pairs

def draw_map(stdscr, map_data, camera_x, camera_y, view_width, view_height,
             cursor_x, cursor_y, selected_char, color_pairs,
             selection_start=None, selection_end=None, tool_state=None):
    max_y, max_x = stdscr.getmaxyx()
    view_width = min(view_width, max_x)
    view_height = min(view_height, max_y - 3)

    sel_coords = set()
    if selection_start and selection_end:
        x0, y0 = selection_start
        x1, y1 = selection_end
        for y in range(min(y0, y1), max(y0, y1) + 1):
            for x in range(min(x0, x1), max(x0, x1) + 1):
                sel_coords.add((x, y))

    for vy in range(view_height):
        my = camera_y + vy
        if my < 0 or my >= len(map_data): continue
        for vx in range(view_width):
            mx = camera_x + vx
            if mx < 0 or mx >= len(map_data[0]): continue

            ch = map_data[my][mx]
            pair = color_pairs.get(ch, 1)
            attr = curses.color_pair(pair)

            if (mx, my) in sel_coords:
                attr = curses.color_pair(color_pairs.get('__SELECTION__', 1))

            if my == cursor_y and mx == cursor_x:
                attr |= curses.A_REVERSE

            if tool_state and tool_state.start_point and tool_state.start_point[0] == mx and tool_state.start_point[1] == my:
                attr |= curses.A_BOLD | curses.A_UNDERLINE

            if tool_state and tool_state.measure_start and tool_state.measure_start[0] == mx and tool_state.measure_start[1] == my:
                attr |= curses.A_BOLD | curses.A_UNDERLINE

            try:
                stdscr.addch(vy, vx, ch, attr)
            except curses.error:
                pass

    return view_height

def draw_status(stdscr, y, map_width, map_height, camera_x, camera_y,
                cursor_x, cursor_y, selected_char, tool_state, undo_stack, bindings):
    max_y, max_x = stdscr.getmaxyx()

    status1 = f'Map:{map_width}x{map_height} Cam:({camera_x},{camera_y}) Cursor:({cursor_x},{cursor_y}) Tool:{tool_state.mode}'
    if tool_state.brush_size > 1:
        status1 += f' Brush:{tool_state.brush_size}'
    status1 += f' Seed:{tool_state.seed}'
    if tool_state.snap_size > 1:
        status1 += f' Snap:{tool_state.snap_size}'
    if tool_state.auto_tiling:
        status1 += f' AutoTile:On'
    if tool_state.measure_start:
        dist = get_distance(tool_state.measure_start, (cursor_x, cursor_y))
        status1 += f' Dist:{dist:.1f}'
    stdscr.addstr(y, 0, status1[:max_x-1])

    undo_str = f'Undo:{len(undo_stack.undo_stack)}' if undo_stack.can_undo() else ''
    redo_str = f'Redo:{len(undo_stack.redo_stack)}' if undo_stack.can_redo() else ''
    status2 = f'Tile:{selected_char} {undo_str} {redo_str} [{get_key_name(bindings["show_help"])}]=Help [{get_key_name(bindings["quit"])}]=Quit'
    stdscr.addstr(y+1, 0, status2[:max_x-1])


_help_cache = {
    "lines": None,
    "bindings": None,
    "size": None
}

def draw_help_overlay(stdscr, bindings):
    max_y, max_x = stdscr.getmaxyx()
    
    # Check cache
    if (_help_cache["lines"] and _help_cache["bindings"] == bindings and _help_cache["size"] == (max_y, max_x)):
        all_lines = _help_cache["lines"]
    else:
        help_sections = [
            ("MOVEMENT", [
                f"View: {get_key_name(bindings['move_view_up'])}/{get_key_name(bindings['move_view_down'])}/{get_key_name(bindings['move_view_left'])}/{get_key_name(bindings['move_view_right'])} (WASD) | Cursor: Arrow Keys"
            ]),
            ("DRAWING TOOLS", [
                f"{get_key_name(bindings['place_tile'])}=Place tile at cursor | {get_key_name(bindings['cycle_tile'])}=Cycle tiles | {get_key_name(bindings['pick_tile'])}=Pick from menu",
                f"{get_key_name(bindings['toggle_palette'])}=Quick Tile Palette",
                f"{get_key_name(bindings['flood_fill'])}=Flood fill area | {get_key_name(bindings['line_tool'])}=Line tool | {get_key_name(bindings['rect_tool'])}=Rectangle | {get_key_name(bindings['circle_tool'])}=Circle",
                f"Pattern Fill: {get_key_name(bindings['pattern_tool'])}=Pattern mode | {get_key_name(bindings['define_pattern'])}=Define pattern",
                f"Custom Brush: {get_key_name(bindings['define_brush'])}=Define brush shape",
                f"Brush size: {get_key_name(bindings['decrease_brush'])}/{get_key_name(bindings['increase_brush'])}"
            ]),
            ("SELECTION & CLIPBOARD", [
                f"{get_key_name(bindings['select_start'])}=Start/End selection | {get_key_name(bindings['clear_selection'])}=Clear selection",
                f"{get_key_name(bindings['copy_selection'])}=Copy | {get_key_name(bindings['paste_selection'])}=Paste",
                f"{get_key_name(bindings['rotate_selection'])}=Rotate 90° | {get_key_name(bindings['flip_h'])}=Flip horizontal | {get_key_name(bindings['flip_v'])}=Flip vertical"
            ]),
            ("EDIT OPERATIONS", [
                f"{get_key_name(bindings['undo'])}=Undo (100 levels) | {get_key_name(bindings['redo'])}=Redo | {get_key_name(bindings['replace_all'])}=Replace all tiles",
                f"{get_key_name(bindings['clear_area'])}=Clear selected area | {get_key_name(bindings['statistics'])}=Show tile statistics"
            ]),
            ("MAP TRANSFORMATIONS", [
                f"{get_key_name(bindings['map_rotate'])}=Rotate map 90° | {get_key_name(bindings['map_flip_h'])}=Flip H | {get_key_name(bindings['map_flip_v'])}=Flip V",
                f"Shift Map: Arrows (mapped keys) to shift entire map contents"
            ]),
            ("PROCEDURAL GENERATION", [
                f"{get_key_name(bindings['random_gen'])}=Cellular automata caves | {get_key_name(bindings['perlin_noise'])}=Perlin noise terrain",
                f"{get_key_name(bindings['voronoi'])}=Voronoi diagram regions | {get_key_name(bindings['set_seed'])}=Set random seed"
            ]),
            ("FILE OPERATIONS", [
                f"{get_key_name(bindings['new_map'])}=New map | {get_key_name(bindings['load_map'])}=Load | {get_key_name(bindings['save_map'])}=Save",
                f"{get_key_name(bindings['resize_map'])}=Resize map | {get_key_name(bindings['export_image'])}=Export PNG/CSV"
            ]),
            ("CONFIGURATION", [
                f"{get_key_name(bindings['define_tiles'])}=Define custom tiles | {get_key_name(bindings['edit_controls'])}=Edit keybindings"
            ]),
            ("MACROS & AUTOMATION", [
                f"{get_key_name(bindings['macro_record_toggle'])}=Toggle Macro Recording | {get_key_name(bindings['macro_play'])}=Play Macro",
                f"Macros record action names. Use the Macro Manager in the menu to define/edit."
            ]),
            ("MEASUREMENT & SNAPPING", [
                f"{get_key_name(bindings['toggle_snap'])}=Set Grid Snap Size | {get_key_name(bindings['set_measure'])}=Set/Clear Measurement Start",
                f"Distance is shown in the status bar from the measurement start to the cursor."
            ]),
            ("AUTO-TILING", [
                f"{get_key_name(bindings['toggle_autotile'])}=Toggle Auto-Tiling",
                f"Use the Auto-Tiling Manager in the main menu or editor menu (F1) to define rules."
            ]),
            ("EDITOR MENU", [
                f"{get_key_name(bindings['editor_menu'])}=Open Editor Pause Menu (F1)",
                f"The menu allows saving, loading, and managing macros without quitting."
            ])
        ]

        all_lines = ["=== MAP EDITOR HELP (ESC to close) ===", ""]
        for section_name, section_lines in help_sections:
            all_lines.append(f"--- {section_name} ---")
            for line in section_lines:
                wrapped = textwrap.wrap(line, max_x - 8)
                all_lines.extend(wrapped)
            all_lines.append("")

        _help_cache["lines"] = all_lines
        _help_cache["bindings"] = bindings
        _help_cache["size"] = (max_y, max_x)
    
    height = min(len(all_lines) + 2, max_y - 4)
    width = max_x - 4
    start_y = (max_y - height) // 2
    start_x = 2

    win = curses.newwin(height, width, start_y, start_x)
    win.keypad(True)
    win.border()

    scroll_offset = 0
    max_scroll = max(0, len(all_lines) - (height - 2))

    while True:
        win.clear()
        win.border()

        for i in range(height - 2):
            line_idx = scroll_offset + i
            if line_idx < len(all_lines):
                try:
                    win.addstr(i + 1, 2, all_lines[line_idx][:width-4])
                except:
                    pass

        win.refresh()
        key = win.getch()

        if key == 27:
            break
        elif key == curses.KEY_UP and scroll_offset > 0:
            scroll_offset -= 1
        elif key == curses.KEY_DOWN and scroll_offset < max_scroll:
            scroll_offset += 1
        elif key == curses.KEY_PPAGE:
            scroll_offset = max(0, scroll_offset - 10)
        elif key == curses.KEY_NPAGE:
            scroll_offset = min(max_scroll, scroll_offset + 10)


def draw_tile_palette(stdscr, tile_chars, color_pairs, selected_char):
    max_y, max_x = stdscr.getmaxyx()
    cols_count = max_x - 10
    rows = (len(tile_chars) // cols_count) + 1
    win_h = rows + 2
    win_w = max_x - 4

    win = curses.newwin(win_h, win_w, max_y - win_h - 3, 2)
    win.border()
    win.addstr(0, 2, " Tile Palette ")

    for i, ch in enumerate(tile_chars):
        attr = curses.color_pair(color_pairs.get(ch, 1))
        if ch == selected_char:
            attr |= curses.A_REVERSE | curses.A_BOLD

        try:
            win.addch(1 + (i // (win_w - 4)), 2 + (i % (win_w - 4)), ch, attr)
        except: pass

    win.refresh()

