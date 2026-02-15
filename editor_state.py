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
        
        self.panning = False
        self.pan_start_pos = (0, 0)
        self.pan_start_cam = (0, 0)
        
        # Register map listener
        self._register_map_listener()

    def _register_map_listener(self):
        # Remove from old map if needed (though session usually has one map)
        self.session.map_obj.listeners.append(self._on_map_change)

    def _on_map_change(self, x, y):
        if x is None or y is None:
            self.renderer.invalidate_cache()
        else:
            self.renderer.invalidate_chunk(x, y)

    def enter(self, **kwargs):
        # We could show a "Toast" message here or something
        pass

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.input_handler.process_key(event.key, event.unicode, self.manager)
        elif event.type == pygame.KEYUP:
            self.input_handler.process_keyup(event.key)
        
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 2:
                self.panning = False

        elif event.type == pygame.MOUSEMOTION:
            mx, my = event.pos
            
            if self.panning:
                tile_size = self.renderer.tile_size
                dx = (mx - self.pan_start_pos[0]) // tile_size
                dy = (my - self.pan_start_pos[1]) // tile_size
                
                self.session.camera_x = max(0, min(self.session.map_obj.width - self.session.view_width, self.pan_start_cam[0] - dx))
                self.session.camera_y = max(0, min(self.session.map_obj.height - self.session.view_height, self.pan_start_cam[1] - dy))

            # Only update map cursor if mouse is within the viewport (above status bar)
            if my < self.session.viewport_px_h:
                if self.session.tool_state.show_palette and self.palette_rects and self.palette_rects[0].collidepoint(mx, my):
                    pass
                else:
                    tile_size = self.renderer.tile_size
                    map_x = (mx // tile_size) + self.session.camera_x
                    map_y = (my // tile_size) + self.session.camera_y
                    
                    if 0 <= map_x < self.session.map_obj.width and 0 <= map_y < self.session.map_obj.height:
                        self.session.cursor_x = map_x
                        self.session.cursor_y = map_y

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 2: # Middle Click Panning
                self.panning = True
                self.pan_start_pos = event.pos
                self.pan_start_cam = (self.session.camera_x, self.session.camera_y)
                return

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
                self.input_handler.process_mouse(event.button, self.manager)

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
             self.input_handler.handle_mouse_hold(self.manager)

        if not self.session.running:
            self.manager.pop()
            return

        # Handle queued actions if any (from macros)
        if self.session.action_queue:
            action = self.session.action_queue.popleft()
            self.input_handler.dispatch(action, self.manager)
            
    def draw(self, surface):
        self.renderer.clear()
        self.renderer.draw_map(self.session)
        self.renderer.draw_status(self.session)
        self.palette_rects = self.renderer.draw_palette(self.session)
        # Note: We don't flip here, the StateManager does
