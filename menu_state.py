import pygame
import sys
from state_engine import State
from core import EditorSession, DEFAULT_VIEW_WIDTH, DEFAULT_VIEW_HEIGHT
from map_io import load_config
from editor_state import EditorState
from menus import (
    NewMapState, LoadMapState, TileRegistryState, 
    ControlSettingsState, MacroManagerState, AutoTilingManagerState
)
from tiles import REGISTRY

class MainMenuState(State):
    def __init__(self, manager, renderer):
        super().__init__(manager)
        self.renderer = renderer
        self.font = renderer.font
        self.options = [
            "1. New Map",
            "2. Load Map",
            "3. Define Custom Tiles",
            "4. Macro Manager",
            "5. Edit Controls",
            "6. Auto-Tiling Manager",
            "Q. Quit"
        ]
        # Pre-load config/macros/rules to pass to session
        self.bindings = load_config()
        self.macros = {} 
        self.tiling_rules = {}

    def draw(self, surface):
        self.renderer.clear()
        
        # Draw Title
        title = self.font.render("=== ADVANCED MAP EDITOR ===", True, (255, 255, 255))
        self.renderer.screen.blit(title, (10, 10))
        
        # Draw Options
        for i, opt in enumerate(self.options):
            text = self.font.render(opt, True, (200, 200, 200))
            self.renderer.screen.blit(text, (20, 50 + i * 30))
            
        # We don't need to flip, StateManager does it

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                self.manager.push(NewMapState(self.manager, self.renderer, DEFAULT_VIEW_WIDTH, DEFAULT_VIEW_HEIGHT, self.start_editor))
            elif event.key == pygame.K_2:
                self.manager.push(LoadMapState(self.manager, self.renderer, DEFAULT_VIEW_WIDTH, DEFAULT_VIEW_HEIGHT, self.start_editor))
            elif event.key == pygame.K_3:
                self.manager.push(TileRegistryState(self.manager, self.renderer))
            elif event.key == pygame.K_4:
                from core import ToolState
                ts = ToolState(macros=self.macros)
                self.manager.push(MacroManagerState(self.manager, self.renderer, ts))
            elif event.key == pygame.K_5:
                self.manager.push(ControlSettingsState(self.manager, self.renderer, self.bindings))
            elif event.key == pygame.K_6:
                from core import ToolState
                ts = ToolState(tiling_rules=self.tiling_rules)
                self.manager.push(AutoTilingManagerState(self.manager, self.renderer, ts))
            elif event.key == pygame.K_q:
                sys.exit()

    def start_editor(self, map_obj):
        session = EditorSession(
            map_obj, 
            DEFAULT_VIEW_WIDTH, 
            DEFAULT_VIEW_HEIGHT, 
            self.bindings, 
            macros=self.macros, 
            tiling_rules=self.tiling_rules
        )
        editor = EditorState(self.manager, session, self.renderer)
        self.manager.push(editor)
