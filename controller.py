import pygame
import sys
from menu import build_key_map
from actions import get_action_dispatcher

class InputHandler:
    def __init__(self, session):
        self.session = session
        self.dispatcher = get_action_dispatcher()
        self.session.key_map = build_key_map(session.bindings)
        self.held_keys = set()

    def process_keyup(self, key):
        if key in self.held_keys:
            self.held_keys.remove(key)

    def check_held_keys(self):
        # Sync held_keys with actual hardware state to prevent stuck keys
        # especially when modal dialogs swallow KEYUP events
        keys_pressed = pygame.key.get_pressed()
        to_remove = []
        for key in self.held_keys:
            if key < len(keys_pressed) and not keys_pressed[key]:
                to_remove.append(key)
        
        for key in to_remove:
            self.held_keys.remove(key)

    def process_key(self, key, unicode_char, manager):
        is_repeat = key in self.held_keys
        self.held_keys.add(key)

        if key == pygame.K_ESCAPE:
            ts = self.session.tool_state
            if ts.start_point: ts.start_point = None
            elif self.session.selection_start: self.session.selection_start, self.session.selection_end = None, None
            elif ts.measure_start: ts.measure_start = None
            else: ts.mode = 'place'
            return

        # 1. Try modified key name (e.g., 'shift f2')
        mods = pygame.key.get_mods()
        key_parts = []
        if mods & pygame.KMOD_SHIFT: key_parts.append('shift')
        if mods & pygame.KMOD_CTRL: key_parts.append('ctrl')
        if mods & pygame.KMOD_ALT: key_parts.append('alt')
        
        base_key_name = pygame.key.name(key).lower()
        key_parts.append(base_key_name)
        full_key_name = " ".join(key_parts)
        
        actions = self.session.key_map.get(full_key_name, [])

        # 2. Try specific unicode character mapping (case-sensitive)
        if not actions and unicode_char and unicode_char in self.session.key_map:
            actions = self.session.key_map[unicode_char]
        
        # 3. Fallback to physical base key name
        if not actions:
            actions = self.session.key_map.get(base_key_name, [])

        for action in actions:
            # Prevent key repeat for place_tile unless in 'place' mode (painting)
            if is_repeat and action == 'place_tile' and self.session.tool_state.mode != 'place':
                continue
            self.dispatch(action, manager)

    def process_mouse(self, button, manager):
        # Check modifiers
        mods = pygame.key.get_mods()
        key_parts = []
        if mods & pygame.KMOD_SHIFT: key_parts.append('shift')
        if mods & pygame.KMOD_CTRL: key_parts.append('ctrl')
        if mods & pygame.KMOD_ALT: key_parts.append('alt')
        key_parts.append(f"mouse {button}")
        
        full_key_name = " ".join(key_parts)
        
        # Try with modifiers first
        actions = self.session.key_map.get(full_key_name, [])
        
        # Fallback to base button if no modified action found
        if not actions:
            actions = self.session.key_map.get(f"mouse {button}", [])
        
        for action in actions:
            self.dispatch(action, manager)

    def handle_mouse_hold(self, manager):
        # Support continuous painting (hold to paint) for mouse
        # Only applies to 'place_tile' in 'place' mode
        pressed = pygame.mouse.get_pressed()
        # pressed is (left, middle, right) which maps to buttons 1, 2, 3
        for i, is_pressed in enumerate(pressed):
            if is_pressed:
                button = i + 1
                key_name = f"mouse {button}"
                actions = self.session.key_map.get(key_name, [])
                for action in actions:
                    if action == 'place_tile' and self.session.tool_state.mode == 'place':
                         self.dispatch(action, manager)

    def dispatch(self, action, manager):
        if action in self.dispatcher:
            # Record action if recording is active, but don't record the toggle itself
            ts = self.session.tool_state
            if ts.recording and action != 'macro_record_toggle':
                ts.current_macro_actions.append(action)

            # Actions now expect (session, manager, action)
            self.dispatcher[action](self.session, manager, action)
