import time
from map_io import autosave_map

def show_message(manager, text, notify=False):
    """
    Displays a message to the user, either via a notification (toast) or a modal dialog.
    """
    if notify:
        manager.notify(text)
        return
    manager.flow.push_message(text)

def check_autosave(session, manager):
    """
    Checks if an autosave is triggered based on the session state and settings.
    """
    ts = session.tool_state
    if not ts.autosave_enabled: return

    do_save = False
    if ts.autosave_mode == 'edits':
        if ts.edits_since_save >= ts.autosave_edits_threshold:
            do_save = True
    elif ts.autosave_mode == 'time':
        if time.time() - ts.last_autosave_time >= ts.autosave_interval * 60:
            do_save = True

    if do_save:
        if autosave_map(session.map_obj, ts.autosave_filename):
            ts.edits_since_save = 0
            ts.last_autosave_time = time.time()
            show_message(manager, f"Autosaved to {ts.autosave_filename}", notify=True)
