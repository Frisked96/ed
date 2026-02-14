import pygame
import sys
from menus import build_key_map
from actions import get_action_dispatcher

class InputHandler:
    def __init__(self, session):
        self.session = session
        self.dispatcher = get_action_dispatcher()
        self.session.key_map = build_key_map(session.bindings)

    def process_key(self, key, unicode_char, renderer):
        if key == pygame.K_ESCAPE:
            ts = self.session.tool_state
            if ts.start_point: ts.start_point = None
            elif self.session.selection_start: self.session.selection_start, self.session.selection_end = None, None
            elif ts.measure_start: ts.measure_start = None
            else: ts.mode = 'place'
            return

        # 1. Try specific unicode character mapping first (case-sensitive)
        actions = []
        if unicode_char and unicode_char in self.session.key_map:
            actions = self.session.key_map[unicode_char]
        
        # 2. Fallback to physical key name if no specific unicode mapping found
        if not actions:
            key_name = pygame.key.name(key).lower()
            actions = self.session.key_map.get(key_name, [])

        for action in actions:
            self.dispatch(action, renderer)

    def dispatch(self, action, context):
        if action in self.dispatcher:
            # Record action if recording is active, but don't record the toggle itself
            ts = self.session.tool_state
            if ts.recording and action != 'macro_record_toggle':
                ts.current_macro_actions.append(action)

            # Note: Actions currently expect (session, context, action)
            # where context was the old PygameContext. Renderer now acts as context.
            self.dispatcher[action](self.session, context, action)
