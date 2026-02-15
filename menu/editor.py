import pygame
import sys
from tiles import REGISTRY
from menu.base import _render_menu_generic, get_map_statistics
from state_engine import State

class StatisticsState(State):
    def __init__(self, manager, context, map_obj):
        super().__init__(manager)
        self.context = context
        self.map_obj = map_obj
        self.lines = self._generate_stats()

    def _generate_stats(self):
        stats = get_map_statistics(self.map_obj)
        total = sum(stats.values())
        lines = ["=== MAP STATISTICS ===", "", f"Total tiles: {total}", ""]
        for tid, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            pct = (count / total * 100) if total > 0 else 0
            tile = REGISTRY.get(tid)
            name = tile.char if tile else str(tid)
            lines.append(f"'{name}': {count} ({pct:.1f}%)")
        lines.append("")
        lines.append("Press any key to continue...")
        return lines

    def handle_event(self, event):
        if event.type in [pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN]:
            self.manager.pop()

    def draw(self, surface):
        _render_menu_generic(self.context, "Statistics", self.lines)

def menu_statistics(context, map_obj):
    context.manager.push(StatisticsState(context.manager, context, map_obj))

class EditorPauseState(State):
    def __init__(self, manager, context, callback):
        super().__init__(manager)
        self.context = context
        self.callback = callback
        self.options = ["Resume", "Save Map", "Load Map", "Macro Manager", "Auto-Tiling Manager", "Autosave Settings", "Exit to Main Menu", "Quit Editor"]
        self.selected = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        if event.key == pygame.K_UP:
            self.selected = (self.selected - 1) % len(self.options)
        elif event.key == pygame.K_DOWN:
            self.selected = (self.selected + 1) % len(self.options)
        elif event.key == pygame.K_ESCAPE:
            self.manager.pop()
            self.callback("Resume")
        elif event.key == pygame.K_RETURN:
            self.manager.pop()
            self.callback(self.options[self.selected])

    def draw(self, surface):
        _render_menu_generic(self.context, "=== EDITOR MENU ===", self.options, self.selected)

def menu_editor_pause(context, callback):
    # This now pushes a state. Note that handle_editor_menu in actions.py needs to be updated.
    context.manager.push(EditorPauseState(context.manager, context, callback))
