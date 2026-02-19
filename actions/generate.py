import random
import numpy as np
from menu import menu_random_generation, menu_perlin_generation, menu_voronoi_generation
from .utils import check_autosave

def handle_generation(session, manager, action=None):
    session.map_obj.push_undo()
    success = False
    z = session.active_z_level
    if action == 'random_gen': success = menu_random_generation(manager, session.map_obj, session.tool_state.seed, z=z)
    elif action == 'perlin_noise': success = menu_perlin_generation(manager, session.map_obj, session.tool_state.seed, z=z)
    elif action == 'voronoi': success = menu_voronoi_generation(manager, session.map_obj, session.tool_state.seed, z=z)
    if success:
        session.tool_state.edits_since_save += 1
        check_autosave(session, manager)

def handle_set_seed(session, manager, action=None):
    def on_seed(inp):
        if inp:
            if inp.lower() == 'random':
                session.tool_state.seed = None
            else:
                try: session.tool_state.seed = int(inp)
                except: pass

            random.seed(session.tool_state.seed)
            np.random.seed(session.tool_state.seed)
    prompt = f"New seed (current: {session.tool_state.seed if session.tool_state.seed is not None else 'random'}): "
    manager.flow.push_text_input(prompt, on_seed)
