from .utils import show_message

def handle_macro_toggle(session, manager, action=None):
    ts = session.tool_state
    if ts.recording:
        ts.recording = False
        def on_name(name):
            if name:
                ts.macros[name] = list(ts.current_macro_actions)
                show_message(manager, f"Macro '{name}' saved", notify=True)
        manager.flow.push_text_input("Enter name for macro: ", on_name)
    else:
        ts.recording = True
        ts.current_macro_actions = []
        show_message(manager, "Recording Macro...", notify=True)

def handle_macro_play(session, manager, action=None):
    ts = session.tool_state
    def on_play(name):
        if name in ts.macros:
            session.action_queue.extendleft(reversed(ts.macros[name]))
    manager.flow.push_text_input("Enter macro name to play: ", on_play)
