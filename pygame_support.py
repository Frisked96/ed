import pygame
import sys

class PygameContext:
    def __init__(self, width=800, height=600, tile_size=20, font_name=None, font_size=20):
        pygame.init()
        self.tile_size = tile_size
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
        pygame.display.set_caption("Advanced Map Editor (Pygame)")

        # Initialize font
        self.font_size = font_size
        try:
            # Try to load a monospace system font
            self.font = pygame.font.SysFont("Courier New", self.font_size, bold=True)
            if not self.font:
                 self.font = pygame.font.SysFont("monospace", self.font_size, bold=True)
        except:
            self.font = pygame.font.Font(None, self.font_size)

        self.clock = pygame.time.Clock()

        # Calculate grid dimensions based on window size
        self.cols = width // tile_size
        self.rows = height // tile_size

        # Enable key repeat
        pygame.key.set_repeat(300, 50)

    def update_dimensions(self):
        w, h = self.screen.get_size()
        self.width = w
        self.height = h
        self.cols = w // self.tile_size
        self.rows = h // self.tile_size

    def clear(self):
        self.screen.fill((0, 0, 0))

    def flip(self):
        pygame.display.flip()
        self.clock.tick(60)

    def get_events(self):
        return pygame.event.get()

    def quit(self):
        pygame.quit()
        sys.exit()
