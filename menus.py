from collections import Counter
import pygame
import sys
import os
import random
import time
import numpy as np
from statemachine import StateMachine, State as SMState
from state_engine import State
from utils import get_key_name, parse_color_name, get_user_input, get_user_confirmation, get_all_colors, get_color_name
from core import COLOR_MAP
from map_io import save_config, export_to_image
from generation import cellular_automata_cave, perlin_noise_generation, voronoi_generation
from tiles import REGISTRY

def build_key_map(bindings):
    key_map = {}
    for action, key_name in bindings.items():
        if not key_name or key_name == 'None':
            continue
        
        # Preserve case for single characters (v vs V), lowercase for others (Space, UP)
        if len(key_name) > 1:
            key_lookup = key_name.lower()
        else:
            key_lookup = key_name
        
        if key_lookup not in key_map:
            key_map[key_lookup] = []
        key_map[key_lookup].append(action)
    return key_map

def get_map_statistics(map_obj):
    return Counter(map_obj.data.flatten())

def _render_menu_generic(context, title, lines, selected_idx=-1):
    screen = context.screen
    font = context.font
    tile_size = context.tile_size

    # Calculate required dimensions
    max_w = max([font.size(line)[0] for line in lines] + [font.size(title)[0]]) + 40
    total_h = (len(lines) + 2) * (tile_size + 6) + 40
    
    # Center the box
    bx = (context.width - max_w) // 2
    by = (context.height - total_h) // 2
    
    # Draw semi-transparent panel
    overlay = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
    overlay.fill((30, 30, 30, 230)) # Dark gray with alpha
    screen.blit(overlay, (bx, by))
    pygame.draw.rect(screen, (200, 200, 200), (bx, by, max_w, total_h), 2) # Border

    # Title
    title_surf = font.render(title, True, (0, 255, 255))
    screen.blit(title_surf, (bx + 20, by + 15))

    y = by + tile_size + 30
    for i, line in enumerate(lines):
        color = (255, 255, 255)
        bg_color = None

        if i == selected_idx:
            color = (0, 0, 0)
            bg_color = (200, 200, 200)
            pygame.draw.rect(screen, bg_color, (bx + 5, y - 2, max_w - 10, tile_size + 4))

        surf = font.render(line, True, color)
        screen.blit(surf, (bx + 20, y))
        y += tile_size + 6

class ColorPickerMachine(StateMachine):
    selecting = SMState(initial=True)
    typing_custom = SMState()
    
    start_custom = selecting.to(typing_custom)
    finish = (selecting.to.itself(internal=True) | typing_custom.to.itself(internal=True))

class ColorPickerState(State):
    def __init__(self, manager, context, callback):
        super().__init__(manager)
        self.context = context
        self.callback = callback
        self.machine = ColorPickerMachine()
        self.colors = get_all_colors()
        self.names = sorted(list(self.colors.keys()))
        self.options = self.names + ["Enter Custom Name/RGB"]
        self.selected = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        if self.machine.current_state == ColorPickerMachine.selecting:
            if event.key == pygame.K_UP:
                self.selected = (self.selected - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected = (self.selected + 1) % len(self.options)
            elif event.key == pygame.K_ESCAPE:
                self.manager.pop()
            elif event.key == pygame.K_RETURN:
                if self.selected < len(self.names):
                    self.callback(self.names[self.selected])
                    self.manager.pop()
                else:
                    self.machine.start_custom()
                    val = get_user_input(self.context, 0, 0, "Color Name or R,G,B: ")
                    if val:
                        self.callback(val)
                    self.manager.pop()

    def draw(self, surface):
        lines = [opt.capitalize() if i < len(self.names) else opt 
                 for i, opt in enumerate(self.options)]
        _render_menu_generic(self.context, "SELECT COLOR", lines, self.selected)

def menu_pick_color(context, redraw_bg=None):
    # Deprecated: replaced by ColorPickerState
    pass

def _menu_form(context, title, fields, redraw_bg=None):
    selected = 0
    options = fields + [["", "", "spacer"], ["Apply", "", "apply"], ["Cancel", "", "cancel"]]

    while True:
        # 1. Draw the background (the previous menu)
        if redraw_bg:
            redraw_bg()
        
        # 2. Calculate dialog dimensions
        max_w = max([context.font.size(f"{f[0]}: {f[1]}")[0] for f in fields] + [context.font.size(title)[0]]) + 80
        total_h = (len(options)) * (context.tile_size + 10) + 60
        
        bx = (context.width - max_w) // 2
        by = (context.height - total_h) // 2

        # 3. Draw the Dialog Box (on top of background)
        dialog_surf = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
        dialog_surf.fill((50, 50, 70, 250)) # Distinct color for dialog
        context.screen.blit(dialog_surf, (bx, by))
        pygame.draw.rect(context.screen, (0, 255, 255), (bx, by, max_w, total_h), 3)

        # 4. Draw Title & Fields
        title_surf = context.font.render(title, True, (255, 255, 0))
        context.screen.blit(title_surf, (bx + 20, by + 15))

        y = by + 60
        for i, (label, val, key) in enumerate(options):
            color = (255, 255, 255)
            if i == selected:
                pygame.draw.rect(context.screen, (255, 255, 255), (bx + 10, y - 5, max_w - 20, context.tile_size + 10))
                color = (0, 0, 0)
            
            if key == "spacer": 
                pass
            elif key == "apply": 
                surf = context.font.render("[ SAVE CHANGES ]", True, color)
                context.screen.blit(surf, (bx + (max_w - surf.get_width())//2, y))
            elif key == "cancel":
                surf = context.font.render("[ CANCEL ]", True, color)
                context.screen.blit(surf, (bx + (max_w - surf.get_width())//2, y))
            else:
                surf = context.font.render(f"{label}: {val}", True, color)
                context.screen.blit(surf, (bx + 20, y))
            y += context.tile_size + 10

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT: sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected = (selected - 1) % len(options)
                    if options[selected][2] == "spacer": selected = (selected - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(options)
                    if options[selected][2] == "spacer": selected = (selected + 1) % len(options)
                elif event.key == pygame.K_ESCAPE: return None
                elif event.key == pygame.K_RETURN:
                    key = options[selected][2]
                    if key == "apply": return {f[2]: f[1] for f in fields}
                    elif key == "cancel": return None
                    else:
                        if options[selected][2] == "color":
                            # Passing the current menu's render function instead of a complex recursive lambda
                            v = menu_pick_color(context, redraw_bg=lambda: _render_menu_generic(context, title, [f"{o[0]}: {o[1]}" if o[2] not in ["spacer", "apply", "cancel"] else ("[ SAVE CHANGES ]" if o[2]=="apply" else "[ CANCEL ]") for o in options], selected))
                        else:
                            v = get_user_input(context, 0, 0, f"Edit {options[selected][0]}: ")
                        
                        if v is not None: options[selected][1] = v

    pygame.display.flip()

class ControlSettingsMachine(StateMachine):
    browsing = SMState(initial=True)
    capturing = SMState()
    
    start_capture = browsing.to(capturing)
    finish_capture = capturing.to(browsing)
    cancel_capture = capturing.to(browsing)

class ControlSettingsState(State):
    def __init__(self, manager, context, bindings):
        super().__init__(manager)
        self.context = context
        self.bindings = bindings
        self.machine = ControlSettingsMachine()
        self.actions = sorted(list(bindings.keys()))
        self.selected_idx = 0
        self.scroll_offset = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        if self.machine.current_state == ControlSettingsMachine.browsing:
            self._handle_browsing(event)
        elif self.machine.current_state == ControlSettingsMachine.capturing:
            self._handle_capturing(event)

    def _handle_browsing(self, event):
        key = event.key
        if key == pygame.K_UP:
            self.selected_idx = max(0, self.selected_idx - 1)
        elif key == pygame.K_DOWN:
            self.selected_idx = min(len(self.actions) - 1, self.selected_idx + 1)
        elif key == pygame.K_PAGEUP:
            self.selected_idx = max(0, self.selected_idx - 10)
        elif key == pygame.K_PAGEDOWN:
            self.selected_idx = min(len(self.actions) - 1, self.selected_idx + 10)
        elif key == pygame.K_RETURN:
            self.machine.start_capture()
        elif key == pygame.K_q or key == pygame.K_ESCAPE:
            self.manager.pop()

    def _handle_capturing(self, event):
        if event.key == pygame.K_ESCAPE:
            self.machine.cancel_capture()
        else:
            action = self.actions[self.selected_idx]
            # Handle case sensitivity for single chars if needed, or just pygame.key.name
            key_name = pygame.key.name(event.key).lower()
            if event.mod & pygame.KMOD_SHIFT and len(key_name) == 1:
                key_name = key_name.upper()
                
            self.bindings[action] = key_name
            save_config(self.bindings)
            self.machine.finish_capture()

    def draw(self, surface):
        self.context.screen.fill((0, 0, 0))
        font = self.context.font
        tile_size = self.context.tile_size
        visible_actions = (self.context.height - 150) // tile_size
        
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + visible_actions:
            self.scroll_offset = self.selected_idx - visible_actions + 1

        surface.blit(font.render("=== EDIT CONTROLS ===", True, (255, 255, 255)), (10, 10))
        surface.blit(font.render("Action                          Key", True, (255, 255, 255)), (10, 2 * tile_size + 10))
        surface.blit(font.render("-" * 50, True, (255, 255, 255)), (10, 3 * tile_size + 10))

        y = 4 * tile_size + 10
        for i in range(visible_actions):
            idx = self.scroll_offset + i
            if idx >= len(self.actions): break
            action = self.actions[idx]
            key_name = self.bindings[action]
            line = f"{action:<30} {key_name}"

            color = (255, 255, 255)
            if idx == self.selected_idx:
                pygame.draw.rect(surface, (60, 60, 60), (0, y, self.context.width, tile_size))
                color = (255, 255, 0)

            surface.blit(font.render(line, True, color), (10, y))
            y += tile_size

        help_y = self.context.height - 80
        if self.machine.current_state == ControlSettingsMachine.browsing:
            surface.blit(font.render("Up/Down: Select | Enter: Change | Q: Back", True, (0, 255, 0)), (10, help_y))
        else:
            action = self.actions[self.selected_idx]
            surface.blit(font.render(f"Press new key for '{action}' (Esc to cancel)...", True, (255, 255, 0)), (10, help_y))

def menu_controls(context, bindings):
    # Deprecated
    pass

class TilePickerState(State):
    def __init__(self, manager, context, callback):
        super().__init__(manager)
        self.context = context
        self.callback = callback
        self.all_tiles = REGISTRY.get_all()
        self.selected_idx = 0
        self.cols = (context.width - 40) // (context.tile_size + 10) or 1

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        if event.key == pygame.K_UP: self.selected_idx = (self.selected_idx - self.cols) % len(self.all_tiles)
        elif event.key == pygame.K_DOWN: self.selected_idx = (self.selected_idx + self.cols) % len(self.all_tiles)
        elif event.key == pygame.K_LEFT: self.selected_idx = (self.selected_idx - 1) % len(self.all_tiles)
        elif event.key == pygame.K_RIGHT: self.selected_idx = (self.selected_idx + 1) % len(self.all_tiles)
        elif event.key == pygame.K_RETURN:
            self.callback(self.all_tiles[self.selected_idx].id)
            self.manager.pop()
        elif event.key == pygame.K_ESCAPE:
            self.manager.pop()

    def draw(self, surface):
        s = pygame.Surface((self.context.width, self.context.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 200))
        surface.blit(s, (0, 0))
        
        surface.blit(self.context.font.render("SELECT TILE", True, (255, 255, 255)), (20, 20))
        
        for i, tile in enumerate(self.all_tiles):
            row = i // self.cols
            col = i % self.cols
            px = 20 + col * (self.context.tile_size + 10)
            py = 60 + row * (self.context.tile_size + 10)
            
            if i == self.selected_idx:
                pygame.draw.rect(surface, (255, 255, 0), (px-2, py-2, self.context.tile_size+4, self.context.tile_size+4), 2)
            
            glyph = self.context.get_glyph(tile.char, tile.color)
            surface.blit(glyph, (px, py))

def menu_pick_tile(context):
    # Deprecated
    pass

def menu_statistics(context, map_obj):
    stats = get_map_statistics(map_obj)
    total = sum(stats.values())

    lines = ["=== MAP STATISTICS ===", "", f"Total tiles: {total}", ""]
    for tid, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        pct = (count / total * 100) if total > 0 else 0
        tile = REGISTRY.get(tid)
        name = tile.char if tile else str(tid)
        lines.append(f"'{name}': {count} ({pct:.1f}%)")
    lines.append("")
    lines.append("Press any key to continue...")

    _render_menu_generic(context, "Statistics", lines)

    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN or event.type == pygame.QUIT:
                waiting = False
        context.clock.tick(10)
    time.sleep(0.1)

def menu_save_map(context, map_obj, filename=None):
    if not filename:
        context.screen.fill((0,0,0))
        pygame.display.flip()
        filename = get_user_input(context, 10, 2, "Save map as: ")
        if not filename: return False

    from map_io import autosave_map as io_save
    return io_save(map_obj, filename)

class TextInputState(State):
    def __init__(self, manager, context, prompt, callback, initial_text=""):
        super().__init__(manager)
        self.context = context
        self.prompt = prompt
        self.callback = callback
        self.input_text = initial_text
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.callback(self.input_text)
                self.manager.pop()
            elif event.key == pygame.K_ESCAPE:
                self.manager.pop()
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                if event.unicode and event.unicode.isprintable():
                    self.input_text += event.unicode

    def draw(self, surface):
        # Calculate box dimensions
        box_w = 500
        box_h = 100
        bx = (self.context.width - box_w) // 2
        by = (self.context.height - box_h) // 2

        # Draw overlay box (StateManager handles drawing previous states under this one)
        s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        s.fill((30, 30, 30, 240))
        surface.blit(s, (bx, by))
        pygame.draw.rect(surface, (0, 255, 255), (bx, by, box_w, box_h), 2)

        # Render text
        prompt_surf = self.context.font.render(self.prompt, True, (0, 255, 255))
        surface.blit(prompt_surf, (bx + 20, by + 15))
        
        input_surf = self.context.font.render(self.input_text + "_", True, (255, 255, 255))
        surface.blit(input_surf, (bx + 20, by + 50))

class ConfirmationState(State):
    def __init__(self, manager, context, prompt, callback):
        super().__init__(manager)
        self.context = context
        self.prompt = prompt
        self.callback = callback

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_y:
                self.callback(True)
                self.manager.pop()
            elif event.key in [pygame.K_n, pygame.K_ESCAPE]:
                self.callback(False)
                self.manager.pop()

    def draw(self, surface):
        box_w = max(400, self.context.font.size(self.prompt)[0] + 60)
        box_h = 80
        bx = (self.context.width - box_w) // 2
        by = (self.context.height - box_h) // 2

        s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        s.fill((30, 30, 30, 240))
        surface.blit(s, (bx, by))
        pygame.draw.rect(surface, (255, 200, 0), (bx, by, box_w, box_h), 2)

        text_surf = self.context.font.render(self.prompt, True, (255, 255, 255))
        surface.blit(text_surf, (bx + (box_w - text_surf.get_width()) // 2, by + (box_h - text_surf.get_height()) // 2))

class NewMapMachine(StateMachine):
    filling_form = SMState(initial=True)
    finished = SMState()
    cancelled = SMState()
    
    submit = filling_form.to(finished)
    cancel = filling_form.to(cancelled)

class NewMapState(State):
    def __init__(self, manager, context, view_width, view_height, callback):
        super().__init__(manager)
        self.context = context
        self.view_width = view_width
        self.view_height = view_height
        self.callback = callback
        self.machine = NewMapMachine()
        self.fields = [
            ["Width", str(view_width), "width"],
            ["Height", str(view_height), "height"],
            ["Border", "#", "border"]
        ]
        self.selected = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        num_fields = len(self.fields)
        # 3 fields + 1 spacer + 1 Apply + 1 Cancel = 6 options
        options_count = num_fields + 3
        
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % options_count
            if self.selected == num_fields: # Skip spacer
                self.selected = (self.selected - 1) % options_count
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % options_count
            if self.selected == num_fields: # Skip spacer
                self.selected = (self.selected + 1) % options_count
        elif event.key == pygame.K_ESCAPE:
            self.manager.pop()
        elif event.key == pygame.K_RETURN:
            if self.selected < num_fields:
                field = self.fields[self.selected]
                def on_input(val):
                    field[1] = val
                self.manager.push(TextInputState(self.manager, self.context, f"Enter {field[0]}: ", on_input, field[1]))
            elif self.selected == num_fields + 1: # Apply
                self._apply()
            elif self.selected == num_fields + 2: # Cancel
                self.manager.pop()

    def _apply(self):
        from core import Map
        res = {f[2]: f[1] for f in self.fields}
        try:
            w = max(self.view_width, int(res["width"]))
            h = max(self.view_height, int(res["height"]))
            map_obj = Map(w, h)
            border_char = res["border"][0] if res["border"] and res["border"] != "." else None
            if border_char:
                tid = REGISTRY.get_by_char(border_char)
                if tid:
                    for x in range(w):
                        map_obj.set(x, 0, tid); map_obj.set(x, h-1, tid)
                    for y in range(h):
                        map_obj.set(0, y, tid); map_obj.set(w-1, y, tid)
            
            # Pop this menu state before calling the callback
            # This ensures start_editor pushes EditorState onto MainMenuState, not on top of this menu
            self.manager.pop()
            self.callback(map_obj)
        except Exception as e:
            print(f"Error creating map: {e}")

    def draw(self, surface):
        options = self.fields + [["", "", "spacer"], ["Create Map", "", "apply"], ["Cancel", "", "cancel"]]
        display_lines = []
        for f in options:
            if f[2] == "spacer":
                display_lines.append("")
            elif f[2] == "apply":
                display_lines.append("[ CREATE ]")
            elif f[2] == "cancel":
                display_lines.append("[ CANCEL ]")
            else:
                display_lines.append(f"{f[0]}: {f[1]}")
        
        _render_menu_generic(self.context, "NEW MAP SETTINGS", display_lines, self.selected)

class LoadMapState(State):
    def __init__(self, manager, context, view_width, view_height, callback):
        super().__init__(manager)
        self.context = context
        self.view_width = view_width
        self.view_height = view_height
        self.callback = callback

    def enter(self, **kwargs):
        from core import Map
        filename = get_user_input(self.context, 0, 0, "Load map from: ")
        if filename and os.path.exists(filename):
            try:
                with open(filename, "r") as f:
                    lines = [line.rstrip("\n") for line in f]
                if lines:
                    w = max(len(l) for l in lines); h = len(lines)
                    w = max(w, self.view_width); h = max(h, self.view_height)
                    m = Map(w, h)
                    for y, line in enumerate(lines):
                        for x, ch in enumerate(line):
                            m.set(x, y, REGISTRY.get_by_char(ch))
                    self.callback(m)
            except: pass
        self.manager.pop()

    def draw(self, surface):
        pass

class ExportMapState(State):
    def __init__(self, manager, context, map_obj):
        super().__init__(manager)
        self.context = context
        self.map_obj = map_obj

    def enter(self, **kwargs):
        filename = get_user_input(self.context, 0, 0, "Export as (.png/.csv): ")
        if filename:
            if not filename.endswith('.png') and not filename.endswith('.csv'):
                filename += '.png'

            if filename.endswith('.png'):
                ts_in = get_user_input(self.context, 0, 0, "Tile size (default 8): ")
                tile_size = int(ts_in) if ts_in else 8
                try:
                    export_to_image(self.map_obj.data, {}, filename, tile_size)
                except Exception as e: print(e)
            elif filename.endswith('.csv'):
                try:
                    with open(filename, 'w') as f:
                        for row in self.map_obj.data:
                            f.write(','.join(map(str, row)) + '\n')
                except Exception as e: print(e)
        self.manager.pop()

    def draw(self, surface):
        pass

def menu_export_image(context, map_obj):
    # This is a shim for actions.py which still calls it
    pass

def menu_load_map(context, view_width, view_height):
    pass

def menu_new_map(context, view_width, view_height):
    pass

class TileRegistryMachine(StateMachine):
    browsing = SMState(initial=True)
    adding = SMState()
    editing = SMState()

    start_add = browsing.to(adding)
    start_edit = browsing.to(editing)
    finish_action = (adding.to(browsing) | editing.to(browsing))
    cancel_action = (adding.to(browsing) | editing.to(browsing))

class TileRegistryState(State):
    def __init__(self, manager, context):
        super().__init__(manager)
        self.context = context
        self.machine = TileRegistryMachine()
        self.selected_idx = 0
        self.form_selected = 0
        self.fields = []
        self.all_tiles = []
        self.color_selected = 0
        self.color_options = []

    def enter(self, **kwargs):
        self.refresh_data()

    def refresh_data(self):
        self.all_tiles = REGISTRY.get_all()
        if not self.all_tiles: self.selected_idx = 0
        else: self.selected_idx = min(self.selected_idx, len(self.all_tiles)-1)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return

        if self.machine.current_state == TileRegistryMachine.browsing:
            self._handle_browsing(event)
        elif self.machine.current_state in [TileRegistryMachine.adding, TileRegistryMachine.editing]:
            self._handle_form(event)

    def _handle_browsing(self, event):
        if event.key == pygame.K_UP:
            self.selected_idx = (self.selected_idx - 1) % len(self.all_tiles) if self.all_tiles else 0
        elif event.key == pygame.K_DOWN:
            self.selected_idx = (self.selected_idx + 1) % len(self.all_tiles) if self.all_tiles else 0
        elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
            self.manager.pop()
        elif event.key == pygame.K_a:
            self.fields = [["Char", "", "char"], ["Name", "New Tile", "name"], ["Color", "white", "color"]]
            self.form_selected = 0
            self.machine.start_add()
        elif event.key == pygame.K_e and self.all_tiles:
            t = self.all_tiles[self.selected_idx]
            self.fields = [["Name", t.name, "name"], ["Color", get_color_name(t.color), "color"]]
            self.form_selected = 0
            self.machine.start_edit()
        elif (event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE) and self.all_tiles:
            target = self.all_tiles[self.selected_idx]
            if get_user_confirmation(self.context, 0, 0, f"Delete tile '{target.char}'?"):
                REGISTRY.delete(target.id)
                self.refresh_data()
                self.context.invalidate_cache()

    def _handle_form(self, event):
        num_fields = len(self.fields)
        # Total options: fields + 1 spacer + 1 Apply + 1 Cancel
        options_count = num_fields + 3 
        
        if event.key == pygame.K_UP:
            self.form_selected = (self.form_selected - 1) % options_count
            if self.form_selected == num_fields: # Skip spacer
                self.form_selected = (self.form_selected - 1) % options_count
        elif event.key == pygame.K_DOWN:
            self.form_selected = (self.form_selected + 1) % options_count
            if self.form_selected == num_fields: # Skip spacer
                self.form_selected = (self.form_selected + 1) % options_count
        elif event.key == pygame.K_ESCAPE:
            self.machine.cancel_action()
        elif event.key == pygame.K_RETURN:
            if self.form_selected < num_fields:
                field = self.fields[self.form_selected]
                if field[2] == "color":
                    def set_color(val):
                        field[1] = val
                    self.manager.push(ColorPickerState(self.manager, self.context, set_color))
                else:
                    val = get_user_input(self.context, 0, 0, f"Edit {field[0]}: ")
                    if val is not None: field[1] = val
            elif self.form_selected == num_fields + 1: # Apply
                self._apply_form()
            elif self.form_selected == num_fields + 2: # Cancel
                self.machine.cancel_action()

    def _apply_form(self):
        res = {f[2]: f[1] for f in self.fields}
        if self.machine.current_state == TileRegistryMachine.adding:
            if res.get("char") and len(res["char"]) == 1:
                REGISTRY.register(res["char"], res["name"], color=parse_color_name(res["color"]))
        else: # Editing
            target = self.all_tiles[self.selected_idx]
            REGISTRY.update_tile(target.id, name=res["name"], color=parse_color_name(res["color"]))
        
        self.refresh_data()
        self.context.invalidate_cache()
        self.machine.finish_action()

    def draw(self, surface):
        # Always draw the background list
        self.context.screen.fill((20, 20, 20))
        font = self.context.font
        tile_size = self.context.tile_size
        
        title = font.render("=== TILE REGISTRY ===", True, (0, 255, 255))
        self.context.screen.blit(title, (20, 20))
        
        y = 70
        for i, t in enumerate(self.all_tiles):
            color = (255, 255, 255)
            if i == self.selected_idx:
                pygame.draw.rect(self.context.screen, (60, 60, 60), (0, y - 2, self.context.width, tile_size + 10))
                color = (255, 255, 0)

            char_surf = font.render(f"[{t.char}]", True, color)
            name_surf = font.render(f"{t.name[:25]}", True, color)
            col_val = get_color_name(t.color)
            color_surf = font.render(f"Color: {col_val}", True, (150, 150, 150) if i != self.selected_idx else (200, 200, 200))
            
            self.context.screen.blit(char_surf, (30, y))
            self.context.screen.blit(name_surf, (100, y))
            self.context.screen.blit(color_surf, (400, y))
            y += tile_size + 15
            
        help_text = font.render("[A] Add New | [E] Edit | [Del] Delete | [Q] Back", True, (0, 255, 0))
        self.context.screen.blit(help_text, (20, self.context.height - 40))

        # Overlay dialogs if not browsing
        if self.machine.current_state in [TileRegistryMachine.adding, TileRegistryMachine.editing]:
            self._draw_form_overlay()

    def _draw_form_overlay(self):
        title = "CREATE NEW TILE" if self.machine.current_state == TileRegistryMachine.adding else "EDIT TILE"
        options = self.fields + [["", "", "spacer"], ["Apply", "", "apply"], ["Cancel", "", "cancel"]]
        
        max_w = 400
        total_h = (len(options)) * (self.context.tile_size + 10) + 60
        bx = (self.context.width - max_w) // 2
        by = (self.context.height - total_h) // 2

        s = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
        s.fill((50, 50, 70, 250))
        self.context.screen.blit(s, (bx, by))
        pygame.draw.rect(self.context.screen, (0, 255, 255), (bx, by, max_w, total_h), 3)

        title_surf = self.context.font.render(title, True, (255, 255, 0))
        self.context.screen.blit(title_surf, (bx + 20, by + 15))

        y = by + 60
        for i, (label, val, key) in enumerate(options):
            color = (255, 255, 255)
            if i == self.form_selected:
                pygame.draw.rect(self.context.screen, (255, 255, 255), (bx + 10, y - 5, max_w - 20, self.context.tile_size + 10))
                color = (0, 0, 0)
            
            if key == "apply": 
                surf = self.context.font.render("[ SAVE CHANGES ]", True, color)
                self.context.screen.blit(surf, (bx + (max_w - surf.get_width())//2, y))
            elif key == "cancel":
                surf = self.context.font.render("[ CANCEL ]", True, color)
                self.context.screen.blit(surf, (bx + (max_w - surf.get_width())//2, y))
            elif key != "spacer":
                surf = self.context.font.render(f"{label}: {val}", True, color)
                self.context.screen.blit(surf, (bx + 20, y))
            y += self.context.tile_size + 10

def menu_random_generation(context, map_obj, seed=None):
    fields = [
        ["Seed", str(seed) if seed is not None else "random", "seed"],
        ["Iterations (3-10)", "5", "iters"],
        ["Wall Char", "#", "wall"],
        ["Floor Char", ".", "floor"]
    ]
    
    res = _menu_form(context, "CAVE GENERATION SETTINGS", fields)
    if not res: return False

    try:
        gen_seed = int(res["seed"]) if res["seed"] != "random" else None
        iterations = max(3, min(10, int(res["iters"])))
        wall_id = REGISTRY.get_by_char(res["wall"][0])
        floor_id = REGISTRY.get_by_char(res["floor"][0])

        final_seed = cellular_automata_cave(map_obj, iterations, wall_id, floor_id, gen_seed)
        if gen_seed is None:
            get_user_confirmation(context, 6, 0, f"Generated with seed: {final_seed}. Press any key...", any_key=True)
        return True
    except Exception as e:
        print(e)
        return False

def menu_perlin_generation(context, map_obj, seed=None):
    fields = [
        ["Seed", str(seed) if seed is not None else "random", "seed"],
        ["Scale", "10.0", "scale"],
        ["Octaves", "4", "octaves"],
        ["Persistence", "0.5", "persistence"]
    ]
    
    res = _menu_form(context, "PERLIN NOISE SETTINGS", fields)
    if not res: return False

    try:
        gen_seed = int(res["seed"]) if res["seed"] != "random" else None
        scale = float(res["scale"])
        octaves = int(res["octaves"])
        persistence = float(res["persistence"])
        tile_ids = [t.id for t in REGISTRY.get_all()]

        final_seed = perlin_noise_generation(map_obj, tile_ids, scale, octaves, persistence, gen_seed)
        if gen_seed is None:
            get_user_confirmation(context, 6, 0, f"Generated with seed: {final_seed}. Press any key...", any_key=True)
        return True
    except Exception as e:
        print(e)
        return False

def menu_voronoi_generation(context, map_obj, seed=None):
    fields = [
        ["Seed", str(seed) if seed is not None else "random", "seed"],
        ["Points", "20", "points"]
    ]
    
    res = _menu_form(context, "VORONOI SETTINGS", fields)
    if not res: return False

    try:
        gen_seed = int(res["seed"]) if res["seed"] != "random" else None
        num_points = int(res["points"])
        tile_ids = [t.id for t in REGISTRY.get_all()]

        final_seed = voronoi_generation(map_obj, tile_ids, num_points, gen_seed)
        if gen_seed is None:
            get_user_confirmation(context, 4, 0, f"Generated with seed: {final_seed}. Press any key...", any_key=True)
        return True
    except Exception as e:
        print(e)
        return False

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
    prompt = f"New seed (current: {current_seed if current_seed is not None else 'random'}): "
    inp = get_user_input(context, 3, 0, prompt)
    if inp:
        if inp.lower() == 'random':
            return None
        try: return int(inp)
        except: pass
    elif inp == "": 
         return current_seed
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

class MacroManagerState(State):
    def __init__(self, manager, context, tool_state):
        super().__init__(manager)
        self.context = context
        self.tool_state = tool_state
        self.selected_idx = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        macros = list(self.tool_state.macros.keys())

        if event.key == pygame.K_UP:
            self.selected_idx = max(0, self.selected_idx - 1)
        elif event.key == pygame.K_DOWN:
            self.selected_idx = min(len(macros) - 1, self.selected_idx + 1)
        elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
            self.manager.pop()
        elif event.key == pygame.K_a:
            name = get_user_input(self.context, 0, 0, "Macro Name: ")
            if name:
                actions = get_user_input(self.context, 0, 0, "Actions (comma-separated chars): ")
                self.tool_state.macros[name] = actions.split(',') if actions else []
        elif event.key == pygame.K_r and macros:
            name = macros[self.selected_idx]
            if get_user_confirmation(self.context, 0, 0, f"Delete macro '{name}'?"):
                del self.tool_state.macros[name]
                self.selected_idx = max(0, self.selected_idx - 1)

    def draw(self, surface):
        macros = list(self.tool_state.macros.keys())
        lines = []
        for m in macros:
            count = len(self.tool_state.macros[m])
            lines.append(f"{m} ({count} steps)")
        
        _render_menu_generic(self.context, "MACRO MANAGER: [A] Add | [R] Remove", lines, self.selected_idx)

def menu_macros(context, tool_state):
    # Deprecated
    pass


class AutoTilingMachine(StateMachine):
    browsing_bases = SMState(initial=True)
    editing_rules = SMState()
    
    start_edit = browsing_bases.to(editing_rules)
    finish_edit = editing_rules.to(browsing_bases)

class AutoTilingManagerState(State):
    def __init__(self, manager, context, tool_state):
        super().__init__(manager)
        self.context = context
        self.tool_state = tool_state
        self.machine = AutoTilingMachine()
        self.base_idx = 0
        self.rule_idx = 0
        self.bases = []

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        self.bases = list(self.tool_state.tiling_rules.keys())

        if self.machine.current_state == AutoTilingMachine.browsing_bases:
            self._handle_browsing(event)
        else:
            self._handle_editing(event)

    def _handle_browsing(self, event):
        if event.key == pygame.K_UP:
            self.base_idx = max(0, self.base_idx - 1)
        elif event.key == pygame.K_DOWN:
            self.base_idx = min(len(self.bases) - 1, self.base_idx + 1)
        elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
            self.manager.pop()
        elif event.key == pygame.K_a:
            base = get_user_input(self.context, 0, 0, "Base Character: ")
            if base and len(base) == 1:
                if base not in self.tool_state.tiling_rules:
                    self.tool_state.tiling_rules[base] = {}
        elif event.key == pygame.K_r and self.bases:
            base = self.bases[self.base_idx]
            if get_user_confirmation(self.context, 0, 0, f"Delete rules for '{base}'?"):
                del self.tool_state.tiling_rules[base]
                self.base_idx = max(0, self.base_idx - 1)
        elif event.key == pygame.K_e and self.bases:
            self.rule_idx = 0
            self.machine.start_edit()

    def _handle_editing(self, event):
        if event.key == pygame.K_ESCAPE:
            self.machine.finish_edit()
        elif event.key == pygame.K_UP:
            self.rule_idx = max(0, self.rule_idx - 1)
        elif event.key == pygame.K_DOWN:
            self.rule_idx = min(14, self.rule_idx + 1)
        elif event.key == pygame.K_RETURN:
            base = self.bases[self.base_idx]
            mask = self.rule_idx + 1
            val = get_user_input(self.context, 0, 0, f"Variant char for mask {mask}: ")
            if val:
                self.tool_state.tiling_rules[base][mask] = val[0]

    def draw(self, surface):
        if self.machine.current_state == AutoTilingMachine.browsing_bases:
            self.bases = list(self.tool_state.tiling_rules.keys())
            lines = [f"Base '{b}': {len(self.tool_state.tiling_rules[b])} rules" for b in self.bases]
            _render_menu_generic(self.context, "AUTO-TILING: [A] Add | [E] Edit | [R] Remove", lines, self.base_idx)
        else:
            base = self.bases[self.base_idx]
            rlines = []
            for m in range(1, 16):
                binary = bin(m)[2:].zfill(4)
                curr = self.tool_state.tiling_rules[base].get(m, "")
                rlines.append(f"Mask {m:2} ({binary}): {curr}")
            _render_menu_generic(self.context, f"RULES FOR '{base}'", rlines, self.rule_idx)

def menu_define_autotiling(context, tool_state, _tile_chars):
    # Deprecated
    pass

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

def menu_define_pattern(context, _tile_chars, _tile_colors):
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

                glyph = context.get_glyph(pattern[r][c], (255,255,255))
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
