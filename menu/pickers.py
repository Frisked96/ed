import pygame
from statemachine import StateMachine, State as SMState
from state_engine import State
from utils import get_all_colors
from tiles import REGISTRY
from menu.base import _render_menu_generic, TextInputState

class ColorPickerMachine(StateMachine):
    selecting = SMState(initial=True)
    typing_custom = SMState()
    
    start_custom = selecting.to(typing_custom)

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
                    def on_custom(val):
                        if val:
                            self.callback(val)
                        # We don't need to pop here because TextInputState already popped itself
                        # and we want to be back at whatever state was before ColorPicker?
                        # Actually ColorPicker is still on stack.
                        self.manager.pop()
                    
                    self.manager.push(TextInputState(self.manager, self.context, "Color Name or R,G,B: ", on_custom))

    def draw(self, surface):
        lines = [opt.capitalize() if i < len(self.names) else opt 
                 for i, opt in enumerate(self.options)]
        _render_menu_generic(self.context, "SELECT COLOR", lines, self.selected)

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
            
            glyph = self.context.get_glyph(tile.id)
            surface.blit(glyph, (px, py))

class MultiTilePickerState(State):
    def __init__(self, manager, context, callback, initial_selection=None):
        super().__init__(manager)
        self.context = context
        self.callback = callback
        self.all_tiles = REGISTRY.get_all()
        self.selected_indices = set()
        if initial_selection:
            for idx, tile in enumerate(self.all_tiles):
                if tile.id in initial_selection:
                    self.selected_indices.add(idx)
                    
        self.cursor_idx = 0
        self.cols = (context.width - 40) // (context.tile_size + 10) or 1

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        if event.key == pygame.K_UP: self.cursor_idx = (self.cursor_idx - self.cols) % len(self.all_tiles)
        elif event.key == pygame.K_DOWN: self.cursor_idx = (self.cursor_idx + self.cols) % len(self.all_tiles)
        elif event.key == pygame.K_LEFT: self.cursor_idx = (self.cursor_idx - 1) % len(self.all_tiles)
        elif event.key == pygame.K_RIGHT: self.cursor_idx = (self.cursor_idx + 1) % len(self.all_tiles)
        elif event.key == pygame.K_SPACE:
            if self.cursor_idx in self.selected_indices:
                self.selected_indices.remove(self.cursor_idx)
            else:
                self.selected_indices.add(self.cursor_idx)
        elif event.key == pygame.K_RETURN:
            selected_ids = [self.all_tiles[i].id for i in self.selected_indices]
            self.callback(selected_ids)
            self.manager.pop()
        elif event.key == pygame.K_ESCAPE:
            self.manager.pop()

    def draw(self, surface):
        s = pygame.Surface((self.context.width, self.context.height), pygame.SRCALPHA)
        s.fill((0, 0, 0, 220))
        surface.blit(s, (0, 0))
        
        surface.blit(self.context.font.render("SELECT TILES (SPACE to toggle, ENTER to confirm)", True, (255, 255, 255)), (20, 20))
        
        for i, tile in enumerate(self.all_tiles):
            row = i // self.cols
            col = i % self.cols
            px = 20 + col * (self.context.tile_size + 10)
            py = 60 + row * (self.context.tile_size + 10)
            
            # Draw selection highlight
            if i in self.selected_indices:
                pygame.draw.rect(surface, (0, 255, 0), (px-2, py-2, self.context.tile_size+4, self.context.tile_size+4), 0)
                
            # Draw cursor
            if i == self.cursor_idx:
                pygame.draw.rect(surface, (255, 255, 0), (px-2, py-2, self.context.tile_size+4, self.context.tile_size+4), 2)
            
            glyph = self.context.get_glyph(tile.id)
            surface.blit(glyph, (px, py))
