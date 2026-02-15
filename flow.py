from statemachine import StateMachine, State
import pygame

class AppFlow(StateMachine):
    """
    Centralized state controller for the application.
    All transitions between high-level states (Menu, Editor) 
    and modal operations happen here.
    """
    # High-level states
    main_menu = State(initial=True)
    editor = State()

    # Transitions
    start_session = main_menu.to(editor)
    exit_to_menu = editor.to(main_menu)

    def __init__(self, manager, renderer):
        self.manager = manager
        self.renderer = renderer
        super().__init__()

    # --- High-Level Transitions ---

    def on_enter_main_menu(self):
        from menu_state import MainMenuState
        # Using change_state ensures the stack is cleared and UI is reset
        self.manager.change_state(MainMenuState(self.manager, self.renderer))

    def on_enter_editor(self, session):
        from editor_state import EditorState
        # Clear stack and enter editor
        self.manager.change_state(EditorState(self.manager, session, self.renderer))

    # --- Modal & Sub-State Navigation ---
    # These use 'push' to keep the current state underneath

    def push_new_map_wizard(self, vw, vh, callback):
        from menu import NewMapState
        self.manager.push(NewMapState(self.manager, self.renderer, vw, vh, callback))

    def push_load_map_wizard(self, vw, vh, callback):
        from menu import LoadMapState
        self.manager.push(LoadMapState(self.manager, self.renderer, vw, vh, callback))

    def push_tile_registry(self):
        from menu import TileRegistryState
        self.manager.push(TileRegistryState(self.manager, self.renderer))

    def push_control_settings(self, bindings):
        from menu import ControlSettingsState
        self.manager.push(ControlSettingsState(self.manager, self.renderer, bindings))

    def push_macro_manager(self, tool_state):
        from menu import MacroManagerState
        self.manager.push(MacroManagerState(self.manager, self.renderer, tool_state))

    def push_autotile_manager(self, tool_state):
        from menu import AutoTilingManagerState
        self.manager.push(AutoTilingManagerState(self.manager, self.renderer, tool_state))

    def push_confirmation(self, prompt, callback):
        from menu import ConfirmationState
        self.manager.push(ConfirmationState(self.manager, self.renderer, prompt, callback))

    def push_message(self, text, callback=None):
        from menu import MessageState
        self.manager.push(MessageState(self.manager, self.renderer, text, callback))

    def push_text_input(self, prompt, callback, initial=""):
        from menu import TextInputState
        self.manager.push(TextInputState(self.manager, self.renderer, prompt, callback, initial))

    def push_help(self, bindings):
        from menu import HelpState
        self.manager.push(HelpState(self.manager, self.renderer, bindings))

    def push_pause_menu(self, callback):
        from menu import menu_editor_pause
        # menu_editor_pause internally pushes EditorPauseState
        menu_editor_pause(self.renderer, callback)

    def push_tile_picker(self, callback):
        from menu.pickers import TilePickerState
        self.manager.push(TilePickerState(self.manager, self.renderer, callback))

    def push_advanced_gen(self, session):
        from menu.generation import AdvancedGenerationState
        self.manager.push(AdvancedGenerationState(self.manager, self.renderer, session))

    def push_export_wizard(self, map_obj):
        from menu import ExportMapState
        self.manager.push(ExportMapState(self.manager, self.renderer, map_obj))

    def push_resize_wizard(self, map_obj, vw, vh, callback):
        from menu import menu_resize_map
        menu_resize_map(self.renderer, map_obj, vw, vh, callback)

    def push_form(self, title, fields, callback):
        from menu import FormState
        self.manager.push(FormState(self.manager, self.renderer, title, fields, callback))
