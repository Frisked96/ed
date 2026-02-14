from collections import Counter
import pygame
import sys
import os
import random
import numpy as np
from utils import get_key_name, parse_color_name, get_user_input
from core import COLOR_MAP
from map_io import save_config, export_to_image
from ui import invalidate_cache, get_glyph
from generation import cellular_automata_cave, perlin_noise_generation, voronoi_generation

def build_key_map(bindings):
    key_map = {}
    for action, key in bindings.items():
        if key not in key_map:
            key_map[key] = []
        key_map[key].append(action)
    return key_map

def get_map_statistics(map_obj):
    return Counter(map_obj.data.flatten())

def _render_menu_generic(context, title, lines, selected_idx=-1):
    screen = context.screen
    font = context.font
    tile_size = context.tile_size

    screen.fill((0, 0, 0))

    # Title
    title_surf = font.render(title, True, (255, 255, 255))
    screen.blit(title_surf, (10, 10))

    y = tile_size * 3
    for i, line in enumerate(lines):
        color = (255, 255, 255)
        bg_color = None

        if i == selected_idx:
            color = (0, 0, 0)
            bg_color = (200, 200, 200)

        if bg_color:
            pygame.draw.rect(screen, bg_color, (0, y, context.width, tile_size + 4))
            surf = font.render(line, True, color)
            screen.blit(surf, (10, y + 2))
        else:
            surf = font.render(line, True, color)
            screen.blit(surf, (10, y + 2))

        y += tile_size + 6

    pygame.display.flip()

def menu_controls(context, bindings):
    actions = list(bindings.keys())
    actions.sort()
    selected_idx = 0

    while True:
        max_y = context.height // context.tile_size
        max_x = context.width // context.tile_size

        lines = []
        # Header rendered manually below

        visible_actions = max_y - 12
        if visible_actions < 5: visible_actions = 5

        scroll_offset = 0
        if selected_idx >= visible_actions:
            scroll_offset = selected_idx - visible_actions + 1

        screen = context.screen
        font = context.font
        tile_size = context.tile_size
        screen.fill((0, 0, 0))

        screen.blit(font.render("=== EDIT CONTROLS ===", True, (255, 255, 255)), (10, 10))
        screen.blit(font.render("Action                          Key", True, (255, 255, 255)), (10, 2 * tile_size + 10))
        screen.blit(font.render("-" * 50, True, (255, 255, 255)), (10, 3 * tile_size + 10))

        y = 4 * tile_size + 10
        for i in range(visible_actions):
            idx = scroll_offset + i
            if idx >= len(actions): break
            action = actions[idx]
            key_val = bindings[action]
            key_name = get_key_name(key_val)
            line = f"{action:<30} {key_name}"

            fg = (255, 255, 255)
            bg = None
            if idx == selected_idx:
                fg = (0, 0, 0)
                bg = (200, 200, 200)
                pygame.draw.rect(screen, bg, (0, y, context.width, tile_size))

            surf = font.render(line, True, fg)
            screen.blit(surf, (10, y))
            y += tile_size

        screen.blit(font.render("Up/Down: select | PgUp/PgDn: scroll fast | Enter: change", True, (255, 255, 255)), (10, context.height - 4 * tile_size))
        screen.blit(font.render("[D] reset to defaults | [Q] back", True, (255, 255, 255)), (10, context.height - 3 * tile_size))
        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                key = event.key

                if key == pygame.K_UP and selected_idx > 0:
                    selected_idx -= 1
                elif key == pygame.K_DOWN and selected_idx < len(actions)-1:
                    selected_idx += 1
                elif key == pygame.K_PAGEUP:
                    selected_idx = max(0, selected_idx - 10)
                elif key == pygame.K_PAGEDOWN:
                    selected_idx = min(len(actions) - 1, selected_idx + 10)
                elif key == pygame.K_d:
                    # Reset confirmation logic omitted
                    pass
                elif key == pygame.K_RETURN:
                    action = actions[selected_idx]
                    screen.blit(font.render(f"Press new key for '{action[:20]}'...", True, (0, 255, 0)), (10, context.height - tile_size))
                    pygame.display.flip()

                    captured = False
                    while not captured:
                        for e in pygame.event.get():
                            if e.type == pygame.KEYDOWN:
                                if e.key != pygame.K_ESCAPE:
                                    val = e.key
                                    if e.unicode and e.unicode.isprintable():
                                        val = ord(e.unicode)
                                    bindings[action] = val
                                    save_config(bindings)
                                captured = True
                elif key == pygame.K_q or key == pygame.K_ESCAPE:
                    return bindings

def menu_pick_tile(context, tile_chars, tile_colors, color_pairs):
    selected_idx = 0
    cols_count = (context.width - 40) // (context.tile_size + 10)
    if cols_count < 1: cols_count = 1

    while True:
        context.screen.fill((0, 0, 0))
        title = context.font.render(" Select Tile (Arrows, Enter)", True, (255, 255, 255))
        context.screen.blit(title, (10, 10))

        x_start = 20
        y_start = 50
        x = x_start
        y = y_start

        for i, ch in enumerate(tile_chars):
            color = tile_colors.get(ch, (255, 255, 255))
            if isinstance(color, int): color = (255, 255, 255)

            if i == selected_idx:
                pygame.draw.rect(context.screen, (100, 100, 100), (x - 2, y - 2, context.tile_size + 4, context.tile_size + 4), 1)

            glyph = get_glyph(context.font, ch, color)
            context.screen.blit(glyph, (x, y))

            x += context.tile_size + 10
            if x > context.width - 40:
                x = x_start
                y += context.tile_size + 10

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_idx = max(0, selected_idx - cols_count)
                elif event.key == pygame.K_DOWN:
                    selected_idx = min(len(tile_chars) - 1, selected_idx + cols_count)
                elif event.key == pygame.K_LEFT:
                    selected_idx = max(0, selected_idx - 1)
                elif event.key == pygame.K_RIGHT:
                    selected_idx = min(len(tile_chars) - 1, selected_idx + 1)
                elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                    return tile_chars[selected_idx]
                elif event.key == pygame.K_ESCAPE:
                    return None

def menu_statistics(context, map_obj):
    stats = get_map_statistics(map_obj)
    total = sum(stats.values())

    lines = ["=== MAP STATISTICS ===", "", f"Total tiles: {total}", ""]
    for tile, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total * 100) if total > 0 else 0
        lines.append(f"'{tile}': {count} ({pct:.1f}%)")
    lines.append("")
    lines.append("Press any key to continue...")

    _render_menu_generic(context, "Statistics", lines)

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN or event.type == pygame.QUIT:
                waiting = False
        context.clock.tick(10)

def menu_save_map(context, map_obj):
    context.screen.fill((0,0,0))
    pygame.display.flip()
    filename = get_user_input(context, 10, 2, "Save map as: ")
    if not filename: return False

    if os.path.exists(filename):
         pass

    try:
        with open(filename, 'w') as f:
            for row in map_obj.data:
                f.write(''.join(row) + '\n')
        return True
    except Exception as e:
        print(e)
        return False

def menu_load_map(context, view_width, view_height):
    from core import Map
    context.screen.fill((0,0,0))
    pygame.display.flip()
    filename = get_user_input(context, 10, 2, "Load map from: ")
    if not filename or not os.path.exists(filename):
        return None

    try:
        with open(filename, 'r') as f:
            lines = [line.rstrip('\n') for line in f]

        if not lines:
            return None

        width = max(len(line) for line in lines) if lines else view_width
        height = len(lines)

        if height < view_height: height = view_height
        if width < view_width: width = view_width

        map_obj = Map(width, height)
        for y, line in enumerate(lines):
            for x, ch in enumerate(line):
                map_obj.set(x, y, ch)
        map_obj.dirty = False
        return map_obj
    except:
        return None

def menu_export_image(context, map_obj, tile_colors):
    context.screen.fill((0,0,0))
    pygame.display.flip()
    filename = get_user_input(context, 10, 2, "Export as (.png/.csv): ")
    if filename:
        if not filename.endswith('.png') and not filename.endswith('.csv'):
            filename += '.png'

        if filename.endswith('.png'):
            tile_size_input = get_user_input(context, 12, 2, "Tile size (default 8): ")
            tile_size = int(tile_size_input) if tile_size_input else 8
            try:
                export_to_image(map_obj.data, tile_colors, filename, tile_size)
            except Exception as e: print(e)
        elif filename.endswith('.csv'):
            try:
                with open(filename, 'w') as f:
                    for row in map_obj.data:
                        f.write(','.join(row) + '\n')
            except Exception as e: print(e)

def menu_new_map(context, view_width, view_height):
    from core import Map
    context.screen.fill((0,0,0))
    pygame.display.flip()

    w = view_width
    while True:
        inp = get_user_input(context, 2, 0, f"Map width (min {view_width}): ")
        if inp is None: return None
        try:
            if not inp:
                w = view_width
                break
            val = int(inp)
            if val >= view_width:
                w = val
                break
        except ValueError: pass

    h = view_height
    while True:
        inp = get_user_input(context, 3, 0, f"Map height (min {view_height}): ")
        if inp is None: return None
        try:
            if not inp:
                h = view_height
                break
            val = int(inp)
            if val >= view_height:
                h = val
                break
        except ValueError: pass

    border_input = get_user_input(context, 4, 0, "Border char (default #, . for none): ")
    if border_input is None: return None

    if not border_input or border_input == '.':
        border_char = None
    else:
        border_char = border_input[0]

    map_obj = Map(w, h)
    if border_char:
        for x in range(w):
            map_obj.set(x, 0, border_char)
            map_obj.set(x, h-1, border_char)
        for y in range(h):
            map_obj.set(0, y, border_char)
            map_obj.set(w-1, y, border_char)
        map_obj.dirty = False
    return map_obj

def menu_define_tiles(context, tile_chars, tile_colors):
    selected_idx = 0

    while True:
        lines = []
        lines.append("=== DEFINE TILES ===")
        lines.append("[A] Add | [E] Edit Color | [R] Remove | [Q] Back")
        lines.append("-" * 30)

        for i, ch in enumerate(tile_chars):
            col_rgb = tile_colors.get(ch, (255,255,255))
            lines.append(f"{ch} : {col_rgb}")

        context.screen.fill((0,0,0))
        y = 10
        for i, line in enumerate(lines):
            fg = (255,255,255)
            if i >= 3 and i - 3 == selected_idx:
                fg = (0, 255, 0)
            context.screen.blit(context.font.render(line, True, fg), (10, y))
            y += context.tile_size + 2

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_idx = max(0, selected_idx - 1)
                elif event.key == pygame.K_DOWN:
                    selected_idx = min(len(tile_chars) - 1, selected_idx + 1)
                elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
                    return
                elif event.key == pygame.K_a:
                    ch_in = get_user_input(context, 10, 2, "Char: ")
                    if ch_in and len(ch_in) == 1:
                        col_in = get_user_input(context, 11, 2, "Color (red, etc): ")
                        if col_in:
                            tile_colors[ch_in] = parse_color_name(col_in)
                            if ch_in not in tile_chars: tile_chars.append(ch_in)
                elif event.key == pygame.K_r:
                     if tile_chars:
                         ch = tile_chars[selected_idx]
                         tile_chars.pop(selected_idx)
                         if ch in tile_colors: del tile_colors[ch]
                         selected_idx = max(0, min(selected_idx, len(tile_chars)-1))

def menu_random_generation(context, map_obj, seed=None):
    context.screen.fill((0,0,0))
    pygame.display.flip()
    inp = get_user_input(context, 2, 0, "Iterations (3-10, default 5): ")
    if inp is None: return False
    try:
        iterations = int(inp or "5")
        iterations = max(3, min(10, iterations))
    except: iterations = 5

    wall_in = get_user_input(context, 3, 0, "Wall char (default #): ")
    wall = wall_in[0] if wall_in else '#'

    floor_in = get_user_input(context, 4, 0, "Floor char (default .): ")
    floor = floor_in[0] if floor_in else '.'

    cellular_automata_cave(map_obj, iterations, wall, floor, seed)
    return True

def menu_perlin_generation(context, map_obj, tile_chars, seed=0):
    context.screen.fill((0,0,0))
    pygame.display.flip()
    perlin_noise_generation(map_obj, tile_chars, 10.0, 4, 0.5, seed)
    return True

def menu_voronoi_generation(context, map_obj, tile_chars, seed=None):
    context.screen.fill((0,0,0))
    pygame.display.flip()
    voronoi_generation(map_obj, tile_chars, 20, seed)
    return True

def menu_resize_map(context, map_obj, view_width, view_height):
    from core import Map
    context.screen.fill((0,0,0))
    pygame.display.flip()
    w = map_obj.width
    inp = get_user_input(context, 2, 0, f"New width: ")
    if inp: w = int(inp)

    h = map_obj.height
    inp = get_user_input(context, 3, 0, f"New height: ")
    if inp: h = int(inp)
    
    if w == map_obj.width and h == map_obj.height: return None
    new_map = Map(w, h)
    copy_h = min(h, map_obj.height)
    copy_w = min(w, map_obj.width)
    new_map.data[:copy_h, :copy_w] = map_obj.data[:copy_h, :copy_w]
    return new_map

def menu_set_seed(context, current_seed):
    context.screen.fill((0,0,0))
    pygame.display.flip()
    inp = get_user_input(context, 3, 0, "New seed (integer): ")
    if inp:
        try: return int(inp)
        except: pass
    return current_seed

def menu_autosave_settings(context, tool_state):
    selected = 0
    options = ["1. Enabled", "2. Mode", "3. Interval/Threshold", "4. Filename", "5. Back"]

    while True:
        lines = ["=== AUTOSAVE SETTINGS ==="]
        lines.append(f"1. Enabled: {'Yes' if tool_state.autosave_enabled else 'No'}")
        lines.append(f"2. Mode: {tool_state.autosave_mode.capitalize()}")
        if tool_state.autosave_mode == 'time':
            lines.append(f"3. Interval: {tool_state.autosave_interval} min")
        else:
            lines.append(f"3. Threshold: {tool_state.autosave_edits_threshold} edits")
        lines.append(f"4. Filename: {tool_state.autosave_filename}")
        lines.append("5. Back")

        _render_menu_generic(context, "AUTOSAVE", lines, selected)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP: selected = max(0, selected - 1)
                elif event.key == pygame.K_DOWN: selected = min(len(lines)-2, selected + 1)
                elif event.key == pygame.K_RETURN:
                    if selected == 0: tool_state.autosave_enabled = not tool_state.autosave_enabled
                    elif selected == 1: tool_state.autosave_mode = 'edits' if tool_state.autosave_mode == 'time' else 'time'
                    elif selected == 2:
                        if tool_state.autosave_mode == 'time':
                            val = get_user_input(context, 10, 0, "Interval (min): ")
                            if val: tool_state.autosave_interval = int(val)
                        else:
                            val = get_user_input(context, 10, 0, "Threshold: ")
                            if val: tool_state.autosave_edits_threshold = int(val)
                    elif selected == 3:
                        val = get_user_input(context, 10, 0, "Filename: ")
                        if val: tool_state.autosave_filename = val
                    elif selected == 4: return
                elif event.key == pygame.K_ESCAPE: return

def menu_editor_pause(context):
    options = ["Resume", "Save Map", "Load Map", "Macro Manager", "Auto-Tiling Manager", "Autosave Settings", "Exit to Main Menu", "Quit Editor"]
    selected = 0

    while True:
        _render_menu_generic(context, "=== EDITOR MENU ===", options, selected)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = max(0, selected - 1)
                elif event.key == pygame.K_DOWN:
                    selected = min(len(options) - 1, selected + 1)
                elif event.key == pygame.K_RETURN:
                    return options[selected]
                elif event.key == pygame.K_ESCAPE:
                    return "Resume"

def menu_macros(context, tool_state):
    selected = 0

    while True:
        macros = list(tool_state.macros.keys())
        lines = ["=== MACROS ===", "[A] Add | [R] Remove | [Q] Back"]
        for m in macros:
            lines.append(m)

        _render_menu_generic(context, "MACROS", lines, selected + 2)

        for event in pygame.event.get():
             if event.type == pygame.KEYDOWN:
                 if event.key == pygame.K_q or event.key == pygame.K_ESCAPE: return
                 elif event.key == pygame.K_a:
                     name = get_user_input(context, 10, 0, "Name: ")
                     if name:
                         # Stub actions input
                         actions = get_user_input(context, 11, 0, "Actions (comma sep): ")
                         tool_state.macros[name] = actions.split(',') if actions else []
                 elif event.key == pygame.K_r:
                     if macros:
                         del tool_state.macros[macros[selected]]
                         selected = max(0, selected - 1)
                 elif event.key == pygame.K_DOWN: selected = min(len(macros)-1, selected+1)
                 elif event.key == pygame.K_UP: selected = max(0, selected-1)


def menu_define_autotiling(context, tool_state, tile_chars):
    selected_idx = 0
    bases = list(tool_state.tiling_rules.keys())

    while True:
        # List bases
        lines = ["=== AUTO-TILING ===", "[A] Add Base | [R] Remove | [E] Edit Rules | [Q] Back"]
        for b in bases:
            count = len(tool_state.tiling_rules[b])
            lines.append(f"Base '{b}': {count} rules")

        _render_menu_generic(context, "AUTO-TILING", lines, selected_idx + 2)

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q or event.key == pygame.K_ESCAPE: return
                elif event.key == pygame.K_UP: selected_idx = max(0, selected_idx - 1)
                elif event.key == pygame.K_DOWN: selected_idx = min(len(bases) - 1, selected_idx + 1)
                elif event.key == pygame.K_a:
                    base = get_user_input(context, 10, 0, "Base Char: ")
                    if base and len(base)==1:
                        if base not in tool_state.tiling_rules:
                             tool_state.tiling_rules[base] = {}
                             bases = list(tool_state.tiling_rules.keys())
                elif event.key == pygame.K_r and bases:
                    del tool_state.tiling_rules[bases[selected_idx]]
                    bases = list(tool_state.tiling_rules.keys())
                    selected_idx = max(0, selected_idx-1)
                elif event.key == pygame.K_e and bases:
                    # Edit rules for base
                    base = bases[selected_idx]
                    rule_idx = 0
                    while True:
                        rlines = [f"=== RULES FOR '{base}' ===", "Use Up/Down to select mask, Enter to edit"]
                        for m in range(1, 16):
                            binary = bin(m)[2:].zfill(4)
                            curr = tool_state.tiling_rules[base].get(m, "")
                            rlines.append(f"Mask {m:2} ({binary}): {curr}")

                        _render_menu_generic(context, f"RULES {base}", rlines, rule_idx + 2)

                        ev = pygame.event.wait()
                        if ev.type == pygame.KEYDOWN:
                            if ev.key == pygame.K_ESCAPE: break
                            elif ev.key == pygame.K_UP: rule_idx = max(0, rule_idx - 1)
                            elif ev.key == pygame.K_DOWN: rule_idx = min(14, rule_idx + 1)
                            elif ev.key == pygame.K_RETURN:
                                mask = rule_idx + 1
                                val = get_user_input(context, 10, 0, f"Variant for mask {mask}: ")
                                if val: tool_state.tiling_rules[base][mask] = val[0]
                        elif ev.type == pygame.QUIT: sys.exit()

def menu_define_brush(context):
    size = 3
    brush = [[False for _ in range(size)] for _ in range(size)]
    by, bx = 0, 0

    while True:
        context.screen.fill((0,0,0))
        context.screen.blit(context.font.render(f"Brush {size}x{size} (Space=Toggle, Enter=Save)", True, (255,255,255)), (10,10))

        # Draw grid
        start_x, start_y = 50, 50
        cell_s = 30

        for r in range(size):
            for c in range(size):
                rect = (start_x + c * cell_s, start_y + r * cell_s, cell_s, cell_s)
                color = (200, 200, 200) if brush[r][c] else (50, 50, 50)
                pygame.draw.rect(context.screen, color, rect)
                pygame.draw.rect(context.screen, (255, 255, 255), rect, 1)

                if r == by and c == bx:
                    pygame.draw.rect(context.screen, (255, 0, 0), rect, 2)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP and by > 0: by -= 1
                elif event.key == pygame.K_DOWN and by < size - 1: by += 1
                elif event.key == pygame.K_LEFT and bx > 0: bx -= 1
                elif event.key == pygame.K_RIGHT and bx < size - 1: bx += 1
                elif event.key == pygame.K_SPACE: brush[by][bx] = not brush[by][bx]
                elif event.key == pygame.K_RETURN: return brush
                elif event.key == pygame.K_ESCAPE: return None

def menu_define_pattern(context, tile_chars, tile_colors):
    size = 2
    # Ask size
    inp = get_user_input(context, 2, 0, "Pattern size (max 5): ")
    if inp:
        try: size = max(1, min(5, int(inp)))
        except: pass

    pattern = [['.' for _ in range(size)] for _ in range(size)]
    by, bx = 0, 0

    while True:
        context.screen.fill((0,0,0))
        context.screen.blit(context.font.render(f"Pattern {size}x{size} (Enter char, Space=Cycle)", True, (255,255,255)), (10,10))

        start_x, start_y = 50, 50
        cell_s = 30

        for r in range(size):
            for c in range(size):
                rect = (start_x + c * cell_s, start_y + r * cell_s, cell_s, cell_s)
                pygame.draw.rect(context.screen, (50, 50, 50), rect)
                pygame.draw.rect(context.screen, (255, 255, 255), rect, 1)

                if r == by and c == bx:
                    pygame.draw.rect(context.screen, (255, 0, 0), rect, 2)

                glyph = get_glyph(context.font, pattern[r][c], (255,255,255))
                context.screen.blit(glyph, (rect[0]+5, rect[1]+5))

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: return None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP and by > 0: by -= 1
                elif event.key == pygame.K_DOWN and by < size - 1: by += 1
                elif event.key == pygame.K_LEFT and bx > 0: bx -= 1
                elif event.key == pygame.K_RIGHT and bx < size - 1: bx += 1
                elif event.key == pygame.K_RETURN: return pattern
                elif event.key == pygame.K_ESCAPE: return None
                elif event.unicode and event.unicode.isprintable():
                    pattern[by][bx] = event.unicode
