import pygame
from state_engine import State
from controller import InputHandler
from view import Renderer
from core import EditorSession
from tiles import REGISTRY

class EditorState(State):
    def __init__(self, manager, session: EditorSession, renderer: Renderer):
        super().__init__(manager)
        self.session = session
        self.renderer = renderer
        self.input_handler = InputHandler(session)
        self.renderer.update_dimensions()

    def enter(self, **kwargs):
        # We could show a "Toast" message here or something
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.input_handler.process_key(event.key, event.unicode, self.renderer)
        
        elif event.type == pygame.VIDEORESIZE:
            self.renderer.update_dimensions()
            self.session.view_width = min(self.session.view_width, self.renderer.width // self.renderer.tile_size)
            self.session.view_height = min(self.session.view_height, (self.renderer.height // self.renderer.tile_size) - 5)


    def update(self, dt):
        if not self.session.running:
            self.manager.pop()
            return

        # Handle queued actions if any (from macros)
        if self.session.action_queue:
            action = self.session.action_queue.popleft()
            self.input_handler.dispatch(action, self.renderer)
            
    def draw(self, surface):
        self.renderer.clear()
        self.renderer.draw_map(self.session)
        self.renderer.draw_status(self.session)
        if self.session.tool_state.show_palette:
             pass # Palette drawing needs update for ID based
        # Note: We don't flip here, the StateManager does
