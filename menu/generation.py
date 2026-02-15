from tiles import REGISTRY
from generation import cellular_automata_cave, perlin_noise_generation, voronoi_generation
from menu.base import FormState, MessageState

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
    return True # Indicates we launched the menu

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
