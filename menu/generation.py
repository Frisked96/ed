from tiles import REGISTRY
from generation import (
    cellular_automata_cave, perlin_noise_generation, voronoi_generation,
    apply_cellular_automata_region, apply_weighted_noise_region, apply_shuffle_region
)
from menu.base import FormState, MessageState, State, MenuState
from menu.pickers import TilePickerState, MultiTilePickerState
import pygame
from core import EditorSession

# --- Simple Menu Helpers (unchanged) ---

def menu_random_generation(context, map_obj, seed=None):
    fields = [
        ["Seed", str(seed) if seed is not None else "random", "seed"],
        ["Iterations (3-10)", "5", "iters"],
        ["Wall Char", "#", "wall"],
        ["Floor Char", ".", "floor"]
    ]
    
    def on_submit(res):
        if not res: return
        try:
            gen_seed = int(res["seed"]) if res["seed"] != "random" else None
            iterations = max(3, min(10, int(res["iters"])))
            wall_id = REGISTRY.get_by_char(res["wall"][0])
            floor_id = REGISTRY.get_by_char(res["floor"][0])

            final_seed = cellular_automata_cave(map_obj, iterations, wall_id, floor_id, gen_seed)
            if gen_seed is None:
                context.manager.push(MessageState(context.manager, context, f"Generated with seed: {final_seed}"))
            context.invalidate_cache()
        except Exception as e:
            print(e)

    context.manager.push(FormState(context.manager, context, "CAVE GENERATION SETTINGS", fields, on_submit))
    return True

def menu_perlin_generation(context, map_obj, seed=None):
    fields = [
        ["Seed", str(seed) if seed is not None else "random", "seed"],
        ["Scale", "10.0", "scale"],
        ["Octaves", "4", "octaves"],
        ["Persistence", "0.5", "persistence"]
    ]
    
    def on_submit(res):
        if not res: return
        try:
            gen_seed = int(res["seed"]) if res["seed"] != "random" else None
            scale = float(res["scale"])
            octaves = int(res["octaves"])
            persistence = float(res["persistence"])
            tile_ids = [t.id for t in REGISTRY.get_all()]

            final_seed = perlin_noise_generation(map_obj, tile_ids, scale, octaves, persistence, gen_seed)
            if gen_seed is None:
                context.manager.push(MessageState(context.manager, context, f"Generated with seed: {final_seed}"))
            context.invalidate_cache()
        except Exception as e:
            print(e)

    context.manager.push(FormState(context.manager, context, "PERLIN NOISE SETTINGS", fields, on_submit))
    return True

def menu_voronoi_generation(context, map_obj, seed=None):
    fields = [
        ["Seed", str(seed) if seed is not None else "random", "seed"],
        ["Points", "20", "points"]
    ]
    
    def on_submit(res):
        if not res: return
        try:
            gen_seed = int(res["seed"]) if res["seed"] != "random" else None
            num_points = int(res["points"])
            tile_ids = [t.id for t in REGISTRY.get_all()]

            final_seed = voronoi_generation(map_obj, tile_ids, num_points, gen_seed)
            if gen_seed is None:
                context.manager.push(MessageState(context.manager, context, f"Generated with seed: {final_seed}"))
            context.invalidate_cache()
        except Exception as e:
            print(e)

    context.manager.push(FormState(context.manager, context, "VORONOI SETTINGS", fields, on_submit))
    return True


# --- Advanced Generation Menu ---

class AdvancedGenerationState(MenuState):
    def __init__(self, manager, context, session: EditorSession):
        options = [
            ("Cellular Automata", self._open_ca),
            ("Weighted Noise", self._open_noise),
            ("Shuffle Selection", self._open_shuffle),
        ]
        super().__init__(manager, context, "ADVANCED GENERATION", options)
        self.session = session

    def _open_ca(self):
        self.manager.push(CAGenState(self.manager, self.context, self.session))

    def _open_noise(self):
        self.manager.push(NoiseGenState(self.manager, self.context, self.session))

    def _open_shuffle(self):
        self.manager.push(ShuffleGenState(self.manager, self.context, self.session))

class BaseGenConfigState(State):
    def __init__(self, manager, context, session, title):
        super().__init__(manager)
        self.context = context
        self.session = session
        self.title = title
        self.options = [] # list of (label, getter, action/setter)
        self.selected_idx = 0
        
    def _get_tile_label(self, tid):
        t = REGISTRY.get(tid)
        return f"{t.char} ({tid})" if t else f"Void ({tid})"

    def _get_selection_range(self):
        map_w, map_h = self.session.map_obj.width, self.session.map_obj.height
        if self.session.selection_start and self.session.selection_end:
            x0, y0 = self.session.selection_start
            x1, y1 = self.session.selection_end
            sx, ex = min(x0, x1), max(x0, x1)
            sy, ey = min(y0, y1), max(y0, y1)
            return (sx, ex + 1), (sy, ey + 1)
        return (0, map_w), (0, map_h)

    def handle_event(self, event):
        if event.type != pygame.KEYDOWN: return
        
        if event.key == pygame.K_UP:
            self.selected_idx = (self.selected_idx - 1) % len(self.options)
        elif event.key == pygame.K_DOWN:
            self.selected_idx = (self.selected_idx + 1) % len(self.options)
        elif event.key == pygame.K_ESCAPE:
            self.manager.pop()
        elif event.key == pygame.K_RETURN or event.key == pygame.K_RIGHT:
            _, _, action = self.options[self.selected_idx]
            if action: action()
        elif event.key == pygame.K_LEFT:
             # Maybe decrease value?
             pass

    def draw(self, surface):
        overlay = pygame.Surface((self.context.width, self.context.height), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        surface.blit(overlay, (0, 0))

        menu_w, menu_h = 600, 500
        mx, my = (self.context.width - menu_w)//2, (self.context.height - menu_h)//2
        pygame.draw.rect(surface, (30, 30, 40), (mx, my, menu_w, menu_h))
        pygame.draw.rect(surface, (0, 255, 255), (mx, my, menu_w, menu_h), 2)

        title = self.context.font.render(self.title, True, (0, 255, 255))
        surface.blit(title, (mx + 20, my + 20))

        for i, (label, getter, _) in enumerate(self.options):
            color = (255, 255, 255) if i == self.selected_idx else (150, 150, 150)
            val_str = getter() if getter else ""
            text = f"{label}: {val_str}"
            surf = self.context.font.render(text, True, color)
            surface.blit(surf, (mx + 30, my + 80 + i * 40))

class CAGenState(BaseGenConfigState):
    def __init__(self, manager, context, session):
        super().__init__(manager, context, session, "CELLULAR AUTOMATA CONFIG")
        self.mode = 'classic' # or 'existing'
        self.iterations = 4
        self.birth = 4
        self.death = 3
        self.wall_tile = REGISTRY.get_by_char('#') or 1
        self.floor_tile = REGISTRY.get_by_char('.') or 0
        self.target_tiles = set() # For existing mode input

        self._rebuild_options()

    def _rebuild_options(self):
        self.options = [
            ("Mode", lambda: self.mode.upper(), self._toggle_mode),
            ("Iterations", lambda: str(self.iterations), self._input_iters),
            ("Birth Limit", lambda: str(self.birth), self._input_birth),
            ("Death Limit", lambda: str(self.death), self._input_death),
            ("Wall Tile", lambda: self._get_tile_label(self.wall_tile), self._pick_wall),
            ("Floor Tile", lambda: self._get_tile_label(self.floor_tile), self._pick_floor),
            ("Target Tiles (Existing Mode)", lambda: f"{len(self.target_tiles)} selected" if self.target_tiles else "All/Non-Floor", self._pick_targets),
            ("APPLY", lambda: "", self._apply)
        ]

    def _toggle_mode(self):
        self.mode = 'existing' if self.mode == 'classic' else 'classic'

    def _input_iters(self):
        self._prompt_num("Iterations:", lambda x: setattr(self, 'iterations', x))
    
    def _input_birth(self):
        self._prompt_num("Birth Limit:", lambda x: setattr(self, 'birth', x))

    def _input_death(self):
        self._prompt_num("Death Limit:", lambda x: setattr(self, 'death', x))

    def _prompt_num(self, prompt, setter):
        def on_val(v):
            if v and v.isdigit(): setter(int(v))
        self.manager.push(FormState(self.manager, self.context, prompt, [["Value", "", "val"]], lambda r: on_val(r['val'])))

    def _pick_wall(self):
        self.manager.push(TilePickerState(self.manager, self.context, lambda t: setattr(self, 'wall_tile', t)))

    def _pick_floor(self):
        self.manager.push(TilePickerState(self.manager, self.context, lambda t: setattr(self, 'floor_tile', t)))

    def _pick_targets(self):
        def on_picked(tiles):
            self.target_tiles = set(tiles)
        self.manager.push(MultiTilePickerState(self.manager, self.context, on_picked, self.target_tiles))

    def _apply(self):
        x_range, y_range = self._get_selection_range()
        apply_cellular_automata_region(
            self.session.map_obj,
            x_range, y_range,
            list(self.target_tiles),
            self.floor_tile,
            self.wall_tile,
            self.iterations,
            self.birth,
            self.death,
            self.mode
        )
        self.context.invalidate_cache()
        self.session.tool_state.edits_since_save += 1
        self.manager.pop() # Close config
        self.manager.pop() # Close main menu

class NoiseGenState(BaseGenConfigState):
    def __init__(self, manager, context, session):
        super().__init__(manager, context, session, "WEIGHTED NOISE CONFIG")
        self.weight = 50
        self.primary_tile = REGISTRY.get_by_char('#') or 1
        self.bg_tile = REGISTRY.get_by_char('.') or 0
        self._rebuild_options()

    def _rebuild_options(self):
        self.options = [
            ("Primary Tile", lambda: self._get_tile_label(self.primary_tile), self._pick_primary),
            ("Background Tile", lambda: self._get_tile_label(self.bg_tile), self._pick_bg),
            ("Weight (%)", lambda: str(self.weight), self._input_weight),
            ("APPLY", lambda: "", self._apply)
        ]

    def _pick_primary(self):
        self.manager.push(TilePickerState(self.manager, self.context, lambda t: setattr(self, 'primary_tile', t)))
        
    def _pick_bg(self):
        self.manager.push(TilePickerState(self.manager, self.context, lambda t: setattr(self, 'bg_tile', t)))

    def _input_weight(self):
        def on_val(r):
            if r and r['val'].isdigit(): self.weight = max(0, min(100, int(r['val'])))
        self.manager.push(FormState(self.manager, self.context, "Weight %", [["Value", str(self.weight), "val"]], on_val))

    def _apply(self):
        x_range, y_range = self._get_selection_range()
        weights = {self.primary_tile: self.weight, self.bg_tile: 100 - self.weight}
        apply_weighted_noise_region(self.session.map_obj, x_range, y_range, weights)
        self.context.invalidate_cache()
        self.session.tool_state.edits_since_save += 1
        self.manager.pop()
        self.manager.pop()

class ShuffleGenState(BaseGenConfigState):
    def __init__(self, manager, context, session):
        super().__init__(manager, context, session, "SHUFFLE CONFIG")
        self.target_tiles = set()
        self._rebuild_options()

    def _rebuild_options(self):
        self.options = [
            ("Target Tiles", lambda: f"{len(self.target_tiles)} selected" if self.target_tiles else "All Tiles", self._pick_targets),
            ("APPLY", lambda: "", self._apply)
        ]

    def _pick_targets(self):
        def on_picked(tiles):
            self.target_tiles = set(tiles)
        self.manager.push(MultiTilePickerState(self.manager, self.context, on_picked, self.target_tiles))

    def _apply(self):
        x_range, y_range = self._get_selection_range()
        apply_shuffle_region(self.session.map_obj, x_range, y_range, list(self.target_tiles))
        self.context.invalidate_cache()
        self.session.tool_state.edits_since_save += 1
        self.manager.pop()
        self.manager.pop()

