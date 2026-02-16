import pygame
import pygame_gui
from pygame_gui.elements import UIButton, UILabel
from state_engine import State
from core import EditorSession
from map_io import load_config, load_macros
from editor_state import EditorState

class MainMenuState(State):
    def __init__(self, manager, renderer):
        super().__init__(manager)
        self.renderer = renderer
        self.ui_elements = []
        # Pre-load config/macros/rules to pass to session
        self.bindings = load_config()
        self.macros = load_macros()
        self.tiling_rules = {}

    def enter(self, **kwargs):
        """Create pygame_gui elements when the state is entered."""
        self._rebuild_ui()

    def _rebuild_ui(self):
        # Clean up old elements if any
        for element in self.ui_elements:
            element.kill()
        self.ui_elements.clear()

        w, h = self.renderer.screen.get_size()
        
        # Title
        title = UILabel(
            relative_rect=pygame.Rect((w // 2 - 200, 20), (400, 50)),
            text="=== ADVANCED MAP EDITOR ===",
            manager=self.ui_manager
        )
        self.ui_elements.append(title)

        menu_options = [
            ("New Map", "new"),
            ("Load Map", "load"),
            ("Define Custom Tiles", "tiles"),
            ("Macro Manager", "macros"),
            ("Edit Controls", "controls"),
            ("Auto-Tiling Manager", "autotile"),
            ("Quit", "quit")
        ]

        # Create buttons
        btn_w, btn_h = 300, 40
        start_y = 100
        for i, (label, action_id) in enumerate(menu_options):
            btn = UIButton(
                relative_rect=pygame.Rect((w // 2 - btn_w // 2, start_y + i * (btn_h + 10)), (btn_w, btn_h)),
                text=label,
                manager=self.ui_manager,
                tool_tip_text=f"Click to start {label.lower()}",
                object_id=f"#{action_id}"
            )
            self.ui_elements.append(btn)

    def exit(self):
        """Clean up UI elements when leaving the state."""
        for element in self.ui_elements:
            element.kill()
        self.ui_elements.clear()

    def draw(self, surface):
        # We only clear the screen; pygame_gui handles drawing the widgets
        self.renderer.clear()

    def handle_event(self, event):
        vw = self.renderer.width // self.renderer.tile_size
        vh = (self.renderer.height - 120) // self.renderer.tile_size
        flow = self.manager.flow

        if event.type == pygame.VIDEORESIZE:
            self.renderer.update_dimensions()
            self._rebuild_ui()

        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            # Check by button text for maximum reliability in this setup
            text = event.ui_element.text
            
            if text == "New Map":
                flow.push_new_map_wizard(vw, vh, self.start_editor)
            elif text == "Load Map":
                flow.push_load_map_wizard(vw, vh, self.start_editor)
            elif text == "Define Custom Tiles":
                flow.push_tile_registry()
            elif text == "Macro Manager":
                from core import ToolState
                ts = ToolState(macros=self.macros)
                flow.push_macro_manager(ts)
            elif text == "Edit Controls":
                flow.push_control_settings(self.bindings)
            elif text == "Auto-Tiling Manager":
                from core import ToolState
                ts = ToolState(tiling_rules=self.tiling_rules)
                flow.push_autotile_manager(ts)
            elif text == "Quit":
                self.manager.running = False

        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                self.manager.running = False

    def start_editor(self, map_obj):
        if map_obj is None:
            return
        
        vw = self.renderer.width // self.renderer.tile_size
        vh = (self.renderer.height - 120) // self.renderer.tile_size
        
        session = EditorSession(
            map_obj, 
            vw, 
            vh, 
            self.bindings, 
            macros=self.macros, 
            tiling_rules=self.tiling_rules
        )
        self.renderer.invalidate_cache()
        self.manager.flow.start_session(session=session)
