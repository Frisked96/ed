import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UITextBox
from state_engine import State
from menu.base import MenuState, get_map_statistics
from tiles import REGISTRY

class StatisticsState(State):
    def __init__(self, manager, context, map_obj):
        super().__init__(manager)
        self.context = context
        self.map_obj = map_obj
        self.window = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        rect = pygame.Rect((w - 500) // 2, (h - 600) // 2, 500, 600)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="MAP STATISTICS"
        )

        text = self._generate_html()
        UITextBox(
            relative_rect=pygame.Rect(0, 0, rect.width - 30, rect.height - 60),
            html_text=text,
            manager=self.ui_manager,
            container=self.window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

    def _generate_html(self):
        stats = get_map_statistics(self.map_obj)
        total = sum(stats.values())

        html = f"<b>Total Tiles:</b> {total}<br><br>"
        html += "<b>Breakdown:</b><br>"

        for tid, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            tile = REGISTRY.get(tid)
            name = tile.name if tile else f"Unknown ({tid})"
            char = tile.char if tile else "?"
            html += f"[{char}] {name}: {count} ({pct:.1f}%)<br>"

        return html

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                self.manager.pop()

    def draw(self, surface):
        pass

def menu_statistics(manager, renderer, map_obj):
    manager.push(StatisticsState(manager, renderer, map_obj))


class EditorPauseState(MenuState):
    def __init__(self, manager, context, callback):
        self.callback = callback
        # Convert options to (label, callback) format for MenuState
        options_list = [
            "Resume",
            "Save Map",
            "Load Map",
            "Macro Manager",
            "Auto-Tiling Manager",
            "Autosave Settings",
            "Exit to Main Menu",
            "Quit Editor"
        ]
        
        menu_options = []
        for opt in options_list:
            # We create a closure to capture the option string
            # callback expects the option string
            menu_options.append((opt, lambda o=opt: self._on_select(o)))

        super().__init__(manager, context, "EDITOR MENU", menu_options)

    def _on_select(self, option):
        self.manager.pop()
        self.callback(option)

def menu_editor_pause(manager, context, callback):
    manager.push(EditorPauseState(manager, context, callback))
