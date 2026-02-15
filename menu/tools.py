import pygame
from state_engine import State
from tiles import REGISTRY

class BrushDefineState(State):
    def __init__(self, manager, context, callback):
        super().__init__(manager)
        self.context = context
        self.callback = callback
        self.size = 3
        self.brush = [[False for _ in range(self.size)] for _ in range(self.size)]
        self.by, self.bx = 0, 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and self.by > 0: self.by -= 1
            elif event.key == pygame.K_DOWN and self.by < self.size - 1: self.by += 1
            elif event.key == pygame.K_LEFT and self.bx > 0: self.bx -= 1
            elif event.key == pygame.K_RIGHT and self.bx < self.size - 1: self.bx += 1
            elif event.key == pygame.K_SPACE: self.brush[self.by][self.bx] = not self.brush[self.by][self.bx]
            elif event.key == pygame.K_RETURN:
                self.manager.pop()
                self.callback(self.brush)
            elif event.key == pygame.K_ESCAPE:
                self.manager.pop()
                self.callback(None)

    def draw(self, surface):
        self.context.screen.fill((0,0,0))
        self.context.screen.blit(self.context.font.render(f"Brush {self.size}x{self.size} (Space=Toggle, Enter=Save)", True, (255,255,255)), (10,10))
        start_x, start_y = 50, 50
        cell_s = 30
        for r in range(self.size):
            for c in range(self.size):
                rect = (start_x + c * cell_s, start_y + r * cell_s, cell_s, cell_s)
                color = (200, 200, 200) if self.brush[r][c] else (50, 50, 50)
                pygame.draw.rect(surface, color, rect)
                pygame.draw.rect(surface, (255, 255, 255), rect, 1)
                if r == self.by and c == self.bx:
                    pygame.draw.rect(surface, (255, 0, 0), rect, 2)

class PatternDefineState(State):
    def __init__(self, manager, context, size, callback):
        super().__init__(manager)
        self.context = context
        self.size = size
        self.callback = callback
        self.pattern = [['.' for _ in range(size)] for _ in range(size)]
        self.by, self.bx = 0, 0

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP and self.by > 0: self.by -= 1
            elif event.key == pygame.K_DOWN and self.by < self.size - 1: self.by += 1
            elif event.key == pygame.K_LEFT and self.bx > 0: self.bx -= 1
            elif event.key == pygame.K_RIGHT and self.bx < self.size - 1: self.bx += 1
            elif event.key == pygame.K_RETURN:
                self.manager.pop()
                self.callback(self.pattern)
            elif event.key == pygame.K_ESCAPE:
                self.manager.pop()
                self.callback(None)
            elif event.unicode and event.unicode.isprintable():
                self.pattern[self.by][self.bx] = event.unicode

    def draw(self, surface):
        self.context.screen.fill((0,0,0))
        self.context.screen.blit(self.context.font.render(f"Pattern {self.size}x{self.size} (Enter char, Enter=Save)", True, (255,255,255)), (10,10))
        start_x, start_y = 50, 50
        cell_s = 30
        for r in range(self.size):
            for c in range(self.size):
                rect = (start_x + c * cell_s, start_y + r * cell_s, cell_s, cell_s)
                pygame.draw.rect(surface, (50, 50, 50), rect)
                pygame.draw.rect(surface, (255, 255, 255), rect, 1)
                if r == self.by and c == self.bx:
                    pygame.draw.rect(surface, (255, 0, 0), rect, 2)
                glyph = self.context.get_glyph(REGISTRY.get_by_char(self.pattern[r][c]))
                if glyph:
                    surface.blit(glyph, (rect[0]+5, rect[1]+5))

def menu_define_brush(context, callback):
    context.manager.push(BrushDefineState(context.manager, context, callback))

def menu_define_pattern(context, callback):
    from menu.base import TextInputState
    def on_size(inp):
        try:
            size = max(1, min(5, int(inp or "2")))
            context.manager.push(PatternDefineState(context.manager, context, size, callback))
        except: pass
    context.manager.push(TextInputState(context.manager, context, "Pattern size (max 5): ", on_size))
