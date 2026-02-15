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
        self.ui_manager = pygame_gui.UIManager(screen.get_size())
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
