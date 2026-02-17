import pygame
import pygame_gui
from pygame_gui.elements import UIPanel, UILabel, UIButton, UIWindow, UIScrollingContainer
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
        
        # UI Elements
        self.status_panel = None
        self.labels = {}
        self.palette_window = None
        self.palette_buttons = {} # btn -> tile_id
        
        # Panning state
        self.panning = False
        self.pan_start_pos = (0, 0)
        self.pan_start_cam = (0, 0)
        
        # Track current map
        self.current_map = self.session.map_obj
        self._register_map_listener(self.current_map)

        # Initial resize to set viewport
        self._update_viewport()

    def _change_level(self, delta):
        new_z = max(0, self.session.active_z_level + delta)
        if new_z != self.session.active_z_level:
            self.session.active_z_level = new_z
            self.labels['level_val'].set_text(str(new_z))
            self.renderer.invalidate_cache()

    def _update_viewport(self):
        self.renderer.update_dimensions()
        # Reserve space for status bar at bottom (150px)
        self.session.viewport_px_w = self.renderer.width
        self.session.viewport_px_h = self.renderer.height - 150
        self.session.view_width = self.session.viewport_px_w // self.renderer.tile_size
        self.session.view_height = self.session.viewport_px_h // self.renderer.tile_size

    def _register_map_listener(self, map_obj):
        map_obj.listeners.append(self._on_map_change)

    def _unregister_map_listener(self, map_obj):
        if self._on_map_change in map_obj.listeners:
            map_obj.listeners.remove(self._on_map_change)

    def _on_map_change(self, x, y):
        if x is None or y is None:
            self.renderer.invalidate_cache()
        else:
            self.renderer.invalidate_chunk(x, y)

    def enter(self, **kwargs):
        self._build_ui()

    def exit(self):
        if self.status_panel:
            self.status_panel.kill()
        if self.palette_window:
            self.palette_window.kill()

    def _build_ui(self):
        if self.status_panel: self.status_panel.kill()

        w, h = self.renderer.screen.get_size()

        # Status Panel at bottom
        self.status_panel = UIPanel(
            relative_rect=pygame.Rect(0, h - 150, w, 150),
            manager=self.ui_manager
        )

        # Labels
        # Row 1: Mode, Cursor, Camera
        self.labels['mode'] = UILabel(pygame.Rect(10, 10, 200, 20), "MODE: --", self.ui_manager, container=self.status_panel, object_id="#unicode_label")
        self.labels['cursor'] = UILabel(pygame.Rect(220, 10, 200, 20), "CURSOR: 0,0", self.ui_manager, container=self.status_panel, object_id="#unicode_label")
        self.labels['camera'] = UILabel(pygame.Rect(440, 10, 200, 20), "CAMERA: 0,0", self.ui_manager, container=self.status_panel, object_id="#unicode_label")

        # Row 2: Brush, Autotile, Snap
        self.labels['brush'] = UILabel(pygame.Rect(10, 35, 200, 20), "BRUSH: 1x1", self.ui_manager, container=self.status_panel, object_id="#unicode_label")
        self.labels['autotile'] = UILabel(pygame.Rect(220, 35, 200, 20), "AUTOTILE: OFF", self.ui_manager, container=self.status_panel, object_id="#unicode_label")
        self.labels['snap'] = UILabel(pygame.Rect(440, 35, 200, 20), "SNAP: OFF", self.ui_manager, container=self.status_panel, object_id="#unicode_label")

        # Row 3: Stats, Help, Macro
        self.labels['map'] = UILabel(pygame.Rect(10, 60, 200, 20), f"MAP: {self.session.map_obj.width}x{self.session.map_obj.height}", self.ui_manager, container=self.status_panel, object_id="#unicode_label")
        self.labels['history'] = UILabel(pygame.Rect(220, 60, 200, 20), "UNDO: 0 / REDO: 0", self.ui_manager, container=self.status_panel, object_id="#unicode_label")
        self.labels['help'] = UILabel(pygame.Rect(440, 60, 300, 20), "[F1] Menu | [?] Help", self.ui_manager, container=self.status_panel, object_id="#unicode_label")

        # Macro Dropdown and Controls
        self.labels['macro_lbl'] = UILabel(pygame.Rect(10, 85, 100, 20), "MACRO:", self.ui_manager, container=self.status_panel)
        macro_options = list(self.session.tool_state.macros.keys())
        if not macro_options: macro_options = ["None"]
        self.macro_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=macro_options,
            starting_option=self.session.tool_state.selected_macro or macro_options[0],
            relative_rect=pygame.Rect(110, 85, 150, 30),
            manager=self.ui_manager,
            container=self.status_panel
        )
        self.macro_play_btn = UIButton(pygame.Rect(270, 85, 80, 30), "PLAY", self.ui_manager, container=self.status_panel)
        self.macro_rec_btn = UIButton(pygame.Rect(360, 85, 80, 30), "REC", self.ui_manager, container=self.status_panel)
        self.macro_iter_btn = UIButton(pygame.Rect(450, 85, 80, 30), f"ITER: {self.session.tool_state.macro_iterations}", self.ui_manager, container=self.status_panel)

        # Level Controls
        self.labels['level_lbl'] = UILabel(pygame.Rect(540, 85, 60, 20), "LEVEL:", self.ui_manager, container=self.status_panel)
        self.level_down_btn = UIButton(pygame.Rect(600, 85, 30, 30), "-", self.ui_manager, container=self.status_panel)
        self.labels['level_val'] = UILabel(pygame.Rect(630, 85, 40, 30), str(self.session.active_z_level), self.ui_manager, container=self.status_panel)
        self.level_up_btn = UIButton(pygame.Rect(670, 85, 30, 30), "+", self.ui_manager, container=self.status_panel)

        # Measurement / Sector Info
        self.labels['sector'] = UILabel(pygame.Rect(w - 450, 85, 220, 20), "SECTOR: --", self.ui_manager, container=self.status_panel, object_id="#unicode_label")
        self.labels['local_coord'] = UILabel(pygame.Rect(w - 450, 110, 220, 20), "LOCAL: --", self.ui_manager, container=self.status_panel, object_id="#unicode_label")

        # Selected Tile Preview (Right side of status)
        self.labels['tile_preview'] = UILabel(pygame.Rect(w - 220, 5, 200, 55), "TILE: [?]", self.ui_manager, container=self.status_panel, object_id="#unicode_label_large")
        self.labels['tile_name'] = UILabel(pygame.Rect(w - 220, 60, 200, 20), "Unknown", self.ui_manager, container=self.status_panel)

        self._build_palette()

    def _build_palette(self):
        if self.palette_window:
            self.palette_window.kill()
            self.palette_window = None
            self.palette_buttons = {}

        if not self.session.tool_state.show_palette:
            return

        w, h = self.renderer.screen.get_size()
        win_w, win_h = 320, h - 100

        self.palette_window = UIWindow(
            rect=pygame.Rect(w - win_w - 20, 20, win_w, win_h),
            manager=self.ui_manager,
            window_display_title="PALETTE",
            resizable=True
        )

        container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, win_w - 30, win_h - 40),
            manager=self.ui_manager,
            container=self.palette_window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

        tiles = REGISTRY.get_all()
        # Grid view: Icon only with tooltips
        cols = 6
        tile_size = 32
        padding = 8
        
        num_rows = (len(tiles) + cols - 1) // cols
        scroll_h = num_rows * (tile_size + padding) + padding

        container.set_scrollable_area_dimensions((win_w - 50, scroll_h))
        
        for i, tile in enumerate(tiles):
            c = i % cols
            r = i // cols
            
            px = padding + c * (tile_size + padding)
            py = padding + r * (tile_size + padding)

            # Generate glyph surface (32x32)
            base_surf = self.renderer.get_glyph(tile.id)
            if base_surf:
                glyph_surf = pygame.transform.scale(base_surf, (tile_size, tile_size))
            else:
                glyph_surf = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
            
            # Create UIImage
            img = pygame_gui.elements.UIImage(
                relative_rect=pygame.Rect(px, py, tile_size, tile_size),
                image_surface=glyph_surf,
                manager=self.ui_manager,
                container=container
            )
            
            # Create Transparent Button
            btn = UIButton(
                relative_rect=pygame.Rect(px, py, tile_size, tile_size),
                text="",
                manager=self.ui_manager,
                container=container,
                object_id="#palette_icon"
            )
            btn.tool_tip_text = f"{tile.name} ([{tile.char}])"
            self.palette_buttons[btn] = tile.id


    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self._update_viewport()
            self._build_ui()
            return

        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element in self.palette_buttons:
                tid = self.palette_buttons[event.ui_element]
                self.session.selected_tile_id = tid
                self._update_ui_labels()
                return
            elif event.ui_element == self.macro_play_btn:
                from actions.macro import handle_macro_play
                handle_macro_play(self.session, self.manager)
            elif event.ui_element == self.macro_rec_btn:
                from actions.macro import handle_macro_toggle
                handle_macro_toggle(self.session, self.manager)
                self._rebuild_macro_ui()
            elif event.ui_element == self.macro_iter_btn:
                from actions.macro import handle_macro_set_iterations
                handle_macro_set_iterations(self.session, self.manager)
            elif event.ui_element == self.level_down_btn:
                self._change_level(-1)
            elif event.ui_element == self.level_up_btn:
                self._change_level(1)

        if event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED:
            if event.ui_element == self.macro_dropdown:
                if event.text != "None":
                    self.session.tool_state.selected_macro = event.text
                    self.session.tool_state.mode = 'macro'
                else:
                    self.session.tool_state.selected_macro = None
                    if self.session.tool_state.mode == 'macro':
                        self.session.tool_state.mode = 'place'

        if event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.palette_window:
                self.session.tool_state.show_palette = False
                self.palette_window = None # It kills itself

        if event.type == pygame.KEYDOWN:
            self.input_handler.process_key(event.key, event.unicode, self.manager)
            # Rebuild palette if toggled via key
            if event.key == pygame.K_p: # Assuming 'p' toggles palette? Need to check bindings.
                # Actually InputHandler processes action.
                pass
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

            # Update Cursor (only if not over UI)
            # We check if mouse is over any UI element
            # But simpler: check if Y < viewport_px_h
            if my < self.session.viewport_px_h:
                # Also check if not over palette window
                over_palette = False
                if self.palette_window and self.palette_window.rect.collidepoint((mx, my)):
                    over_palette = True

                if not over_palette:
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

            # Click on map
            mx, my = event.pos
            if my < self.session.viewport_px_h:
                over_palette = False
                if self.palette_window and self.palette_window.rect.collidepoint((mx, my)):
                    over_palette = True

                if not over_palette:
                    if self.session.tool_state.mode == 'macro':
                        from actions.macro import handle_macro_play
                        handle_macro_play(self.session, self.manager)
                    else:
                        self.input_handler.process_mouse(event.button, self.manager)

    def update(self, dt):
        if self.session.map_obj is not self.current_map:
            # Preserve callback if recording
            cb = self.current_map.on_tile_changed_callback
            self._unregister_map_listener(self.current_map)
            self.current_map = self.session.map_obj
            self._register_map_listener(self.current_map)
            self.current_map.on_tile_changed_callback = cb
            self.renderer.invalidate_cache()

        self.input_handler.check_held_keys()
        
        # Check palette toggle (state vs UI existence)
        if self.session.tool_state.show_palette and not self.palette_window:
            self._build_palette()
        elif not self.session.tool_state.show_palette and self.palette_window:
            self.palette_window.kill()
            self.palette_window = None

        # Continuous mouse paint
        mx, my = pygame.mouse.get_pos()
        if my < self.session.viewport_px_h:
            over_palette = False
            if self.palette_window and self.palette_window.rect.collidepoint((mx, my)):
                over_palette = True

            if not over_palette:
                self.input_handler.handle_mouse_hold(self.manager)

        if not self.session.running:
            self.manager.pop()
            return

        if self.session.action_queue:
            action = self.session.action_queue.popleft()
            self.input_handler.dispatch(action, self.manager)

        self._update_ui_labels()

    def _update_ui_labels(self):
        if not self.labels or 'mode' not in self.labels:
            return

        ts = self.session.tool_state

        mode_str = ts.mode.upper()
        if ts.recording: mode_str += " (REC)"

        self.labels['mode'].set_text(f"MODE: {mode_str}")
        self.labels['cursor'].set_text(f"CURSOR: {self.session.cursor_x}, {self.session.cursor_y}")
        self.labels['camera'].set_text(f"CAMERA: {self.session.camera_x}, {self.session.camera_y}")
        self.labels['brush'].set_text(f"BRUSH: {ts.brush_size}x{ts.brush_size}")
        self.labels['autotile'].set_text(f"AUTOTILE: {'ON' if ts.auto_tiling else 'OFF'}")
        self.labels['snap'].set_text(f"SNAP: {'ON' if ts.snap_size > 1 else 'OFF'}")
        self.labels['map'].set_text(f"MAP: {self.session.map_obj.width}x{self.session.map_obj.height}")
        self.labels['history'].set_text(f"UNDO: {self.session.undo_stack.undo_count} / REDO: {self.session.undo_stack.redo_count}")

        if hasattr(self, 'macro_rec_btn'):
            self.macro_rec_btn.set_text("STOP" if ts.recording else "REC")
            self.macro_iter_btn.set_text(f"ITER: {ts.macro_iterations}")
            # Update dropdown if macro count changed
            if len(ts.macros) != len(self.macro_dropdown.options_list) - (1 if "None" in self.macro_dropdown.options_list else 0):
                 self._rebuild_macro_ui()
            
            if 'level_val' in self.labels:
                self.labels['level_val'].set_text(str(self.session.active_z_level))

            # Sync selection (if it changed externally via context menu)
            curr_sel = self.macro_dropdown.selected_option
            target_sel = ts.selected_macro or "None"
            if curr_sel != target_sel:
                # We don't want to kill/rebuild every frame, only if mismatch
                # But UIDropDownMenu is tricky to just 'set'
                # Rebuilding is safest to ensure visual sync
                self._rebuild_macro_ui()

        # Update Sector Info
        if 'sector' in self.labels:
            grid_size = ts.measurement_config.get('grid_size', 100)
            sec_x = self.session.cursor_x // grid_size
            sec_y = self.session.cursor_y // grid_size
            rel_x = self.session.cursor_x % grid_size
            rel_y = self.session.cursor_y % grid_size
            self.labels['sector'].set_text(f"SECTOR: {sec_x}, {sec_y}")
            self.labels['local_coord'].set_text(f"LOCAL: {rel_x}, {rel_y}")

        t = REGISTRY.get(self.session.selected_tile_id)
        if t:
            # Use color if available
            self.labels['tile_preview'].set_text(f"TILE: [{t.char}]")
            self.labels['tile_name'].set_text(t.name)

    def _rebuild_macro_ui(self):
        macro_options = list(self.session.tool_state.macros.keys())
        if not macro_options: macro_options = ["None"]
        current = self.session.tool_state.selected_macro or macro_options[0]
        
        # This is a bit hacky but pygame_gui doesn't always like list updates
        self.macro_dropdown.kill()
        self.macro_dropdown = pygame_gui.elements.UIDropDownMenu(
            options_list=macro_options,
            starting_option=current if current in macro_options else macro_options[0],
            relative_rect=pygame.Rect(110, 85, 150, 30),
            manager=self.ui_manager,
            container=self.status_panel
        )
            
    def draw(self, surface):
        self.renderer.clear()
        self.renderer.draw_map(self.session)
        # UI is drawn by StateManager
