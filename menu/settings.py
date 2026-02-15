import pygame
import sys
from statemachine import StateMachine, State as SMState
from state_engine import State
from map_io import save_config
from menu.base import _render_menu_generic, TextInputState

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
        elif key in [pygame.K_q, pygame.K_ESCAPE]:
            self.manager.pop()

    def _handle_capturing(self, event):
        if event.key == pygame.K_ESCAPE:
            self.machine.cancel_capture()
            return

        # Ignore modifier keys
        if event.key in [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_LCTRL, pygame.K_RCTRL, 
                         pygame.K_LALT, pygame.K_RALT, pygame.K_LGUI, pygame.K_RGUI, pygame.K_CAPSLOCK]:
            return

        action = self.actions[self.selected_idx]
        key_name = pygame.key.name(event.key)
        
        # Use unicode for single-character keys to respect Shift/Caps Lock (e.g., 'A' instead of 'a', '!' instead of '1')
        # But preserve special key names like 'space', 'return', 'tab'
        if len(key_name) == 1 and event.unicode:
            key_name = event.unicode

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

class AutosaveSettingsState(State):
    def __init__(self, manager, context, tool_state):
        super().__init__(manager)
        self.context = context
        self.tool_state = tool_state
        self.selected = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        if event.key == pygame.K_UP: self.selected = max(0, self.selected - 1)
        elif event.key == pygame.K_DOWN: self.selected = min(4, self.selected + 1)
        elif event.key == pygame.K_ESCAPE: self.manager.pop()
        elif event.key == pygame.K_RETURN:
            if self.selected == 0: 
                self.tool_state.autosave_enabled = not self.tool_state.autosave_enabled
            elif self.selected == 1: 
                self.tool_state.autosave_mode = 'edits' if self.tool_state.autosave_mode == 'time' else 'time'
            elif self.selected == 2:
                if self.tool_state.autosave_mode == 'time':
                    def on_val(val):
                        if val: self.tool_state.autosave_interval = int(val)
                    self.manager.push(TextInputState(self.manager, self.context, "Interval (min): ", on_val))
                else:
                    def on_val(val):
                        if val: self.tool_state.autosave_edits_threshold = int(val)
                    self.manager.push(TextInputState(self.manager, self.context, "Threshold: ", on_val))
            elif self.selected == 3:
                def on_val(val):
                    if val: self.tool_state.autosave_filename = val
                self.manager.push(TextInputState(self.manager, self.context, "Filename: ", on_val))
            elif self.selected == 4: 
                self.manager.pop()

    def draw(self, surface):
        lines = ["=== AUTOSAVE SETTINGS ==="]
        lines.append(f"1. Enabled: {'Yes' if self.tool_state.autosave_enabled else 'No'}")
        lines.append(f"2. Mode: {self.tool_state.autosave_mode.capitalize()}")
        if self.tool_state.autosave_mode == 'time':
            lines.append(f"3. Interval: {self.tool_state.autosave_interval} min")
        else:
            lines.append(f"3. Threshold: {self.tool_state.autosave_edits_threshold} edits")
        lines.append(f"4. Filename: {self.tool_state.autosave_filename}")
        lines.append("5. Back")
        _render_menu_generic(self.context, "AUTOSAVE", lines, self.selected)

def menu_autosave_settings(context, tool_state):
    context.manager.push(AutosaveSettingsState(context.manager, context, tool_state))
