import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UISelectionList, UILabel, UIButton, UIScrollingContainer
from state_engine import State
from menu.base import TextInputState, ConfirmationState

class MacroManagerState(State):
    def __init__(self, manager, context, tool_state):
        super().__init__(manager)
        self.context = context
        self.tool_state = tool_state
        self.window = None
        self.selection_list = None
        self.macros = [] # List of macro names

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        rect = pygame.Rect((w - 500) // 2, (h - 600) // 2, 500, 600)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="MACRO MANAGER"
        )

        # Toolbar
        self.btn_add = UIButton(pygame.Rect(20, 20, 100, 30), "Add New", self.ui_manager, container=self.window)
        self.btn_del = UIButton(pygame.Rect(130, 20, 100, 30), "Delete", self.ui_manager, container=self.window)
        self.btn_back = UIButton(pygame.Rect(rect.width - 120, 20, 100, 30), "Back", self.ui_manager, container=self.window)

        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(20, 60, rect.width - 40, rect.height - 100),
            item_list=[],
            manager=self.ui_manager,
            container=self.window
        )
        self.refresh_list()

    def refresh_list(self):
        self.macros = sorted(list(self.tool_state.macros.keys()))
        items = [f"{m} ({len(self.tool_state.macros[m])} steps)" for m in self.macros]
        self.selection_list.set_item_list(items)

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_add:
                def on_name(name):
                    if name:
                        def on_actions(actions):
                            self.tool_state.macros[name] = actions.split(',') if actions else []
                            self.refresh_list()
                        self.manager.push(TextInputState(self.manager, self.context, "Actions (comma-separated chars): ", on_actions))
                self.manager.push(TextInputState(self.manager, self.context, "Macro Name: ", on_name))
            elif event.ui_element == self.btn_del:
                sel = self.selection_list.get_single_selection()
                if sel:
                    # Parse name from string "name (N steps)"
                    name = sel.split(" (")[0]
                    def on_confirm(confirmed):
                        if confirmed:
                            if name in self.tool_state.macros:
                                del self.tool_state.macros[name]
                                self.refresh_list()
                    self.manager.push(ConfirmationState(self.manager, self.context, f"Delete macro '{name}'?", on_confirm))
            elif event.ui_element == self.btn_back:
                self.manager.pop()
        
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def draw(self, surface):
        pass

class AutoTilingManagerState(State):
    def __init__(self, manager, context, tool_state):
        super().__init__(manager)
        self.context = context
        self.tool_state = tool_state
        self.window = None
        self.selection_list = None
        self.bases = []
        self.editing_base = None

    def enter(self, **kwargs):
        self._build_main_ui()
        self.refresh_list()

    def exit(self):
        if self.window:
            self.window.kill()

    def _build_main_ui(self):
        w, h = self.manager.screen.get_size()
        rect = pygame.Rect((w - 500) // 2, (h - 600) // 2, 500, 600)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="AUTO-TILING MANAGER"
        )

        self.btn_add = UIButton(pygame.Rect(20, 20, 100, 30), "Add Base", self.ui_manager, container=self.window)
        self.btn_edit = UIButton(pygame.Rect(130, 20, 100, 30), "Edit Rules", self.ui_manager, container=self.window)
        self.btn_del = UIButton(pygame.Rect(240, 20, 100, 30), "Delete", self.ui_manager, container=self.window)
        self.btn_back = UIButton(pygame.Rect(rect.width - 120, 20, 100, 30), "Back", self.ui_manager, container=self.window)

        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(20, 60, rect.width - 40, rect.height - 100),
            item_list=[],
            manager=self.ui_manager,
            container=self.window
        )

    def refresh_list(self):
        self.bases = sorted(list(self.tool_state.tiling_rules.keys()))
        items = [f"Base '{b}': {len(self.tool_state.tiling_rules[b])} rules" for b in self.bases]
        self.selection_list.set_item_list(items)

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.btn_add:
                def on_base(base):
                    if base and len(base) == 1:
                        if base not in self.tool_state.tiling_rules:
                            self.tool_state.tiling_rules[base] = {}
                            self.refresh_list()
                self.manager.push(TextInputState(self.manager, self.context, "Base Character: ", on_base))
            elif event.ui_element == self.btn_edit:
                sel = self.selection_list.get_single_selection()
                if sel:
                    base = sel.split("'")[1]
                    self._open_rules_editor(base)
            elif event.ui_element == self.btn_del:
                sel = self.selection_list.get_single_selection()
                if sel:
                    base = sel.split("'")[1]
                    def on_confirm(confirmed):
                        if confirmed:
                            if base in self.tool_state.tiling_rules:
                                del self.tool_state.tiling_rules[base]
                                self.refresh_list()
                    self.manager.push(ConfirmationState(self.manager, self.context, f"Delete rules for '{base}'?", on_confirm))
            elif event.ui_element == self.btn_back:
                self.manager.pop()

        elif event.type == pygame_gui.UI_SELECTION_LIST_DOUBLE_CLICKED_SELECTION:
            if event.ui_element == self.selection_list:
                sel = self.selection_list.get_single_selection()
                if sel:
                    base = sel.split("'")[1]
                    self._open_rules_editor(base)

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def _open_rules_editor(self, base):
        self.manager.push(AutoTilingRulesState(self.manager, self.context, self.tool_state, base))

    def draw(self, surface):
        pass

class AutoTilingRulesState(State):
    def __init__(self, manager, context, tool_state, base):
        super().__init__(manager)
        self.context = context
        self.tool_state = tool_state
        self.base = base
        self.window = None
        self.buttons = {} # btn -> mask

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        win_w, win_h = 600, h - 100
        rect = pygame.Rect((w - win_w) // 2, (h - win_h) // 2, win_w, win_h)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title=f"RULES FOR '{self.base}'",
            resizable=True
        )

        container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, win_w - 30, win_h - 40),
            manager=self.ui_manager,
            container=self.window
        )

        y = 10
        rules = self.tool_state.tiling_rules[self.base]

        for m in range(1, 16):
            binary = bin(m)[2:].zfill(4)
            curr = rules.get(m, "")

            UILabel(
                relative_rect=pygame.Rect(10, y, 200, 30),
                text=f"Mask {m:2} ({binary}):",
                manager=self.ui_manager,
                container=container
            )

            btn = UIButton(
                relative_rect=pygame.Rect(220, y, 100, 30),
                text=curr if curr else "Set...",
                manager=self.ui_manager,
                container=container
            )
            self.buttons[btn] = m
            y += 40

        container.set_scrollable_area_dimensions((win_w - 50, y + 10))

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element in self.buttons:
                mask = self.buttons[event.ui_element]
                btn = event.ui_element
                def on_val(val):
                    if val:
                        self.tool_state.tiling_rules[self.base][mask] = val[0]
                        btn.set_text(val[0])
                self.manager.push(TextInputState(self.manager, self.context, f"Variant char for mask {mask}: ", on_val))

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def draw(self, surface):
        pass
