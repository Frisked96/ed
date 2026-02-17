import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UISelectionList, UILabel, UITextEntryLine, UIButton, UITextBox, UIPanel
from pygame_gui.windows import UIConfirmationDialog, UIMessageWindow
from state_engine import State
from collections import Counter
from utils import get_key_name

def build_key_map(bindings):
    key_map = {}
    for action, key_val in bindings.items():
        if not key_val or key_val == 'None':
            continue
        
        if isinstance(key_val, list):
            keys = key_val
        else:
            keys = [key_val]

        for key_name in keys:
            if not key_name or key_name == 'None': continue

            if len(key_name) > 1:
                key_lookup = key_name.lower()
            else:
                key_lookup = key_name
            
            if key_lookup not in key_map:
                key_map[key_lookup] = []
            key_map[key_lookup].append(action)
    return key_map

def get_map_statistics(map_obj):
    return Counter(map_obj.data.flatten())

# Remove _render_menu_generic as we are using pygame_gui

class MenuState(State):
    def __init__(self, manager, context, title, options):
        """
        options: list of (label, callback) tuples.
        If callback is None, it's just a label or disabled item (though UISelectionList doesn't support disabled items well, we can ignore selection).
        """
        super().__init__(manager)
        self.context = context
        self.title = title
        self.options = options
        self.option_labels = [opt[0] for opt in options]
        self.window = None
        self.selection_list = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()

        # Calculate size based on content
        # Default size, maybe adjust based on option length
        menu_w = 400
        menu_h = min(h - 100, len(self.options) * 30 + 70)

        rect = pygame.Rect((w - menu_w) // 2, (h - menu_h) // 2, menu_w, menu_h)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title=self.title,
            object_id='#menu_window'
        )

        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(10, 10, menu_w - 50, menu_h - 60),
            item_list=self.option_labels,
            manager=self.ui_manager,
            container=self.window,
            object_id='#menu_list'
        )

    def exit(self):
        if self.window:
            self.window.kill()
            self.window = None

    def handle_event(self, event):
        if event.type == pygame_gui.UI_SELECTION_LIST_DOUBLE_CLICKED_SELECTION:
            if event.ui_element == self.selection_list:
                self._confirm_selection()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()
            elif event.key == pygame.K_RETURN:
                self._confirm_selection()

    def _confirm_selection(self):
        selected_item = self.selection_list.get_single_selection()
        if selected_item:
            # Find the index
            try:
                idx = self.option_labels.index(selected_item)
                callback = self.options[idx][1]
                if callback:
                    callback()
                # Note: We don't automatically pop here unless the callback does it,
                # but typically menu items trigger a new state or action.
                # If it's a "leaf" action, the callback should handle popping or not.
                # Many existing callbacks expect to pop themselves or push a new state.
            except ValueError:
                pass

    def draw(self, surface):
        # pygame_gui handles drawing
        pass

class TextInputState(State):
    def __init__(self, manager, context, prompt, callback, initial_text=""):
        super().__init__(manager)
        self.context = context
        self.prompt = prompt
        self.callback = callback
        self.initial_text = str(initial_text)
        self.window = None
        self.text_entry = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        box_w, box_h = 400, 150
        rect = pygame.Rect((w - box_w) // 2, (h - box_h) // 2, box_w, box_h)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title=self.prompt,
            object_id='#input_window'
        )
        
        self.text_entry = UITextEntryLine(
            relative_rect=pygame.Rect(20, 40, box_w - 70, 30),
            manager=self.ui_manager,
            container=self.window,
            initial_text=self.initial_text
        )
        self.text_entry.focus()
        pygame.key.start_text_input()

        btn_w = 100
        self.ok_btn = UIButton(
            relative_rect=pygame.Rect((box_w - 70)//2 - btn_w - 10, 90, btn_w, 30),
            text="OK",
            manager=self.ui_manager,
            container=self.window
        )
        self.cancel_btn = UIButton(
            relative_rect=pygame.Rect((box_w - 70)//2 + 10, 90, btn_w, 30),
            text="Cancel",
            manager=self.ui_manager,
            container=self.window
        )

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_TEXT_ENTRY_FINISHED:
            if event.ui_element == self.text_entry:
                print(f"DEBUG: Text entry finished: {event.text}")
                self.manager.pop()
                self.callback(event.text)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.ok_btn:
                print(f"DEBUG: OK button pressed. Text: {self.text_entry.get_text()}")
                self.manager.pop()
                self.callback(self.text_entry.get_text())
            elif event.ui_element == self.cancel_btn:
                print("DEBUG: Cancel button pressed.")
                self.manager.pop()
                self.callback(None)
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                print("DEBUG: Window closed in TextInputState")
                self.manager.pop()
                self.callback(None)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                print("DEBUG: ESC pressed in TextInputState")
                self.manager.pop()
                self.callback(None)

    def draw(self, surface):
        pass

class ConfirmationState(State):
    def __init__(self, manager, context, prompt, callback):
        super().__init__(manager)
        self.context = context
        self.prompt = prompt
        self.callback = callback
        self.dialog = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        rect = pygame.Rect((w - 400) // 2, (h - 200) // 2, 400, 200)
        
        self.dialog = UIConfirmationDialog(
            rect=rect,
            manager=self.ui_manager,
            action_long_desc=self.prompt,
            window_title="Confirm",
            blocking=True
        )

    def exit(self):
        if self.dialog:
            self.dialog.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_CONFIRMATION_DIALOG_CONFIRMED:
            if event.ui_element == self.dialog:
                self.manager.pop()
                self.callback(True)
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.dialog:
                self.manager.pop()
                self.callback(False)

    def draw(self, surface):
        pass

class MessageState(State):
    def __init__(self, manager, context, text, callback=None):
        super().__init__(manager)
        self.context = context
        self.text = text
        self.callback = callback
        self.window = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        rect = pygame.Rect((w - 400) // 2, (h - 200) // 2, 400, 200)

        self.window = UIMessageWindow(
            rect=rect,
            manager=self.ui_manager,
            html_message=self.text,
            window_title="Message"
        )

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
                if self.callback:
                    self.callback()

    def draw(self, surface):
        pass

class HelpState(State):
    def __init__(self, manager, context, bindings):
        super().__init__(manager)
        self.context = context
        self.bindings = bindings
        self.window = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        rect = pygame.Rect(50, 50, w - 100, h - 100)

        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title="Help (Press ESC to close)",
            resizable=True
        )

        text = self._generate_help_html()
        UITextBox(
            relative_rect=pygame.Rect(0, 0, rect.width - 30, rect.height - 60),
            html_text=text,
            manager=self.ui_manager,
            container=self.window,
            anchors={'top': 'top', 'bottom': 'bottom', 'left': 'left', 'right': 'right'}
        )

    def _generate_help_html(self):
        b = self.bindings
        sections = [
            ("MOVEMENT", [
                f"View: {get_key_name(b.get('move_view_up'))}/{get_key_name(b.get('move_view_down'))}/{get_key_name(b.get('move_view_left'))}/{get_key_name(b.get('move_view_right'))}",
                f"Cursor: Arrow Keys"
            ]),
            ("DRAWING TOOLS", [
                f"<b>{get_key_name(b.get('place_tile'))}</b>: Place tile | <b>{get_key_name(b.get('cycle_tile'))}</b>: Cycle tiles | <b>{get_key_name(b.get('pick_tile'))}</b>: Pick tile",
                f"<b>{get_key_name(b.get('flood_fill'))}</b>: Flood fill | <b>{get_key_name(b.get('line_tool'))}</b>: Line | <b>{get_key_name(b.get('rect_tool'))}</b>: Rectangle",
                f"<b>{get_key_name(b.get('circle_tool'))}</b>: Circle | <b>{get_key_name(b.get('pattern_tool'))}</b>: Pattern mode",
                f"Brush: <b>{get_key_name(b.get('decrease_brush'))}/{get_key_name(b.get('increase_brush'))}</b> (Size)"
            ]),
             ("SELECTION & CLIPBOARD", [
                f"<b>{get_key_name(b.get('select_start'))}</b>: Start/End selection | <b>{get_key_name(b.get('clear_selection'))}</b>: Clear",
                f"<b>{get_key_name(b.get('copy_selection'))}</b>: Copy | <b>{get_key_name(b.get('paste_selection'))}</b>: Paste",
                f"<b>{get_key_name(b.get('rotate_selection'))}</b>: Rotate Sel | <b>{get_key_name(b.get('flip_h'))}</b>: Flip H Sel | <b>{get_key_name(b.get('flip_v'))}</b>: Flip V Sel",
                f"<b>{get_key_name(b.get('clear_area'))}</b>: Clear selected area"
            ]),
             ("EDIT OPERATIONS", [
                f"<b>{get_key_name(b.get('undo'))}</b>: Undo | <b>{get_key_name(b.get('redo'))}</b>: Redo",
                f"<b>{get_key_name(b.get('replace_all'))}</b>: Replace all tiles | <b>{get_key_name(b.get('statistics'))}</b>: Show statistics"
            ]),
        ]

        html = "<font face='fira_code' size=4>"
        for title, lines in sections:
            html += f"<br><b><font color='#00FFFF'>{title}</font></b><br>"
            for line in lines:
                html += line + "<br>"
        html += "</font>"
        return html

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                self.manager.pop()
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()

    def draw(self, surface):
        pass

class FormState(State):
    def __init__(self, manager, context, title, fields, callback):
        super().__init__(manager)
        self.context = context
        self.title = title
        self.fields_data = fields # [[label, value, key], ...]
        self.callback = callback
        self.window = None
        self.entry_map = {}

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        
        # Calculate height
        form_h = len(self.fields_data) * 40 + 100
        form_w = 400
        rect = pygame.Rect((w - form_w) // 2, (h - form_h) // 2, form_w, form_h)
        
        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title=self.title
        )
        
        y = 20
        first_entry = None
        for label, val, key in self.fields_data:
            UILabel(
                relative_rect=pygame.Rect(20, y, 150, 30),
                text=label + ":",
                manager=self.ui_manager,
                container=self.window
            )

            entry = UITextEntryLine(
                relative_rect=pygame.Rect(180, y, 180, 30),
                manager=self.ui_manager,
                container=self.window,
                initial_text=str(val)
            )
            self.entry_map[key] = entry
            if not first_entry:
                first_entry = entry
            y += 40

        if first_entry:
            first_entry.focus()
        pygame.key.start_text_input()

        self.apply_btn = UIButton(
            relative_rect=pygame.Rect(80, y + 10, 100, 30),
            text="Apply",
            manager=self.ui_manager,
            container=self.window
        )
        
        self.cancel_btn = UIButton(
            relative_rect=pygame.Rect(220, y + 10, 100, 30),
            text="Cancel",
            manager=self.ui_manager,
            container=self.window
        )

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.apply_btn:
                res = {k: entry.get_text() for k, entry in self.entry_map.items()}
                self.manager.pop()
                self.callback(res)
            elif event.ui_element == self.cancel_btn:
                self.manager.pop()
                self.callback(None)
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
                self.callback(None)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()
                self.callback(None)

    def draw(self, surface):
        pass

class ChoiceSelectorState(State):
    def __init__(self, manager, context, title, choices, callback):
        super().__init__(manager)
        self.context = context
        self.title = title
        self.choices = choices
        self.callback = callback
        self.window = None

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        menu_w = 300
        menu_h = min(400, len(self.choices) * 35 + 80)
        
        self.window = UIWindow(
            rect=pygame.Rect((w - menu_w) // 2, (h - menu_h) // 2, menu_w, menu_h),
            manager=self.ui_manager,
            window_display_title=self.title
        )
        
        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(10, 10, menu_w - 50, menu_h - 100),
            item_list=self.choices,
            manager=self.ui_manager,
            container=self.window
        )
        
        self.cancel_btn = UIButton(
            relative_rect=pygame.Rect(10, menu_h - 80, menu_w - 50, 30),
            text="Cancel",
            manager=self.ui_manager,
            container=self.window
        )

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.selection_list:
                item = self.selection_list.get_single_selection()
                self.manager.pop()
                self.callback(item)
        elif event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == self.cancel_btn:
                self.manager.pop()
                self.callback(None)
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
                self.callback(None)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()
                self.callback(None)

    def draw(self, surface):
        pass

class ContextMenuState(State):
    def __init__(self, manager, context, options, screen_pos):
        super().__init__(manager)
        self.context = context
        self.options = options
        self.screen_pos = screen_pos
        self.option_labels = [opt[0] for opt in options]
        self.window = None
        self.selection_list = None

    def enter(self, **kwargs):
        x, y = self.screen_pos
        w, h = 200, min(300, len(self.options) * 30 + 20)
        
        # Adjust if off-screen
        sw, sh = self.manager.screen.get_size()
        if x + w > sw: x = sw - w
        if y + h > sh: y = sh - h
        
        self.window = UIPanel(
            relative_rect=pygame.Rect(x, y, w, h),
            manager=self.ui_manager
        )
        
        self.selection_list = UISelectionList(
            relative_rect=pygame.Rect(0, 0, w, h),
            item_list=self.option_labels,
            manager=self.ui_manager,
            container=self.window
        )

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_SELECTION_LIST_NEW_SELECTION:
            if event.ui_element == self.selection_list:
                item = self.selection_list.get_single_selection()
                try:
                    idx = self.option_labels.index(item)
                    cb = self.options[idx][1]
                    self.manager.pop()
                    if cb: cb()
                except ValueError:
                    self.manager.pop()
        elif event.type == pygame.MOUSEBUTTONDOWN:
            # Click outside closes menu
            if not self.window.rect.collidepoint(event.pos):
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def draw(self, surface):
        pass
