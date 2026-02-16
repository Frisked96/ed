import pygame
import pygame_gui
import sys
from typing import Optional

class State:
    def __init__(self, manager):
        self.manager = manager
        self.ui_manager = manager.ui_manager

    def enter(self, **kwargs):
        pass

    def exit(self):
        pass

    def handle_event(self, event: pygame.event.Event):
        """Handle raw pygame events."""
        pass

    def update(self, dt: float):
        """Update logic. dt is delta time in seconds."""
        pass

    def draw(self, surface: pygame.Surface):
        """Render to the screen."""
        pass

class StateManager:
    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.running = True
        self.states = []
        self.ui_manager = pygame_gui.UIManager(screen.get_size(), "theme.json")
        
        # Try to load a font that supports Unicode for the UI
        from utils import test_unicode_support
        font_names = ["dejavusansmono", "freemono", "notomono", "liberationmono", "ubuntumono", "notosans", "notosanssymbols", "unifont", "arialunicodems", "seguisym", "couriernew", "monospace"]
        found_path = None
        found_bold_path = None
        
        for name in font_names:
            try:
                # Test with SysFont first to see if it renders unicode
                test_font = pygame.font.SysFont(name, 18)
                if test_unicode_support(test_font):
                    found_path = pygame.font.match_font(name)
                    found_bold_path = pygame.font.match_font(name, bold=True)
                    if found_path:
                        break
            except:
                continue
        
        if found_path:
            # Register it as 'app_font' AND 'default' to be sure
            actual_bold = found_bold_path if found_bold_path else found_path
            self.ui_manager.add_font_paths("app_font", found_path, actual_bold)
            self.ui_manager.add_font_paths("default", found_path, actual_bold)
            
            # Preload various sizes
            sizes = [14, 16, 18, 20, 24, 32, 36, 48, 64]
            preload_list = []
            for size in sizes:
                preload_list.append({"name": "app_font", "point_size": size, "style": "regular"})
                preload_list.append({"name": "app_font", "point_size": size, "style": "bold"})
            
            self.ui_manager.preload_fonts(preload_list)
            # Re-load theme to make sure it picks up the new font definitions
            self.ui_manager.get_theme().load_theme("theme.json")
        else:
            print("DEBUG: No Unicode font found! Falling back to sans-serif.")
            # Fallback to whatever pygame can find that might be better than the default
            self.ui_manager.preload_fonts([{"name": "sans-serif", "point_size": 14, "style": "regular"}])

        self.clock = pygame.time.Clock()
        self.notifications = []

    def notify(self, text, duration=2.0, color=(0, 255, 0)):
        import time
        self.notifications.append({
            "text": text,
            "expiry": time.time() + duration,
            "color": color
        })

    def _update_notifications(self):
        import time
        now = time.time()
        self.notifications = [n for n in self.notifications if n["expiry"] > now]

    def push(self, state, **kwargs):
        self.states.append(state)
        state.enter(**kwargs)

    def pop(self):
        if self.states:
            top = self.states.pop()
            top.exit()
            # Safety: Ensure text input is stopped
            pygame.key.stop_text_input()
        if self.states:
            # Re-sync keys for the resuming state
            pass

    def set(self, state, **kwargs):
        """Clear the stack and set a new root state."""
        while self.states:
            top = self.states.pop()
            top.exit()
        
        # Reset global Pygame states
        pygame.key.stop_text_input()
        
        self.push(state, **kwargs)

    def change_state(self, state, **kwargs):
        """Alias for set() to encourage centralized transitions."""
        self.set(state, **kwargs)

    @property
    def current_state(self):
        return self.states[-1] if self.states else None

    def run(self, renderer):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self._update_notifications()
            
            # Event Loop
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11:
                        # Toggle Fullscreen
                        is_fullscreen = self.screen.get_flags() & pygame.FULLSCREEN
                        if is_fullscreen:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.RESIZABLE)
                        else:
                            self.screen = pygame.display.set_mode(self.screen.get_size(), pygame.FULLSCREEN)
                        
                        self.ui_manager.set_window_resolution(self.screen.get_size())
                        renderer.screen = self.screen
                        renderer.update_dimensions()

                if event.type == pygame.VIDEORESIZE:
                    # Pygame updates the display surface automatically when using RESIZABLE.
                    # We just need to notify our systems of the new size and refresh references.
                    self.ui_manager.set_window_resolution(event.size)
                    self.screen = pygame.display.get_surface()
                    renderer.screen = self.screen
                    renderer.update_dimensions()

                self.ui_manager.process_events(event)
                
                if self.states:
                    self.states[-1].handle_event(event)

            # Update
            self.ui_manager.update(dt)
            if self.states:
                self.states[-1].update(dt)

            # Draw
            for state in self.states:
                state.draw(self.screen)
            
            renderer.draw_notifications(self.notifications)
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()
            
        pygame.display.quit()
        pygame.quit()
        sys.exit()
