import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UISelectionList, UILabel, UIButton, UIScrollingContainer
from state_engine import State
from map_io import save_config
from menu.base import TextInputState, MenuState

class ControlSettingsState(State):
    def __init__(self, manager, context, bindings):
        super().__init__(manager)
        self.context = context
        self.bindings = bindings
        self.actions = sorted(list(bindings.keys()))
        self.window = None
        self.buttons = {} # ui_element -> action_name
        self.capturing = None # action being captured

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        win_w, win_h = 600, h - 100
        rect = pygame.Rect((w - win_w) // 2, (h - win_h) // 2, win_w, win_h)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="EDIT CONTROLS",
            resizable=True
        )

        container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, win_w - 30, win_h - 40),
            manager=self.ui_manager,
            container=self.window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

        y = 10
        for action in self.actions:
            key_val = self.bindings[action]
            if isinstance(key_val, list):
                key_name = ", ".join(key_val)
            else:
                key_name = str(key_val)

            UILabel(
                relative_rect=pygame.Rect(10, y, 250, 30),
                text=action,
                manager=self.ui_manager,
                container=container
            )

            btn = UIButton(
                relative_rect=pygame.Rect(270, y, 200, 30),
                text=key_name,
                manager=self.ui_manager,
                container=container
            )
            self.buttons[btn] = action
            y += 40

        container.set_scrollable_area_dimensions((win_w - 50, y + 10))

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if self.capturing:
            self._handle_capture(event)
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element in self.buttons:
                action = self.buttons[event.ui_element]
                self.capturing = action
                event.ui_element.set_text("Press Key...")
                event.ui_element.disable()
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def _handle_capture(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                # Cancel
                self._end_capture(self.bindings[self.capturing])
                return

            # Ignore modifier keys
            if event.key in [pygame.K_LSHIFT, pygame.K_RSHIFT, pygame.K_LCTRL, pygame.K_RCTRL, 
                            pygame.K_LALT, pygame.K_RALT, pygame.K_LGUI, pygame.K_RGUI, pygame.K_CAPSLOCK]:
                return

            key_name = pygame.key.name(event.key)
            if len(key_name) == 1 and event.unicode:
                key_name = event.unicode

            self.bindings[self.capturing] = key_name
            save_config(self.bindings)
            self._end_capture(key_name)

        elif event.type == pygame.MOUSEBUTTONDOWN:
            key_name = f"mouse {event.button}"
            self.bindings[self.capturing] = key_name
            save_config(self.bindings)
            self._end_capture(key_name)

    def _end_capture(self, new_text):
        if isinstance(new_text, list):
            display_text = ", ".join(new_text)
        else:
            display_text = str(new_text)
            
        # Find button
        for btn, action in self.buttons.items():
            if action == self.capturing:
                btn.set_text(display_text)
                btn.enable()
                break
        self.capturing = None

    def draw(self, surface):
        pass

class AutosaveSettingsState(MenuState):
    def __init__(self, manager, context, tool_state):
        self.tool_state = tool_state
        self.base_options = ["Enabled", "Mode", "Interval/Threshold", "Filename", "Back"]
        # MenuState expects static options list, but we want dynamic labels.
        # We can pass dummy list and override update?
        # Or just rebuild menu every time?
        # MenuState logic is simple.
        # Let's use a custom implementation inheriting from MenuState but overriding enter to build dynamic list?
        # No, simpler: Just use callbacks to update state and REBUILD the menu (pop/push).
        # Or better: AutosaveSettingsState should just be a UIWindow with specific controls (checkboxes, inputs).
        # But for now, let's stick to MenuState pattern but using dynamic labels is hard with standard MenuState.
        # I'll implement it as a custom UIWindow state.
        super().__init__(manager, context, "AUTOSAVE SETTINGS", []) # Dummy options

    def enter(self, **kwargs):
        # Override MenuState.enter to build custom UI
        w, h = self.manager.screen.get_size()
        rect = pygame.Rect((w - 400) // 2, (h - 400) // 2, 400, 400)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="AUTOSAVE SETTINGS"
        )

        self.labels = {}
        ts = self.tool_state
        
        y = 20
        # Enabled
        UILabel(pygame.Rect(20, y, 150, 30), "Enabled:", self.ui_manager, container=self.window)
        self.btn_enabled = UIButton(pygame.Rect(180, y, 100, 30), "Yes" if ts.autosave_enabled else "No", self.ui_manager, container=self.window)
        y += 40

        # Mode
        UILabel(pygame.Rect(20, y, 150, 30), "Mode:", self.ui_manager, container=self.window)
        self.btn_mode = UIButton(pygame.Rect(180, y, 100, 30), ts.autosave_mode.capitalize(), self.ui_manager, container=self.window)
        y += 40

        # Interval/Threshold
        label_text = "Interval (min):" if ts.autosave_mode == 'time' else "Threshold:"
        val_text = str(ts.autosave_interval) if ts.autosave_mode == 'time' else str(ts.autosave_edits_threshold)
        self.lbl_val = UILabel(pygame.Rect(20, y, 150, 30), label_text, self.ui_manager, container=self.window)
        self.btn_val = UIButton(pygame.Rect(180, y, 100, 30), val_text, self.ui_manager, container=self.window)
        y += 40

        # Filename
        UILabel(pygame.Rect(20, y, 150, 30), "Filename:", self.ui_manager, container=self.window)
        self.btn_filename = UIButton(pygame.Rect(180, y, 180, 30), ts.autosave_filename, self.ui_manager, container=self.window)
        y += 40

    def handle_event(self, event):
        ts = self.tool_state
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_enabled:
                ts.autosave_enabled = not ts.autosave_enabled
                self.btn_enabled.set_text("Yes" if ts.autosave_enabled else "No")
            elif event.ui_element == self.btn_mode:
                ts.autosave_mode = 'edits' if ts.autosave_mode == 'time' else 'time'
                self.btn_mode.set_text(ts.autosave_mode.capitalize())
                # Update val label/btn
                label_text = "Interval (min):" if ts.autosave_mode == 'time' else "Threshold:"
                val_text = str(ts.autosave_interval) if ts.autosave_mode == 'time' else str(ts.autosave_edits_threshold)
                self.lbl_val.set_text(label_text)
                self.btn_val.set_text(val_text)
            elif event.ui_element == self.btn_val:
                if ts.autosave_mode == 'time':
                    def on_v(v):
                        if v:
                            ts.autosave_interval = int(v)
                            self.btn_val.set_text(str(v))
                    self.manager.push(TextInputState(self.manager, self.context, "Interval (min):", on_v))
                else:
                    def on_v(v):
                        if v:
                            ts.autosave_edits_threshold = int(v)
                            self.btn_val.set_text(str(v))
                    self.manager.push(TextInputState(self.manager, self.context, "Threshold:", on_v))
            elif event.ui_element == self.btn_filename:
                def on_f(v):
                    if v:
                        ts.autosave_filename = v
                        self.btn_filename.set_text(v)
                self.manager.push(TextInputState(self.manager, self.context, "Filename:", on_f))

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

def menu_autosave_settings(manager, renderer, tool_state):
    manager.push(AutosaveSettingsState(manager, renderer, tool_state))
