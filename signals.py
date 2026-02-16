from blinker import signal

# Define core signals for the application
# These can be imported and connected to by other modules
on_map_saved = signal('map_saved')
on_map_loaded = signal('map_loaded')
on_tool_changed = signal('tool_changed')
on_tile_placed = signal('tile_placed')
on_selection_changed = signal('selection_changed')
on_generation_complete = signal('generation_complete')
on_app_exit = signal('app_exit')
