import numpy as np
import tcod
import tcod.bsp
import random
from scipy.signal import convolve2d

def cellular_automata_cave(map_obj, iterations=5, wall_id=1, floor_id=0,
                           seed=None, use_dual_rule=True, verbose=False, z=0):
    """
    Generate a cave map using cellular automata.
    wall_id, floor_id : int (Tile IDs)
    """
    if seed is None:
        seed = random.randint(0, 999999)

    if verbose:
        print(f"Generating cave: iterations={iterations}, seed={seed}")

    rng = np.random.default_rng(seed)
    width, height = map_obj.width, map_obj.height

    # Initial random grid (48% walls for stricter rules)
    grid = rng.random((height, width)) <= 0.48
    grid = grid.astype(np.uint8)  # 1 = wall, 0 = floor

    # Set borders to walls
    grid[0, :] = 1
    grid[-1, :] = 1
    grid[:, 0] = 1
    grid[:, -1] = 1

    # Kernel to count neighbours (excluding centre)
    kernel = np.ones((3, 3), dtype=np.uint8)
    kernel[1, 1] = 0

    for i in range(iterations):
        neighbour_count = convolve2d(grid, kernel, mode='same',
                                     boundary='fill', fillvalue=0)

        new_grid = grid.copy()
        if use_dual_rule and i < iterations // 2:
            # First half: slightly strict rule (B5/S4)
            new_grid[(grid == 1) & (neighbour_count < 4)] = 0
            new_grid[(grid == 0) & (neighbour_count >= 5)] = 1
        else:
            # Second half: very strict rule (B5/S5)
            new_grid[(grid == 1) & (neighbour_count < 5)] = 0
            new_grid[(grid == 0) & (neighbour_count >= 5)] = 1

        grid = new_grid
        # Reinforce borders
        grid[0, :] = 1
        grid[-1, :] = 1
        grid[:, 0] = 1
        grid[:, -1] = 1

    # Write final grid to map object
    map_obj.push_undo()
    map_obj.ensure_layer(z)
    map_obj.layers[z][:] = np.where(grid, wall_id, floor_id)
    map_obj.dirty = True

def bsp_generation(map_obj, x_range, y_range, street_tile, min_block_size, iterations, two_lanes, has_median, median_tile=None, z=0):
    x0, x1 = x_range
    y0, y1 = y_range
    w = x1 - x0
    h = y1 - y0
    
    if w <= 0 or h <= 0: return

    # Ensure layer
    map_obj.ensure_layer(z)

    # Create BSP Root
    root = tcod.bsp.BSP(x=0, y=0, width=w, height=h)

    # Split
    # min_size needs to accommodate the street width to leave useful blocks
    # Street width is up to 3. So let's ensure nodes are at least min_block + 3 roughly
    # But user sets min_block_size directly. I'll trust their input but maybe enforce a minimum for split logic.
    root.split_recursive(
        depth=iterations,
        min_width=min_block_size,
        min_height=min_block_size,
        max_horizontal_ratio=1.5,
        max_vertical_ratio=1.5
    )

    map_obj.push_undo()
    layer = map_obj.layers[z]

    def draw_node(node):
        if not node.children:
            return

        # Draw split line
        # node.position is absolute coordinate (relative to root x,y)
        split_pos = node.position

        # Determine street width
        width = 1
        if two_lanes:
            width = 3 if has_median else 2

        # Calculate offsets to center the street around the split
        # width 1: [0] (at split pos) -> actually, let's put it at split_pos
        # width 2: [-1, 0]
        # width 3: [-1, 0, 1]

        offsets = []
        if width == 1:
            offsets = [0]
        elif width == 2:
            offsets = [-1, 0]
        elif width == 3:
            offsets = [-1, 0, 1]

        if node.horizontal:
            # Horizontal split (y = split_pos)
            for off in offsets:
                y = y0 + split_pos + off
                if y0 <= y < y1:
                    sx = x0 + node.x
                    ex = sx + node.width

                    tile_to_use = street_tile
                    if has_median and width == 3 and off == 0:
                        if median_tile: tile_to_use = median_tile

                    sx = max(0, min(sx, map_obj.width))
                    ex = max(0, min(ex, map_obj.width))

                    if 0 <= y < map_obj.height and sx < ex:
                        layer[y, sx:ex] = tile_to_use
        else:
            # Vertical split (x = split_pos)
            for off in offsets:
                x = x0 + split_pos + off
                if x0 <= x < x1:
                    sy = y0 + node.y
                    ey = sy + node.height

                    tile_to_use = street_tile
                    if has_median and width == 3 and off == 0:
                        if median_tile: tile_to_use = median_tile

                    sy = max(0, min(sy, map_obj.height))
                    ey = max(0, min(ey, map_obj.height))

                    if 0 <= x < map_obj.width and sy < ey:
                        layer[sy:ey, x] = tile_to_use

        for child in node.children:
            draw_node(child)

    draw_node(root)
    map_obj.dirty = True


def perlin_noise_generation(map_obj, tile_ids, scale=10.0, octaves=4,
                            persistence=0.5, seed=None, z=0):
    """
    Generate terrain using Perlin noise (FBM).
    """
    if seed is None:
        seed = random.randint(0, 999999)

    width, height = map_obj.width, map_obj.height
    seed_val = int(seed) % (2**31 - 1)

    noise = tcod.noise.Noise(
        dimensions=2,
        algorithm=tcod.noise.Algorithm.PERLIN,
        implementation=tcod.noise.Implementation.FBM,
        lacunarity=2.0,
        octaves=octaves,
        hurst=persistence,   # persistence used as Hurst exponent
        seed=seed_val
    )

    x_coords = np.arange(width, dtype=np.float32) / scale
    y_coords = np.arange(height, dtype=np.float32) / scale
    samples = noise.sample_ogrid((x_coords, y_coords))

    min_val, max_val = samples.min(), samples.max()
    if max_val > min_val:
        samples = (samples - min_val) / (max_val - min_val)
    else:
        samples = np.zeros_like(samples)

    # Write to map object using vectorized indexing
    map_obj.push_undo()
    indices = (samples * len(tile_ids)).astype(np.uint16)
    indices = np.clip(indices, 0, len(tile_ids) - 1)
    
    tile_ids_arr = np.array(tile_ids, dtype=np.uint16)
    map_obj.ensure_layer(z)
    map_obj.layers[z][:] = tile_ids_arr[indices]
    map_obj.dirty = True
    
    return seed


def voronoi_generation(map_obj, tile_ids, num_points=20, seed=None, z=0):
    """
    Generate a Voronoi diagram, assigning a random tile to each region.
    """
    if seed is None:
        seed = random.randint(0, 999999)

    rng = np.random.default_rng(seed)
    width, height = map_obj.width, map_obj.height

    points_x = rng.integers(0, width, size=num_points)
    points_y = rng.integers(0, height, size=num_points)

    xv, yv = np.meshgrid(np.arange(width), np.arange(height))
    distances = (xv[..., np.newaxis] - points_x) ** 2 + \
                (yv[..., np.newaxis] - points_y) ** 2
    region_indices = np.argmin(distances, axis=-1)

    point_ids = rng.choice(tile_ids, size=num_points)

    # Vectorized write
    map_obj.push_undo()
    map_obj.ensure_layer(z)
    map_obj.layers[z][:] = point_ids[region_indices].astype(np.uint16)
    map_obj.dirty = True
    
    return seed


def apply_cellular_automata_region(map_obj, x_range, y_range, target_tiles, floor_tile, wall_tile, iterations=4, birth_limit=4, death_limit=3, mode='classic', z=0):
    """
    Apply CA to a specific region of the map.
    mode: 'classic' (random init) or 'existing' (use current map)
    """
    x0, x1 = x_range
    y0, y1 = y_range
    w = x1 - x0
    h = y1 - y0
    if w <= 0 or h <= 0: return

    map_obj.ensure_layer(z)
    sub_map = map_obj.layers[z][y0:y1, x0:x1]
    
    if mode == 'existing':
        # Grid: 1 where it matches target_tiles, 0 otherwise
        # If target_tiles is empty, maybe default to non-floor? 
        # But for 'existing' mode, we usually want specific tiles to be 'alive'.
        if not target_tiles:
            # Fallback: Treat non-floor as alive if no targets specified
            grid = (sub_map != floor_tile).astype(np.uint8)
        else:
            grid = np.isin(sub_map, target_tiles).astype(np.uint8)
    else:
        # Classic: Random initialization
        rng = np.random.default_rng()
        grid = (rng.random((h, w)) < 0.45).astype(np.uint8)

    kernel = np.array([[1,1,1],[1,0,1],[1,1,1]], dtype=np.uint8)
    
    for _ in range(iterations):
        neighbors = convolve2d(grid, kernel, mode='same', boundary='symm')
        
        mask_survive = (grid == 1) & (neighbors >= death_limit)
        mask_birth = (grid == 0) & (neighbors >= birth_limit)
        
        new_grid = np.zeros_like(grid)
        new_grid[mask_survive | mask_birth] = 1
        grid = new_grid
        
    output = np.full_like(sub_map, floor_tile)
    output[grid == 1] = wall_tile
    
    map_obj.push_undo()
    map_obj.layers[z][y0:y1, x0:x1] = output
    map_obj.dirty = True

def apply_weighted_noise_region(map_obj, x_range, y_range, weights: dict, z=0):
    x0, x1 = x_range
    y0, y1 = y_range
    w = x1 - x0
    h = y1 - y0
    if w <= 0 or h <= 0: return

    tiles = np.array(list(weights.keys()))
    probs = np.array(list(weights.values()), dtype=np.float64)
    if probs.sum() == 0: return
    probs /= probs.sum()
    
    choices = np.random.choice(tiles, size=(h, w), p=probs).astype(np.uint16)
    
    map_obj.push_undo()
    map_obj.ensure_layer(z)
    map_obj.layers[z][y0:y1, x0:x1] = choices
    map_obj.dirty = True

def apply_shuffle_region(map_obj, x_range, y_range, target_tiles=None, z=0):
    x0, x1 = x_range
    y0, y1 = y_range
    w = x1 - x0
    h = y1 - y0
    if w <= 0 or h <= 0: return

    map_obj.ensure_layer(z)
    sub_map = map_obj.layers[z][y0:y1, x0:x1]
    
    if target_tiles:
        # Only shuffle specific tiles amongst themselves
        mask = np.isin(sub_map, target_tiles)
        values = sub_map[mask]
        np.random.shuffle(values)
        
        # Write back
        new_sub = sub_map.copy()
        new_sub[mask] = values
        
        map_obj.push_undo()
        map_obj.layers[z][y0:y1, x0:x1] = new_sub
    else:
        # Shuffle everything
        flat = sub_map.flatten()
        np.random.shuffle(flat)
        map_obj.push_undo()
        map_obj.layers[z][y0:y1, x0:x1] = flat.reshape((h, w))
        
    map_obj.dirty = True
