from tiles import REGISTRY
from generation import (
    cellular_automata_cave, perlin_noise_generation, voronoi_generation,
    apply_cellular_automata_region, apply_weighted_noise_region, apply_shuffle_region,
    bsp_generation
)
from menu.base import FormState, MessageState, State, MenuState
from menu.pickers import TilePickerState, MultiTilePickerState
import pygame
import pygame_gui
from pygame_gui.elements import UIWindow, UIScrollingContainer, UILabel, UIButton
from core import EditorSession

# --- Simple Menu Helpers (unchanged) ---

def menu_random_generation(context, map_obj, seed=None, z=0):
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

            final_seed = cellular_automata_cave(map_obj, iterations, wall_id, floor_id, gen_seed, z=z)
            if gen_seed is None:
                context.manager.push(MessageState(context.manager, context, f"Generated with seed: {final_seed}"))
            context.invalidate_cache()
        except Exception as e:
            print(e)

    context.manager.push(FormState(context.manager, context, "CAVE GENERATION SETTINGS", fields, on_submit))
    return True

def menu_perlin_generation(context, map_obj, seed=None, z=0):
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

            final_seed = perlin_noise_generation(map_obj, tile_ids, scale, octaves, persistence, gen_seed, z=z)
            if gen_seed is None:
                context.manager.push(MessageState(context.manager, context, f"Generated with seed: {final_seed}"))
            context.invalidate_cache()
        except Exception as e:
            print(e)

    context.manager.push(FormState(context.manager, context, "PERLIN NOISE SETTINGS", fields, on_submit))
    return True

def menu_voronoi_generation(context, map_obj, seed=None, z=0):
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

            final_seed = voronoi_generation(map_obj, tile_ids, num_points, gen_seed, z=z)
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
            ("BSP Partition", self._open_bsp),
        ]
        super().__init__(manager, context, "ADVANCED GENERATION", options)
        self.session = session

    def _open_ca(self):
        self.manager.push(CAGenState(self.manager, self.context, self.session))

    def _open_noise(self):
        self.manager.push(NoiseGenState(self.manager, self.context, self.session))

    def _open_shuffle(self):
        self.manager.push(ShuffleGenState(self.manager, self.context, self.session))

    def _open_bsp(self):
        self.manager.push(BSPGenState(self.manager, self.context, self.session))

class BaseGenConfigState(State):
    def __init__(self, manager, context, session, title):
        super().__init__(manager)
        self.context = context
        self.session = session
        self.title = title
        self.options = [] # list of (label, getter, action/setter)
        self.window = None
        self.ui_elements = [] # list of (getter, ui_element) to update

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

    def enter(self, **kwargs):
        w, h = self.manager.screen.get_size()
        win_w, win_h = 600, 500
        rect = pygame.Rect((w - win_w) // 2, (h - win_h) // 2, win_w, win_h)
        
        self.window = UIWindow(
            rect=rect,
            manager=self.ui_manager,
            window_display_title=self.title
        )

        container = UIScrollingContainer(
            relative_rect=pygame.Rect(0, 0, win_w - 30, win_h - 40),
            manager=self.ui_manager,
            container=self.window
        )

        y = 10
        self.buttons = {} # btn -> action

        for label, getter, action in self.options:
            UILabel(
                relative_rect=pygame.Rect(10, y, 200, 30),
                text=label + ":",
                manager=self.ui_manager,
                container=container
            )

            val_text = getter() if getter else ">>>"
            btn = UIButton(
                relative_rect=pygame.Rect(220, y, 300, 30),
                text=val_text,
                manager=self.ui_manager,
                container=container
            )
            self.buttons[btn] = action
            if getter:
                self.ui_elements.append((getter, btn))

            y += 40

        container.set_scrollable_area_dimensions((win_w - 50, y + 10))

    def exit(self):
        if self.window:
            self.window.kill()

    def handle_event(self, event):
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element in self.buttons:
                action = self.buttons[event.ui_element]
                if action: action()
        elif event.type == pygame_gui.UI_WINDOW_CLOSE:
            if event.ui_element == self.window:
                self.manager.pop()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.manager.pop()

    def update(self, dt):
        # Update dynamic labels
        for getter, element in self.ui_elements:
            new_val = getter()
            if element.text != new_val:
                element.set_text(new_val)

    def draw(self, surface):
        pass

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
        def on_val(r):
            if r and r['val'].isdigit(): setter(int(r['val']))
        self.manager.push(FormState(self.manager, self.context, prompt, [["Value", "", "val"]], on_val))

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
            self.mode,
            z=self.session.active_z_level
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
        apply_weighted_noise_region(self.session.map_obj, x_range, y_range, weights, z=self.session.active_z_level)
        self.context.invalidate_cache()
        self.session.tool_state.edits_since_save += 1
        self.manager.pop()
        self.manager.pop()

class BSPGenState(BaseGenConfigState):
    def __init__(self, manager, context, session):
        super().__init__(manager, context, session, "BSP PARTITION CONFIG")
        t = REGISTRY.get_by_char('#')
        self.street_tile = t if t else 1
        self.min_block_size = 5
        self.iterations = 4
        self.two_lanes = False
        self.has_median = False
        t2 = REGISTRY.get_by_char('+')
        self.median_tile = t2 if t2 else 1

        self._rebuild_options()

    def _rebuild_options(self):
        self.options = [
            ("Street Tile", lambda: self._get_tile_label(self.street_tile), self._pick_street),
            ("Min Block Size", lambda: str(self.min_block_size), self._input_size),
            ("Iterations", lambda: str(self.iterations), self._input_iters),
            ("Two Lanes", lambda: "YES" if self.two_lanes else "NO", self._toggle_two_lanes),
            ("Has Median", lambda: "YES" if self.has_median else "NO", self._toggle_median),
            ("Median Tile", lambda: self._get_tile_label(self.median_tile) if self.has_median else "---", self._pick_median),
            ("APPLY", lambda: "", self._apply)
        ]

    def _pick_street(self):
        self.manager.push(TilePickerState(self.manager, self.context, lambda t: setattr(self, 'street_tile', t)))

    def _pick_median(self):
        if self.has_median:
            self.manager.push(TilePickerState(self.manager, self.context, lambda t: setattr(self, 'median_tile', t)))

    def _input_size(self):
        def on_val(r):
            if r and r['val'].isdigit(): self.min_block_size = max(3, int(r['val']))
        self.manager.push(FormState(self.manager, self.context, "Min Block Size", [["Value", str(self.min_block_size), "val"]], on_val))

    def _input_iters(self):
        def on_val(r):
            if r and r['val'].isdigit(): self.iterations = max(1, min(10, int(r['val'])))
        self.manager.push(FormState(self.manager, self.context, "Iterations", [["Value", str(self.iterations), "val"]], on_val))

    def _toggle_two_lanes(self):
        self.two_lanes = not self.two_lanes
        if not self.two_lanes: self.has_median = False

    def _toggle_median(self):
        if self.two_lanes:
            self.has_median = not self.has_median

    def _apply(self):
        x_range, y_range = self._get_selection_range()
        bsp_generation(
            self.session.map_obj,
            x_range, y_range,
            self.street_tile,
            self.min_block_size,
            self.iterations,
            self.two_lanes,
            self.has_median,
            self.median_tile,
            z=self.session.active_z_level
        )
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
        apply_shuffle_region(self.session.map_obj, x_range, y_range, list(self.target_tiles), z=self.session.active_z_level)
        self.context.invalidate_cache()
        self.session.tool_state.edits_since_save += 1
        self.manager.pop()
        self.manager.pop()

