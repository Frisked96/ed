from collections import Counter
import pygame
from state_engine import State
from utils import get_key_name

def build_key_map(bindings):
    key_map = {}
    for action, key_val in bindings.items():
        if not key_val or key_val == 'None':
            continue
        
        if isinstance(key_val, list):
            keys = key_val
        else:
            keys = [key_val]

        for key_name in keys:
            if not key_name or key_name == 'None': continue

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

    def draw(self, surface):
        lines = [opt[0] for opt in self.options]
        _render_menu_generic(self.context, self.title, lines, self.selected_idx)

class MenuState(State):
    def __init__(self, manager, context, title, options):
        """
        options: list of (label, callback) tuples
        """
        super().__init__(manager)
        self.context = context
        self.title = title
        self.options = options
        self.selected_idx = 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.selected_idx = (self.selected_idx - 1) % len(self.options)
            elif event.key == pygame.K_DOWN:
                self.selected_idx = (self.selected_idx + 1) % len(self.options)
            elif event.key == pygame.K_RETURN:
                callback = self.options[self.selected_idx][1]
                if callback: callback()
            elif event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def draw(self, surface):
        lines = [opt[0] for opt in self.options]
        _render_menu_generic(self.context, self.title, lines, self.selected_idx)

class TextInputState(State):
    def __init__(self, manager, context, prompt, callback, initial_text=""):
        super().__init__(manager)
        self.context = context
        self.prompt = prompt
        self.callback = callback
        self.input_text = str(initial_text)
        
    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.manager.pop()
                self.callback(self.input_text)
            elif event.key == pygame.K_ESCAPE:
                self.manager.pop()
                self.callback(None)
            elif event.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                if event.unicode and event.unicode.isprintable():
                    self.input_text += event.unicode

    def draw(self, surface):
        box_w = 500
        box_h = 100
        bx = (self.context.width - box_w) // 2
        by = (self.context.height - box_h) // 2

        s = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        s.fill((30, 30, 30, 240))
        surface.blit(s, (bx, by))
        pygame.draw.rect(surface, (0, 255, 255), (bx, by, box_w, box_h), 2)

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
        
        # Determine dimensions
        font = self.context.font
        prompt_w = font.size(self.prompt)[0]
        self.box_w = max(400, prompt_w + 60)
        self.box_h = 100
        self.bx = (self.context.width - self.box_w) // 2
        self.by = (self.context.height - self.box_h) // 2
        
        # Button rects (relative to box)
        self.yes_rect = pygame.Rect(self.bx + self.box_w//2 - 110, self.by + 50, 80, 30)
        self.no_rect = pygame.Rect(self.bx + self.box_w//2 + 30, self.by + 50, 80, 30)
        self.hover_btn = None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_y:
                self.manager.pop()
                self.callback(True)
            elif event.key in [pygame.K_n, pygame.K_ESCAPE, pygame.K_RETURN]:
                self.manager.pop()
                self.callback(False)
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            if self.yes_rect.collidepoint(mx, my):
                self.hover_btn = 'yes'
            elif self.no_rect.collidepoint(mx, my):
                self.hover_btn = 'no'
            else:
                self.hover_btn = None
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                mx, my = event.pos
                if self.yes_rect.collidepoint(mx, my):
                    self.manager.pop()
                    self.callback(True)
                elif self.no_rect.collidepoint(mx, my):
                    self.manager.pop()
                    self.callback(False)

    def draw(self, surface):
        s = pygame.Surface((self.box_w, self.box_h), pygame.SRCALPHA)
        s.fill((30, 30, 30, 240))
        surface.blit(s, (self.bx, self.by))
        pygame.draw.rect(surface, (255, 200, 0), (self.bx, self.by, self.box_w, self.box_h), 2)

        text_surf = self.context.font.render(self.prompt, True, (255, 255, 255))
        surface.blit(text_surf, (self.bx + (self.box_w - text_surf.get_width()) // 2, self.by + 15))

        # Draw Buttons
        yes_color = (100, 255, 100) if self.hover_btn == 'yes' else (60, 180, 60)
        no_color = (255, 100, 100) if self.hover_btn == 'no' else (180, 60, 60)
        
        pygame.draw.rect(surface, yes_color, self.yes_rect)
        pygame.draw.rect(surface, no_color, self.no_rect)
        
        yes_txt = self.context.font.render("YES", True, (0,0,0))
        no_txt = self.context.font.render("NO", True, (0,0,0))
        
        surface.blit(yes_txt, (self.yes_rect.centerx - yes_txt.get_width()//2, self.yes_rect.centery - yes_txt.get_height()//2))
        surface.blit(no_txt, (self.no_rect.centerx - no_txt.get_width()//2, self.no_rect.centery - no_txt.get_height()//2))

class MessageState(State):
    def __init__(self, manager, context, text, callback=None):
        super().__init__(manager)
        self.context = context
        self.text = text
        self.callback = callback

    def handle_event(self, event):
        if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
            self.manager.pop()
            if self.callback:
                self.callback()

    def draw(self, surface):
        text_surf = self.context.font.render(self.text, True, (255, 255, 255))
        rect = text_surf.get_rect(center=(self.context.width // 2, self.context.height // 2))
        bg_rect = rect.inflate(40, 40)

        pygame.draw.rect(surface, (0, 0, 0), bg_rect)
        pygame.draw.rect(surface, (255, 255, 255), bg_rect, 2)
        surface.blit(text_surf, rect)

class HelpState(State):
    def __init__(self, manager, context, bindings):
        super().__init__(manager)
        self.context = context
        self.bindings = bindings
        self.scroll = 0
        self.all_lines = self._generate_help()

    def _generate_help(self):
        try:
            b = self.bindings
            help_sections = [
                ("MOVEMENT", [
                    f"View: {get_key_name(b.get('move_view_up'))}/{get_key_name(b.get('move_view_down'))}/{get_key_name(b.get('move_view_left'))}/{get_key_name(b.get('move_view_right'))}",
                    f"Cursor: Arrow Keys"
                ]),
                ("DRAWING TOOLS", [
                    f"{get_key_name(b.get('place_tile'))}=Place tile | {get_key_name(b.get('cycle_tile'))}=Cycle tiles | {get_key_name(b.get('pick_tile'))}=Pick tile",
                    f"{get_key_name(b.get('flood_fill'))}=Flood fill | {get_key_name(b.get('line_tool'))}=Line | {get_key_name(b.get('rect_tool'))}=Rectangle",
                    f"{get_key_name(b.get('circle_tool'))}=Circle | {get_key_name(b.get('pattern_tool'))}=Pattern mode | {get_key_name(b.get('define_pattern'))}=Def Pattern",
                    f"Brush: {get_key_name(b.get('decrease_brush'))}/{get_key_name(b.get('increase_brush'))} (Size) | {get_key_name(b.get('define_brush'))}=Define shape",
                    f"{get_key_name(b.get('define_tiles'))}=Define Custom Tiles"
                ]),
                ("SELECTION & CLIPBOARD", [
                    f"{get_key_name(b.get('select_start'))}=Start/End selection | {get_key_name(b.get('clear_selection'))}=Clear",
                    f"{get_key_name(b.get('copy_selection'))}=Copy | {get_key_name(b.get('paste_selection'))}=Paste",
                    f"{get_key_name(b.get('rotate_selection'))}=Rotate Sel | {get_key_name(b.get('flip_h'))}=Flip H Sel | {get_key_name(b.get('flip_v'))}=Flip V Sel",
                    f"{get_key_name(b.get('clear_area'))}=Clear selected area"
                ]),
                ("EDIT OPERATIONS", [
                    f"{get_key_name(b.get('undo'))}=Undo | {get_key_name(b.get('redo'))}=Redo",
                    f"{get_key_name(b.get('replace_all'))}=Replace all tiles | {get_key_name(b.get('statistics'))}=Show statistics"
                ]),
                ("MAP TRANSFORMATIONS", [
                    f"{get_key_name(b.get('map_rotate'))}=Rotate map 90° | {get_key_name(b.get('map_flip_h'))}=Flip H | {get_key_name(b.get('map_flip_v'))}=Flip V"
                ]),
                ("PROCEDURAL GENERATION", [
                    f"{get_key_name(b.get('random_gen'))}=Cellular Cave | {get_key_name(b.get('perlin_noise'))}=Perlin Noise",
                    f"{get_key_name(b.get('voronoi'))}=Voronoi regions | {get_key_name(b.get('set_seed'))}=Set random seed"
                ]),
                ("FILE OPERATIONS", [
                    f"{get_key_name(b.get('new_map'))}=New map | {get_key_name(b.get('load_map'))}=Load | {get_key_name(b.get('save_map'))}=Save",
                    f"{get_key_name(b.get('resize_map'))}=Resize map | {get_key_name(b.get('export_image'))}=Export PNG/CSV"
                ]),
                ("MACROS & AUTOMATION", [
                    f"{get_key_name(b.get('macro_record_toggle'))}=Toggle Macro Record | {get_key_name(b.get('macro_play'))}=Play Macro",
                    f"{get_key_name(b.get('toggle_autotile'))}=Toggle Auto-Tiling"
                ]),
                ("SYSTEM", [
                    f"{get_key_name(b.get('toggle_snap'))}=Set Snap | {get_key_name(b.get('set_measure'))}=Measure Dist",
                    f"{get_key_name(b.get('editor_menu'))}=Pause Menu (F1) | {get_key_name(b.get('quit'))}=Quit Editor",
                    f"{get_key_name(b.get('show_help'))}=Toggle Help (?) | {get_key_name(b.get('toggle_palette'))}=Toggle Palette",
                    f"{get_key_name(b.get('edit_controls'))}=Edit Controls"
                ])
            ]
            all_lines = ["=== HELP (ESC to close) ==="]
            for section, lines in help_sections:
                all_lines.append(f"--- {section} ---")
                all_lines.extend(lines)
                all_lines.append("")
            return all_lines
        except Exception as e:
            print(f"ERROR in _generate_help: {e}")
            return ["Error generating help", str(e), "Check console for details"]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in [pygame.K_ESCAPE, pygame.K_q]:
                self.manager.pop()
            elif event.key == pygame.K_UP:
                self.scroll = max(0, self.scroll - 1)
            elif event.key == pygame.K_DOWN:
                self.scroll = min(len(self.all_lines) - 5, self.scroll + 1)

    def draw(self, surface):
        overlay_w, overlay_h = self.context.width - 100, self.context.height - 100
        ox, oy = 50, 50
        
        # Proper transparency
        temp_surface = pygame.Surface((overlay_w, overlay_h), pygame.SRCALPHA)
        temp_surface.fill((20, 20, 30, 230))
        surface.blit(temp_surface, (ox, oy))
        
        pygame.draw.rect(surface, (0, 255, 255), (ox, oy, overlay_w, overlay_h), 2)

        line_h = 24
        max_lines = (overlay_h - 40) // line_h
        for i in range(max_lines):
            idx = self.scroll + i
            if idx < len(self.all_lines):
                line_text = self.all_lines[idx]
                color = (255, 255, 255)
                if line_text.startswith("---"): color = (255, 255, 0)
                if line_text.startswith("==="): color = (0, 255, 255)
                
                surf = self.context.font.render(line_text, True, color)
                surface.blit(surf, (ox + 20, oy + 20 + i * line_h))

class FormState(State):
    def __init__(self, manager, context, title, fields, callback):
        super().__init__(manager)
        self.context = context
        self.title = title
        self.fields = fields # [[label, value, key], ...]
        self.callback = callback
        self.selected = 0
        self.options = fields + [["", "", "spacer"], ["Apply", "", "apply"], ["Cancel", "", "cancel"]]
        self.is_editing = False
        self.editing_text = ""

    def handle_event(self, event):
        if self.is_editing:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.options[self.selected][1] = self.editing_text
                    self.is_editing = False
                    pygame.key.stop_text_input()
                    return
                elif event.key == pygame.K_ESCAPE:
                    self.is_editing = False
                    pygame.key.stop_text_input()
                    self.manager.pop()
                    self.callback(None)
                    return
                elif event.key == pygame.K_BACKSPACE:
                    self.editing_text = self.editing_text[:-1]
                    return
            elif event.type == pygame.TEXTINPUT:
                self.editing_text += event.text
                return
            return

        if event.type != pygame.KEYDOWN: return
        
        num_fields = len(self.fields)
        options_count = len(self.options)
        
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % options_count
            if self.options[self.selected][2] == "spacer":
                self.selected = (self.selected - 1) % options_count
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % options_count
            if self.options[self.selected][2] == "spacer":
                self.selected = (self.selected + 1) % options_count
        elif event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
            self.manager.pop()
            self.callback(None)
        elif event.key == pygame.K_RETURN:
            key = self.options[self.selected][2]
            if key == "apply":
                self.manager.pop()
                self.callback({f[2]: f[1] for f in self.fields})
            elif key == "cancel":
                self.manager.pop()
                self.callback(None)
            elif key == "spacer":
                pass
            elif key == "color":
                from menu.pickers import ColorPickerState
                def set_color(val):
                    if val: self.options[self.selected][1] = val
                self.manager.push(ColorPickerState(self.manager, self.context, set_color))
            else:
                self.is_editing = True
                self.editing_text = str(self.options[self.selected][1])
                pygame.key.start_text_input()

    def draw(self, surface):
        # Dynamic width calculation
        text_lines = []
        for i, (label, val, key) in enumerate(self.options):
            if key in ["apply", "cancel", "spacer"]: continue
            display_val = self.editing_text if (self.is_editing and i == self.selected) else val
            text_lines.append(f"{label}: {display_val}")
        
        max_w = max([self.context.font.size(line)[0] for line in text_lines] + 
                    [self.context.font.size(self.title)[0], 200]) + 80
        
        total_h = (len(self.options)) * (self.context.tile_size + 10) + 60
        bx = (self.context.width - max_w) // 2
        by = (self.context.height - total_h) // 2

        s = pygame.Surface((max_w, total_h), pygame.SRCALPHA)
        s.fill((50, 50, 70, 250))
        surface.blit(s, (bx, by))
        pygame.draw.rect(surface, (0, 255, 255), (bx, by, max_w, total_h), 3)

        title_surf = self.context.font.render(self.title, True, (255, 255, 0))
        surface.blit(title_surf, (bx + 20, by + 15))

        y = by + 60
        for i, (label, val, key) in enumerate(self.options):
            color = (255, 255, 255)
            if i == self.selected:
                bg_color = (100, 100, 150) if self.is_editing else (255, 255, 255)
                pygame.draw.rect(surface, bg_color, (bx + 10, y - 5, max_w - 20, self.context.tile_size + 10))
                color = (255, 255, 255) if self.is_editing else (0, 0, 0)
            
            if key == "apply": 
                surf = self.context.font.render("[ SAVE CHANGES ]", True, color)
                surface.blit(surf, (bx + (max_w - surf.get_width())//2, y))
            elif key == "cancel":
                surf = self.context.font.render("[ CANCEL ]", True, color)
                surface.blit(surf, (bx + (max_w - surf.get_width())//2, y))
            elif key != "spacer":
                display_val = val
                if i == self.selected and self.is_editing:
                    display_val = self.editing_text + "_"
                surf = self.context.font.render(f"{label}: {display_val}", True, color)
                surface.blit(surf, (bx + 20, y))
            y += self.context.tile_size + 10

class ContextMenuState(State):
    def __init__(self, manager, context, options, screen_pos):
        super().__init__(manager)
        self.context = context
        self.options = options
        self.screen_pos = screen_pos
        self.selected_idx = -1
        
        font = context.font
        
        # Layout calculation
        self.item_height = 30
        self.max_rows = 12 # Max items per column before splitting
        
        count = len(options)
        if count > self.max_rows:
            self.cols = 2
            self.rows = (count + 1) // 2
        else:
            self.cols = 1
            self.rows = count

        # Calculate width per column
        self.col_widths = []
        for c in range(self.cols):
            # Items for this column
            start = c * self.rows
            end = min(start + self.rows, count)
            col_items = options[start:end]
            
            w = 0
            for label, _ in col_items:
                tw = font.size(label)[0]
                if tw > w: w = tw
            self.col_widths.append(w + 40) # Padding
            
        self.width = sum(self.col_widths)
        self.height = self.rows * self.item_height + 10

        x, y = screen_pos
        # Adjust position if off-screen
        if x + self.width > context.width: x = max(0, context.width - self.width)
        if y + self.height > context.height: y = max(0, context.height - self.height)
        self.rect = pygame.Rect(x, y, self.width, self.height)

    def get_index_at(self, pos):
        mx, my = pos
        if not self.rect.collidepoint(mx, my): return -1
        
        rel_x = mx - self.rect.x
        rel_y = my - self.rect.y - 5
        
        if rel_y < 0 or rel_y >= self.rows * self.item_height: return -1
        
        row = rel_y // self.item_height
        
        current_x = 0
        col = -1
        for i, w in enumerate(self.col_widths):
            if rel_x >= current_x and rel_x < current_x + w:
                col = i
                break
            current_x += w
            
        if col == -1: return -1
        
        idx = col * self.rows + row
        if idx < len(self.options):
            return idx
        return -1

    def handle_event(self, event):
        if event.type == pygame.MOUSEMOTION:
            self.selected_idx = self.get_index_at(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            idx = self.get_index_at(event.pos)
            if idx != -1:
                cb = self.options[idx][1]
                self.manager.pop()
                if cb: cb()
            else:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: self.manager.pop()

    def draw(self, surface):
        shadow = self.rect.copy()
        shadow.move_ip(4, 4)
        s = pygame.Surface((shadow.width, shadow.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 100))
        surface.blit(s, shadow)

        pygame.draw.rect(surface, (40, 40, 40), self.rect)
        pygame.draw.rect(surface, (150, 150, 150), self.rect, 1)
        
        # Draw Separator if 2 cols
        current_x = self.rect.x
        for i in range(self.cols - 1):
             current_x += self.col_widths[i]
             pygame.draw.line(surface, (100, 100, 100), (current_x, self.rect.y + 5), (current_x, self.rect.y + self.height - 5))

        font = self.context.font
        current_x = self.rect.x
        
        for c in range(self.cols):
            start = c * self.rows
            end = min(start + self.rows, len(self.options))
            
            for r in range(end - start):
                idx = start + r
                label, _ = self.options[idx]
                
                # Item Rect
                item_rect = pygame.Rect(current_x, self.rect.y + 5 + r * self.item_height, self.col_widths[c], self.item_height)
                
                color = (200, 200, 200)
                if idx == self.selected_idx:
                    pygame.draw.rect(surface, (60, 60, 80), item_rect)
                    color = (255, 255, 255)
                
                surf = font.render(label, True, color)
                surface.blit(surf, (item_rect.x + 20, item_rect.y + (self.item_height - surf.get_height()) // 2))
            
            current_x += self.col_widths[c]
