import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIScrollingContainer, UILabel, UIButton, UIPanel
from state_engine import State
from tiles import REGISTRY
from utils import parse_color_name, get_color_name
from menu.base import ConfirmationState, FormState
from menu.pickers import ColorPickerState

class TileRegistryState(State):
    def __init__(self, manager, context):
        super().__init__(manager)
        self.context = context
        self.all_tiles = []

        # UI Elements
        self.main_window = None
        self.list_container = None
        self.tile_rows = [] # list of (tile, panel_element)
        self.selected_tile_id = None

        self.buttons = {} # btn -> action

    def enter(self, **kwargs):
        self._build_main_ui()
        self.refresh_data()

    def exit(self):
        if self.main_window:
            self.main_window.kill()

    def _build_main_ui(self):
        w, h = self.manager.screen.get_size()
        
        self.main_window = UIWindow(
            rect=pygame.Rect(20, 20, w - 40, h - 40),
            manager=self.ui_manager,
            window_display_title="TILE REGISTRY",
            resizable=True
        )
        
        # Toolbar
        self.btn_add = UIButton(pygame.Rect(20, 20, 100, 30), "Add New", self.ui_manager, container=self.main_window)
        self.btn_edit = UIButton(pygame.Rect(130, 20, 100, 30), "Edit", self.ui_manager, container=self.main_window)
        self.btn_del = UIButton(pygame.Rect(240, 20, 100, 30), "Delete", self.ui_manager, container=self.main_window)
        self.btn_back = UIButton(pygame.Rect(w - 200, 20, 100, 30), "Back", self.ui_manager, container=self.main_window)
        
        self.buttons[self.btn_add] = 'add'
        self.buttons[self.btn_edit] = 'edit'
        self.buttons[self.btn_del] = 'delete'
        self.buttons[self.btn_back] = 'back'

        # List
        self.list_container = UIScrollingContainer(
            relative_rect=pygame.Rect(20, 60, w - 100, h - 150),
            manager=self.ui_manager,
            container=self.main_window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

    def refresh_data(self):
        self.all_tiles = REGISTRY.get_all()
        # Rebuild list
        self.list_container.clear() # Does clear work? No, need to kill children.
        # Ideally we shouldn't rebuild every time, but it's easier.
        # pygame_gui doesn't have clear(), so we iterate and kill.
        # Actually UIScrollingContainer doesn't expose children easily.
        # We can just kill the container and recreate it, or keep track of rows.
        
        # Let's recreate the container content
        # Note: killing container kills children? Yes.
        if self.list_container:
            self.list_container.kill()

        w, h = self.main_window.get_container().get_size()
        self.list_container = UIScrollingContainer(
            relative_rect=pygame.Rect(20, 60, w - 40, h - 80),
            manager=self.ui_manager,
            container=self.main_window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )
        
        self.tile_rows = []
        y = 0
        row_h = 40
        
        for tile in self.all_tiles:
            panel = UIPanel(
                relative_rect=pygame.Rect(0, y, w - 60, row_h),
                manager=self.ui_manager,
                container=self.list_container,
                layer_thickness=1
            )
            
            # Clickable overlay button (invisible or transparent)
            btn = UIButton(
                relative_rect=pygame.Rect(0, 0, w - 60, row_h),
                text="",
                manager=self.ui_manager,
                container=panel,
                object_id="#transparent_button" # Need theme to make transparent?
                # Alternatively just use the button AS the row.
            )
            # Default button style is opaque.
            # Let's just use labels and a button "Select" or make the whole row a button with text.
            # Button text: "[#] Name (Color)"
            
            btn.set_text(f"[{tile.char}] {tile.name} ({get_color_name(tile.color)})")

            if tile.id == self.selected_tile_id:
                btn.select()

            self.tile_rows.append((tile, btn))
            y += row_h

        self.list_container.set_scrollable_area_dimensions((w - 60, y))

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element in self.buttons:
                action = self.buttons[event.ui_element]
                if action == 'add':
                    self._open_form(None)
                elif action == 'edit':
                    if self.selected_tile_id:
                        tile = REGISTRY.get(self.selected_tile_id)
                        self._open_form(tile)
                elif action == 'delete':
                    if self.selected_tile_id:
                        tile = REGISTRY.get(self.selected_tile_id)
                        self.manager.push(ConfirmationState(self.manager, self.context, f"Delete '{tile.name}'?", self._on_delete))
                elif action == 'back':
                    self.manager.pop()
            else:
                # Check rows
                for tile, btn in self.tile_rows:
                    if event.ui_element == btn:
                        self.selected_tile_id = tile.id
                        # Unselect others
                        for _, b in self.tile_rows: b.unselect()
                        btn.select()
                        break
        
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.main_window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def _on_delete(self, confirmed):
        if confirmed and self.selected_tile_id:
            REGISTRY.delete(self.selected_tile_id)
            self.selected_tile_id = None
            self.refresh_data()
            self.context.invalidate_cache()

    def _open_form(self, tile):
        # Use FormState
        is_edit = tile is not None

        fields = [
            ["Char", tile.char if is_edit else "?", "char"],
            ["Name", tile.name if is_edit else "New Tile", "name"],
            ["Color", get_color_name(tile.color) if is_edit else "white", "color"]
        ]

        def on_submit(res):
            if not res: return
            
            try:
                char = res['char']
                name = res['name']
                color_val = parse_color_name(res['color']) # This might fail if custom rgb not handled by utils

                if is_edit:
                    REGISTRY.update_tile(tile.id, name=name, color=color_val) # Update char not supported?
                    # Registry update_tile doesn't support changing char usually, but let's check.
                    # REGISTRY.update_tile implementation needs checking. Assuming name/color.
                    # If char changed, we might need to re-register.
                else:
                    REGISTRY.register(char, name, color=color_val)

                self.refresh_data()
                self.context.invalidate_cache()
            except Exception as e:
                print(e)

        self.manager.push(FormState(self.manager, self.context, "EDIT TILE" if is_edit else "NEW TILE", fields, on_submit))

    def draw(self, surface):
        pass
