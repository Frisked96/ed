import pygame
import textwrap
import numpy as np
from utils import get_key_name, get_distance
from core import COLOR_MAP

# Cache for rendered glyphs to avoid calling font.render every frame for every tile
_glyph_cache = {}

def get_glyph(font, char, color, bg_color=None, bold=False):
    key = (char, color, bg_color, bold)
    if key not in _glyph_cache:
        # We ignore bold for now or we could use a bold font variant if we had one
        # To strictly follow "bold", we might render twice with offset?
        # For now, just render.
        surf = font.render(char, True, color, bg_color)
        _glyph_cache[key] = surf
    return _glyph_cache[key]

def invalidate_cache():
    global _glyph_cache
    _glyph_cache = {}

def init_color_pairs(tile_colors):
    # No-op for pygame as we use RGB directly
    pass

def draw_map(context, map_data, camera_x, camera_y, view_width, view_height,
             cursor_x, cursor_y, selected_char, color_pairs,
             selection_start=None, selection_end=None, tool_state=None):

    screen = context.screen
    font = context.font
    tile_size = context.tile_size

    # Fill background (or just the map area)
    # screen.fill((0,0,0)) # Assumed handled by main loop or we overwrite

    sel_x0 = sel_y0 = sel_x1 = sel_y1 = -1
    if selection_start and selection_end:
        x0, y0 = selection_start
        x1, y1 = selection_end
        sel_x0, sel_x1 = (x0, x1) if x0 < x1 else (x1, x0)
        sel_y0, sel_y1 = (y0, y1) if y0 < y1 else (y1, y0)

    sp_x = sp_y = -1
    if tool_state and tool_state.start_point:
        sp_x, sp_y = tool_state.start_point

    ms_x = ms_y = -1
    if tool_state and tool_state.measure_start:
        ms_x, ms_y = tool_state.measure_start

    map_h, map_w = map_data.shape

    # We iterate over the VIEW dimensions
    for vy in range(view_height):
        my = camera_y + vy
        py = vy * tile_size # Pixel Y

        # Optimization: Don't draw outside screen
        if py >= context.height: break

        if my < 0 or my >= map_h:
            # Draw empty space
            continue

        for vx in range(view_width):
            mx = camera_x + vx
            px = vx * tile_size # Pixel X

            if px >= context.width: break

            if mx < 0 or mx >= map_w:
                ch = ' '
                color = (0, 0, 0)
            else:
                ch = map_data[my, mx]
                # Map char to color.
                # color_pairs in curses was a dict of {char: pair_index}.
                # Here we expect color_pairs to be meaningless or we need the actual color map.
                # Actually main.py passes `tile_colors`? No, it passes `color_pairs`.
                # Wait, `init_color_pairs` in curses returned a map of char -> index.
                # In pygame, we should pass `tile_colors` (char -> RGB) directly to `draw_map`.
                # But to preserve signature match with existing calls (until I update them),
                # I should check what is passed.
                # In main.py: `session.color_pairs = init_color_pairs(tile_colors)`
                # I should change `init_color_pairs` to just return `tile_colors` or similar.
                # Let's assume `color_pairs` IS `tile_colors` (char -> RGB) after my refactor of init.

                # Check if color_pairs is actually the dict we want
                # If it's the old int mapping, we have a problem.
                # I will ensure init_color_pairs returns tile_colors.

                color = color_pairs.get(ch, (255, 255, 255))
                if isinstance(color, int): # Fallback if it was an int
                     color = (255, 255, 255)

                bg_color = None

                # Selection logic
                if sel_x0 <= mx <= sel_x1 and sel_y0 <= my <= sel_y1:
                    bg_color = (100, 100, 0) # Yellowish selection background
                    color = (0, 0, 0) # Black text

                # Cursor logic
                if my == cursor_y and mx == cursor_x:
                    bg_color = (255, 255, 255) # White cursor block
                    color = (0, 0, 0)

                # Tool markers
                if (mx == sp_x and my == sp_y) or (mx == ms_x and my == ms_y):
                     color = (255, 0, 0) # Red highlight for start points
                     # Bold?

                # Draw background if needed
                if bg_color:
                    pygame.draw.rect(screen, bg_color, (px, py, tile_size, tile_size))

                # Draw char
                if ch != ' ':
                    glyph = get_glyph(font, ch, color)
                    # Center the glyph in the tile? Or top-left?
                    # Monospace font should fit.
                    screen.blit(glyph, (px, py))

    return view_height * tile_size # Return Y position for status bar

def draw_status(context, y_pos, map_width, map_height, camera_x, camera_y,
                cursor_x, cursor_y, selected_char, tool_state, undo_stack, bindings):
    screen = context.screen
    font = context.font
    tile_size = context.tile_size
    width = context.width

    # y_pos is in pixels now (returned from draw_map)
    # We add some padding
    y = y_pos + 10

    lines = []

    status1 = f'Cursor:({cursor_x},{cursor_y}) '
    if tool_state.measure_start:
        dist = get_distance(tool_state.measure_start, (cursor_x, cursor_y))
        status1 += f'Dist:{dist:.1f} '
    status1 += f'Tool:{tool_state.mode}'
    if tool_state.brush_size > 1:
        status1 += f' Br:{tool_state.brush_size}'
    if tool_state.snap_size > 1:
        status1 += f' Sn:{tool_state.snap_size}'
    if tool_state.auto_tiling:
        status1 += f' AT:On'
    lines.append(status1)

    status2 = f'Map:{map_width}x{map_height} Cam:({camera_x},{camera_y}) Seed:{tool_state.seed} Tile:{selected_char}'
    lines.append(status2)

    undo_str = f'Undo:{len(undo_stack.undo_stack)}' if undo_stack.can_undo() else ''
    redo_str = f'Redo:{len(undo_stack.redo_stack)}' if undo_stack.can_redo() else ''
    # Using get_key_name for bindings
    help_key = get_key_name(bindings.get('show_help', 63)) # 63 is '?'
    quit_key = get_key_name(bindings.get('quit', 113)) # 113 is 'q'
    status3 = f'{undo_str} {redo_str} [{help_key}]=Help [{quit_key}]=Quit'
    lines.append(status3)

    # Draw status background
    # pygame.draw.rect(screen, (50, 50, 50), (0, y, width, len(lines) * tile_size + 10))

    for i, line in enumerate(lines):
        surf = font.render(line, True, (200, 200, 200))
        screen.blit(surf, (10, y + i * (tile_size + 2)))

def draw_help_overlay(context, bindings):
    screen = context.screen
    font = context.font
    tile_size = context.tile_size
    w, h = context.width, context.height
    
    # Create help text
    help_sections = [
            ("MOVEMENT", [
                f"View: WASD | Cursor: Arrow Keys"
            ]),
            ("DRAWING TOOLS", [
                f"{get_key_name(bindings.get('place_tile'))}=Place | {get_key_name(bindings.get('cycle_tile'))}=Cycle | {get_key_name(bindings.get('pick_tile'))}=Pick",
                f"{get_key_name(bindings.get('toggle_palette'))}=Palette",
                f"{get_key_name(bindings.get('flood_fill'))}=Fill | {get_key_name(bindings.get('line_tool'))}=Line | {get_key_name(bindings.get('rect_tool'))}=Rect",
                f"{get_key_name(bindings.get('circle_tool'))}=Circle | {get_key_name(bindings.get('pattern_tool'))}=Pattern",
            ]),
            ("SELECTION & EDIT", [
                f"{get_key_name(bindings.get('select_start'))}=Sel Start/End | {get_key_name(bindings.get('clear_selection'))}=Clear",
                f"{get_key_name(bindings.get('copy_selection'))}=Copy | {get_key_name(bindings.get('paste_selection'))}=Paste",
                f"{get_key_name(bindings.get('undo'))}=Undo | {get_key_name(bindings.get('redo'))}=Redo",
            ]),
            ("FILE & GEN", [
                f"{get_key_name(bindings.get('save_map'))}=Save | {get_key_name(bindings.get('load_map'))}=Load",
                f"{get_key_name(bindings.get('random_gen'))}=Cave Gen | {get_key_name(bindings.get('perlin_noise'))}=Perlin",
            ]),
             ("OTHER", [
                f"{get_key_name(bindings.get('editor_menu'))}=Menu (F1) | {get_key_name(bindings.get('quit'))}=Quit",
            ])
    ]
    
    all_lines = ["=== HELP (ESC close) ==="]
    for section_name, lines in help_sections:
        all_lines.append(f"--- {section_name} ---")
        for line in lines:
            all_lines.append(line)
        all_lines.append("")

    # Calculate overlay size
    overlay_w = w - 100
    overlay_h = h - 100
    ox = 50
    oy = 50

    # Draw overlay background
    pygame.draw.rect(screen, (30, 30, 30), (ox, oy, overlay_w, overlay_h))
    pygame.draw.rect(screen, (200, 200, 200), (ox, oy, overlay_w, overlay_h), 2) # Border

    # Render text
    # Simple scrollable view? Or just fit?
    # Assuming it fits for now.
    line_h = tile_size + 2
    max_lines = (overlay_h - 20) // line_h

    scroll_offset = 0
    running = True

    while running:
        # Clear overlay area
        pygame.draw.rect(screen, (30, 30, 30), (ox + 2, oy + 2, overlay_w - 4, overlay_h - 4))

        for i in range(max_lines):
            idx = scroll_offset + i
            if idx < len(all_lines):
                surf = font.render(all_lines[idx], True, (255, 255, 255))
                screen.blit(surf, (ox + 10, oy + 10 + i * line_h))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_UP and scroll_offset > 0:
                    scroll_offset -= 1
                elif event.key == pygame.K_DOWN and scroll_offset < len(all_lines) - max_lines:
                    scroll_offset += 1
                elif event.key == pygame.K_PAGEUP:
                    scroll_offset = max(0, scroll_offset - 10)
                elif event.key == pygame.K_PAGEDOWN:
                    scroll_offset = min(len(all_lines) - max_lines, scroll_offset + 10)


def draw_tile_palette(context, tile_chars, color_pairs, selected_char):
    screen = context.screen
    font = context.font
    tile_size = context.tile_size
    w, h = context.width, context.height

    # Palette window at bottom
    palette_h = 100
    palette_y = h - palette_h - 10
    pygame.draw.rect(screen, (20, 20, 20), (0, palette_y, w, palette_h))
    pygame.draw.rect(screen, (100, 100, 100), (0, palette_y, w, palette_h), 1)

    x = 10
    y = palette_y + 10

    for ch in tile_chars:
        color = color_pairs.get(ch, (255, 255, 255))
        if isinstance(color, int): color = (255, 255, 255)

        # Highlight selected
        if ch == selected_char:
            pygame.draw.rect(screen, (100, 100, 100), (x - 2, y - 2, tile_size + 4, tile_size + 4), 1)

        glyph = get_glyph(font, ch, color)
        screen.blit(glyph, (x, y))

        x += tile_size + 10
        if x > w - 20:
            x = 10
            y += tile_size + 10
