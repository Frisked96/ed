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
        
        # Set initial fixed pixel dimensions
        self.session.viewport_px_w = self.renderer.width
        self.session.viewport_px_h = self.renderer.height - 120
        
        self.palette_rects = None

    def enter(self, **kwargs):
        # We could show a "Toast" message here or something
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.input_handler.process_key(event.key, event.unicode, self.renderer)
        elif event.type == pygame.KEYUP:
            self.input_handler.process_keyup(event.key)
        
        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            
            # Palette interaction (block cursor update)
            if self.session.tool_state.show_palette and self.palette_rects and self.palette_rects[0].collidepoint(mx, my):
                pass
            else:
                tile_size = self.renderer.tile_size
                # Calculate map coordinates based on camera position
                map_x = (mx // tile_size) + self.session.camera_x
                map_y = (my // tile_size) + self.session.camera_y
                
                # Update cursor position if within bounds
                if 0 <= map_x < self.session.map_obj.width and 0 <= map_y < self.session.map_obj.height:
                    self.session.cursor_x = map_x
                    self.session.cursor_y = map_y

        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Check Palette Interaction
            handled = False
            if self.session.tool_state.show_palette and self.palette_rects:
                main_rect, clickables = self.palette_rects
                if main_rect.collidepoint(event.pos):
                    # Check if clicked a specific tile
                    for r, tid in clickables:
                        if r.collidepoint(event.pos):
                            self.session.selected_tile_id = tid
                            break
                    handled = True

            if not handled:
                # Dispatch mouse button press as an action
                # event.button is 1 (left), 2 (middle), 3 (right), 4 (scroll up), 5 (scroll down)
                self.input_handler.process_mouse(event.button, self.renderer)

        elif event.type == pygame.VIDEORESIZE:
            self.renderer.update_dimensions()
            self.session.viewport_px_w = self.renderer.width
            self.session.viewport_px_h = self.renderer.height - 120
            
            # Update tile counts based on new pixel area
            self.session.view_width = self.session.viewport_px_w // self.renderer.tile_size
            self.session.view_height = self.session.viewport_px_h // self.renderer.tile_size


    def update(self, dt):
        # Sync keys to prevent stuck inputs after modal dialogs
        self.input_handler.check_held_keys()
        
        # Support continuous mouse painting (hold to paint)
        mx, my = pygame.mouse.get_pos()
        if not (self.session.tool_state.show_palette and self.palette_rects and self.palette_rects[0].collidepoint(mx, my)):
             self.input_handler.handle_mouse_hold(self.renderer)

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
        self.palette_rects = self.renderer.draw_palette(self.session)
        # Note: We don't flip here, the StateManager does
