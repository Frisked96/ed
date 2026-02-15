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

    def push(self, state: State, **kwargs):
        if self.states:
            # We don't exit the previous state, we just pause it effectively
            pass
        self.states.append(state)
        state.enter(**kwargs)

    def pop(self):
        if self.states:
            top = self.states.pop()
            top.exit()
        if self.states:
            # Resume previous state if needed
            pass

    def set(self, state: State, **kwargs):
        while self.states:
            self.pop()
        self.push(state, **kwargs)

    @property
    def current_state(self) -> Optional[State]:
        return self.states[-1] if self.states else None

    def run(self):
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            
            # Event Loop
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                
                self.ui_manager.process_events(event)
                
                # Only the top-most state handles events
                if self.states:
                    self.states[-1].handle_event(event)

            # Update
            self.ui_manager.update(dt)
            if self.states:
                self.states[-1].update(dt)

            # Draw
            # Draw all states from bottom to top (allows overlays)
            # We don't clear the screen here anymore; individual states decide if they fill the background
            for state in self.states:
                state.draw(self.screen)
            
            self.ui_manager.draw_ui(self.screen)
            pygame.display.flip()
            
        pygame.display.quit()
        pygame.quit()
        sys.exit()
