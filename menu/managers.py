import pygame
from statemachine import StateMachine, State as SMState
from state_engine import State
from menu.base import _render_menu_generic, TextInputState, ConfirmationState

class MacroManagerState(State):
    def __init__(self, manager, context, tool_state):
        super().__init__(manager)
        self.context = context
        self.tool_state = tool_state
        self.selected_idx = 0

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        macros = list(self.tool_state.macros.keys())

        if event.key == pygame.K_UP:
            self.selected_idx = max(0, self.selected_idx - 1)
        elif event.key == pygame.K_DOWN:
            self.selected_idx = min(len(macros) - 1, self.selected_idx + 1)
        elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
            self.manager.pop()
        elif event.key == pygame.K_a:
            def on_name(name):
                if name:
                    def on_actions(actions):
                        self.tool_state.macros[name] = actions.split(',') if actions else []
                    self.manager.push(TextInputState(self.manager, self.context, "Actions (comma-separated chars): ", on_actions))
            self.manager.push(TextInputState(self.manager, self.context, "Macro Name: ", on_name))
        elif event.key == pygame.K_r and macros:
            name = macros[self.selected_idx]
            def on_confirm(confirmed):
                if confirmed:
                    del self.tool_state.macros[name]
                    self.selected_idx = max(0, self.selected_idx - 1)
            self.manager.push(ConfirmationState(self.manager, self.context, f"Delete macro '{name}'?", on_confirm))

    def draw(self, surface):
        macros = list(self.tool_state.macros.keys())
        lines = []
        for m in macros:
            count = len(self.tool_state.macros[m])
            lines.append(f"{m} ({count} steps)")
        
        _render_menu_generic(self.context, "MACRO MANAGER: [A] Add | [R] Remove", lines, self.selected_idx)

class AutoTilingMachine(StateMachine):
    browsing_bases = SMState(initial=True)
    editing_rules = SMState()
    
    start_edit = browsing_bases.to(editing_rules)
    finish_edit = editing_rules.to(browsing_bases)

class AutoTilingManagerState(State):
    def __init__(self, manager, context, tool_state):
        super().__init__(manager)
        self.context = context
        self.tool_state = tool_state
        self.machine = AutoTilingMachine()
        self.base_idx = 0
        self.rule_idx = 0
        self.bases = []

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        self.bases = list(self.tool_state.tiling_rules.keys())

        if self.machine.current_state == AutoTilingMachine.browsing_bases:
            self._handle_browsing(event)
        else:
            self._handle_editing(event)

    def _handle_browsing(self, event):
        if event.key == pygame.K_UP:
            self.base_idx = max(0, self.base_idx - 1)
        elif event.key == pygame.K_DOWN:
            self.base_idx = min(len(self.bases) - 1, self.base_idx + 1)
        elif event.key == pygame.K_q or event.key == pygame.K_ESCAPE:
            self.manager.pop()
        elif event.key == pygame.K_a:
            def on_base(base):
                if base and len(base) == 1:
                    if base not in self.tool_state.tiling_rules:
                        self.tool_state.tiling_rules[base] = {}
            self.manager.push(TextInputState(self.manager, self.context, "Base Character: ", on_base))
        elif event.key == pygame.K_r and self.bases:
            base = self.bases[self.base_idx]
            def on_confirm(confirmed):
                if confirmed:
                    del self.tool_state.tiling_rules[base]
                    self.base_idx = max(0, self.base_idx - 1)
            self.manager.push(ConfirmationState(self.manager, self.context, f"Delete rules for '{base}'?", on_confirm))
        elif event.key == pygame.K_e and self.bases:
            self.rule_idx = 0
            self.machine.start_edit()

    def _handle_editing(self, event):
        if event.key == pygame.K_ESCAPE:
            self.machine.finish_edit()
        elif event.key == pygame.K_UP:
            self.rule_idx = max(0, self.rule_idx - 1)
        elif event.key == pygame.K_DOWN:
            self.rule_idx = min(14, self.rule_idx + 1)
        elif event.key == pygame.K_RETURN:
            base = self.bases[self.base_idx]
            mask = self.rule_idx + 1
            def on_variant(val):
                if val:
                    self.tool_state.tiling_rules[base][mask] = val[0]
            self.manager.push(TextInputState(self.manager, self.context, f"Variant char for mask {mask}: ", on_variant))

    def draw(self, surface):
        if self.machine.current_state == AutoTilingMachine.browsing_bases:
            self.bases = list(self.tool_state.tiling_rules.keys())
            lines = [f"Base '{b}': {len(self.tool_state.tiling_rules[b])} rules" for b in self.bases]
            _render_menu_generic(self.context, "AUTO-TILING: [A] Add | [E] Edit | [R] Remove", lines, self.base_idx)
        else:
            base = self.bases[self.base_idx]
            rlines = []
            for m in range(1, 16):
                binary = bin(m)[2:].zfill(4)
                curr = self.tool_state.tiling_rules[base].get(m, "")
                rlines.append(f"Mask {m:2} ({binary}): {curr}")
            _render_menu_generic(self.context, f"RULES FOR '{base}'", rlines, self.rule_idx)
