import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UISelectionList, UIButton, UIPanel, UILabel, UITextEntryLine, UIScrollingContainer
from state_engine import State
from utils import get_all_colors
from tiles import REGISTRY

class ColorPickerMachine:
    # We don't really need a state machine here anymore with the new UI flow
    pass

class ColorPickerState(State):
    def __init__(self, manager, context, callback):
        super().__init__(manager)
        self.context = context
        self.callback = callback
        self.colors = get_all_colors()
        self.names = sorted(list(self.colors.keys()))
        self.options = self.names + ["Custom (Name or R,G,B)"]
        self.window = None
        self.selection_list = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        rect = pygame.Rect((w - 400) // 2, (h - 500) // 2, 400, 500)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="SELECT COLOR"
        )
        
        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(10, 10, 380, 430),
            item_list=[opt.capitalize() if i < len(self.names) else opt for i, opt in enumerate(self.options)],
            manager=self.ui_manager,
            container=self.window
        )

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_SELECTION_LIST_DOUBLE_CLICKED_SELECTION:
            if event.ui_element == self.selection_list:
                self._confirm()
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()
            elif event.key == pygame.K_RETURN:
                self._confirm()

    def _confirm(self):
        selected_item = self.selection_list.get_single_selection()
        if not selected_item: return

        # Check if "Custom"
        if "Custom" in selected_item:
            from menu.base import TextInputState
            def on_custom(val):
                if val:
                    self.callback(val)
                # We pop ourselves after custom input is done (or cancelled)
                # Actually, on_custom is called after TextInputState pops.
                # So we are back here. If val is valid, we invoke callback and pop.
                if val:
                    self.manager.pop()

            # We push TextInputState on top.
            self.manager.push(TextInputState(self.manager, self.context, "Color Name or R,G,B: ", on_custom))
        else:
            # Map back to original name (lowercase key)
            key = selected_item.lower()
            # Handle case mismatch if capitalized
            if key not in self.colors:
                # Find matching key
                for k in self.colors:
                    if k.lower() == key:
                        key = k
                        break

            self.callback(key)
            self.manager.pop()

    def draw(self, surface):
        pass

class TilePickerState(State):
    def __init__(self, manager, context, callback):
        super().__init__(manager)
        self.context = context
        self.callback = callback
        self.all_tiles = REGISTRY.get_all()
        self.window = None
        self.buttons = {} # ui_element -> tile_id

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        win_w, win_h = 600, 500
        rect = pygame.Rect((w - win_w) // 2, (h - win_h) // 2, win_w, win_h)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="SELECT TILE"
        )

        container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, win_w - 30, win_h - 40),
            manager=self.ui_manager,
            container=self.window
        )
        
        # Grid layout
        cols = (win_w - 60) // 50
        tile_size = 40
        padding = 10

        scroll_h = 0
        
        for i, tile in enumerate(self.all_tiles):
            c = i % cols
            r = i // cols

            px = padding + c * (tile_size + padding)
            py = padding + r * (tile_size + padding)
            
            btn = UIButton(
                relative_rect=pygame.Rect(px, py, tile_size, tile_size),
                text=tile.char,
                manager=self.ui_manager,
                container=container
            )
            # We can't easily set button color, so we rely on text char
            # Maybe tooltip for full name
            btn.tool_tip_text = f"{tile.name} ({tile.id})"
            
            self.buttons[btn] = tile.id
            scroll_h = max(scroll_h, py + tile_size + padding)

        container.set_scrollable_area_dimensions((win_w - 50, scroll_h))

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element in self.buttons:
                tid = self.buttons[event.ui_element]
                self.manager.pop()
                self.callback(tid)
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def draw(self, surface):
        pass

class MultiTilePickerState(State):
    def __init__(self, manager, context, callback, initial_selection=None):
        super().__init__(manager)
        self.context = context
        self.callback = callback
        self.all_tiles = REGISTRY.get_all()
        self.selected_indices = set()
        if initial_selection:
            initial_ids = set(initial_selection)
            for idx, tile in enumerate(self.all_tiles):
                if tile.id in initial_ids:
                    self.selected_indices.add(idx)
                    
        self.window = None
        self.buttons = {} # ui_element -> index
        self.confirm_btn = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        win_w, win_h = 600, 500
        rect = pygame.Rect((w - win_w) // 2, (h - win_h) // 2, win_w, win_h)
        
        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="SELECT TILES (Multi)"
        )
        
        self.confirm_btn = UIButton(
            relative_rect=pygame.Rect((win_w - 120)//2, win_h - 70, 120, 30),
            text="Confirm",
            manager=self.ui_manager,
            container=self.window
        )

        container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, win_w - 30, win_h - 80),
            manager=self.ui_manager,
            container=self.window
        )

        cols = (win_w - 60) // 50
        tile_size = 40
        padding = 10
        scroll_h = 0
        
        for i, tile in enumerate(self.all_tiles):
            c = i % cols
            r = i // cols

            px = padding + c * (tile_size + padding)
            py = padding + r * (tile_size + padding)
            
            # Determine initial state
            is_selected = i in self.selected_indices
            text = f"[{tile.char}]" if is_selected else tile.char
            
            btn = UIButton(
                relative_rect=pygame.Rect(px, py, tile_size, tile_size),
                text=text,
                manager=self.ui_manager,
                container=container
            )
            btn.tool_tip_text = f"{tile.name} ({tile.id})"
            if is_selected:
                btn.select() # Visual indication if theme supports it

            self.buttons[btn] = i
            scroll_h = max(scroll_h, py + tile_size + padding)

        container.set_scrollable_area_dimensions((win_w - 50, scroll_h))

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.confirm_btn:
                selected_ids = [self.all_tiles[i].id for i in self.selected_indices]
                self.manager.pop()
                self.callback(selected_ids)
            elif event.ui_element in self.buttons:
                idx = self.buttons[event.ui_element]
                if idx in self.selected_indices:
                    self.selected_indices.remove(idx)
                    event.ui_element.set_text(self.all_tiles[idx].char)
                    event.ui_element.unselect()
                else:
                    self.selected_indices.add(idx)
                    event.ui_element.set_text(f"[{self.all_tiles[idx].char}]")
                    event.ui_element.select()

        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def draw(self, surface):
        pass
