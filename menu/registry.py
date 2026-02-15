import pygame
from statemachine import StateMachine, State as SMState
from state_engine import State
from tiles import REGISTRY
from utils import parse_color_name, get_color_name
from menu.pickers import ColorPickerState
from menu.base import TextInputState, ConfirmationState

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
        self.scroll_offset = 0
        self.form_selected = 0
        self.fields = []
        self.all_tiles = []
        self.is_editing = False
        self.editing_text = ""

    def enter(self, **kwargs):
        self.refresh_data()

    def refresh_data(self):
        self.all_tiles = REGISTRY.get_all()
        if not self.all_tiles: self.selected_idx = 0
        else: self.selected_idx = min(self.selected_idx, len(self.all_tiles)-1)
        self._ensure_selection_visible()

    def _ensure_selection_visible(self):
        if not self.all_tiles: return
        row_height = self.context.tile_size + 15
        available_height = self.context.height - 120
        rows_per_page = available_height // row_height
        
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + rows_per_page:
            self.scroll_offset = self.selected_idx - rows_per_page + 1

    def handle_event(self, event):
        if self.machine.current_state == TileRegistryMachine.browsing:
            if event.type != pygame.KEYDOWN: return
            self._handle_browsing(event)
        elif self.machine.current_state in [TileRegistryMachine.adding, TileRegistryMachine.editing]:
            self._handle_form(event)

    def _handle_browsing(self, event):
        if event.key == pygame.K_UP:
            self.selected_idx = (self.selected_idx - 1) % len(self.all_tiles) if self.all_tiles else 0
            self._ensure_selection_visible()
        elif event.key == pygame.K_DOWN:
            self.selected_idx = (self.selected_idx + 1) % len(self.all_tiles) if self.all_tiles else 0
            self._ensure_selection_visible()
        elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
            self.manager.pop()
        elif event.key == pygame.K_a:
            self.fields = [["Char", "", "char"], ["Name", "New Tile", "name"], ["Color", "white", "color"]]
            self.form_selected = 0
            self.is_editing = False
            self.machine.start_add()
        elif event.key == pygame.K_e and self.all_tiles:
            t = self.all_tiles[self.selected_idx]
            self.fields = [["Name", t.name, "name"], ["Color", get_color_name(t.color), "color"]]
            self.form_selected = 0
            self.is_editing = False
            self.machine.start_edit()
        elif (event.key == pygame.K_DELETE or event.key == pygame.K_BACKSPACE) and self.all_tiles:
            target = self.all_tiles[self.selected_idx]
            def on_confirm(confirmed):
                if confirmed:
                    REGISTRY.delete(target.id)
                    self.refresh_data()
                    self.context.invalidate_cache()
            self.manager.push(ConfirmationState(self.manager, self.context, f"Delete tile '{target.char}'?", on_confirm))

    def _handle_form(self, event):
        num_fields = len(self.fields)
        options_count = num_fields + 3 
        
        if self.is_editing:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    self.fields[self.form_selected][1] = self.editing_text
                    self.is_editing = False
                    pygame.key.stop_text_input()
                    return
                elif event.key == pygame.K_ESCAPE:
                    self.is_editing = False
                    pygame.key.stop_text_input()
                    return
                elif event.key == pygame.K_BACKSPACE:
                    self.editing_text = self.editing_text[:-1]
                    return
            elif event.type == pygame.TEXTINPUT:
                self.editing_text += event.text
                return
            return

        if event.type != pygame.KEYDOWN: return

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
                        if val: field[1] = val
                    self.manager.push(ColorPickerState(self.manager, self.context, set_color))
                else:
                    self.is_editing = True
                    self.editing_text = str(field[1])
                    pygame.key.start_text_input()
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
        self.context.screen.fill((20, 20, 20))
        font = self.context.font
        tile_size = self.context.tile_size
        
        title = font.render("=== TILE REGISTRY ===", True, (0, 255, 255))
        self.context.screen.blit(title, (20, 20))
        
        row_height = tile_size + 15
        available_height = self.context.height - 120
        rows_per_page = available_height // row_height
        
        y = 70
        visible_tiles = self.all_tiles[self.scroll_offset : self.scroll_offset + rows_per_page]
        for idx_rel, t in enumerate(visible_tiles):
            i = self.scroll_offset + idx_rel
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
            y += row_height
            
        help_text = font.render("[A] Add New | [E] Edit | [Del] Delete | [Q] Back", True, (0, 255, 0))
        self.context.screen.blit(help_text, (20, self.context.height - 40))

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
                bg_color = (100, 100, 150) if self.is_editing else (255, 255, 255)
                pygame.draw.rect(self.context.screen, bg_color, (bx + 10, y - 5, max_w - 20, self.context.tile_size + 10))
                color = (255, 255, 255) if self.is_editing else (0, 0, 0)
            
            if key == "apply": 
                surf = self.context.font.render("[ SAVE CHANGES ]", True, color)
                self.context.screen.blit(surf, (bx + (max_w - surf.get_width())//2, y))
            elif key == "cancel":
                surf = self.context.font.render("[ CANCEL ]", True, color)
                self.context.screen.blit(surf, (bx + (max_w - surf.get_width())//2, y))
            elif key != "spacer":
                display_val = val
                if i == self.form_selected and self.is_editing:
                    display_val = self.editing_text + "_"
                surf = self.context.font.render(f"{label}: {display_val}", True, color)
                self.context.screen.blit(surf, (bx + 20, y))
            y += self.context.tile_size + 10

