import random
import numpy as np
import tcod
from scipy.signal import convolve2d

def cellular_automata_cave(map_obj, iterations=5, wall_char='#', floor_char='.', seed=None):
    """Generate a cave map using cellular automata (4-5 rule)."""
    if seed is not None:
        np.random.seed(seed)

    width, height = map_obj.width, map_obj.height

    # Initial random grid (45% walls)
    grid = np.random.rand(height, width)
    grid = (grid <= 0.45).astype(np.uint8)  # 1 = wall, 0 = floor

    # Set borders to walls
    grid[0, :] = 1
    grid[-1, :] = 1
    grid[:, 0] = 1
    grid[:, -1] = 1

    # Kernel to count wall neighbours (excluding centre)
    kernel = np.ones((3, 3), dtype=np.uint8)
    kernel[1, 1] = 0

    for _ in range(iterations):
        # Count walls in Moore neighbourhood
        neighbour_count = convolve2d(grid, kernel, mode='same', boundary='fill', fillvalue=0)

        # Apply rules: a wall becomes floor if <4 walls, floor becomes wall if ≥5 walls
        new_grid = grid.copy()
        new_grid[(grid == 1) & (neighbour_count < 4)] = 0
        new_grid[(grid == 0) & (neighbour_count >= 5)] = 1
        grid = new_grid

        # Re‑enforce borders (they must remain walls)
        grid[0, :] = 1
        grid[-1, :] = 1
        grid[:, 0] = 1
        grid[:, -1] = 1

    # Write final grid to map object
    for y in range(height):
        for x in range(width):
            map_obj.set(x, y, wall_char if grid[y, x] else floor_char)


def perlin_noise_generation(map_obj, tile_chars, scale=10.0, octaves=4, persistence=0.5, seed=0):
    """Generate terrain using Perlin noise (FBM implementation)."""
    width, height = map_obj.width, map_obj.height

    # Create noise generator with Fractal Brownian Motion to use octaves
    noise = tcod.noise.Noise(
        dimensions=2,
        algorithm=tcod.noise.Algorithm.PERLIN,
        implementation=tcod.noise.Implementation.FBM,   # was SIMPLE – now uses octaves
        lacunarity=2.0,
        octaves=octaves,
        hurst=persistence,   # persistence controls amplitude decay
        seed=seed
    )

    # Sample noise over the whole map
    x_coords = np.arange(width, dtype=np.float32) / scale
    y_coords = np.arange(height, dtype=np.float32) / scale
    samples = noise.sample_ogrid((x_coords, y_coords))  # returns shape (height, width)

    # Normalize to [0, 1]
    min_val, max_val = samples.min(), samples.max()
    samples = (samples - min_val) / (max_val - min_val + 1e-8)   # avoid division by zero

    # Map noise values to tile characters
    for y in range(height):
        for x in range(width):
            idx = int(samples[y, x] * len(tile_chars))
            idx = min(idx, len(tile_chars) - 1)
            map_obj.set(x, y, tile_chars[idx])


def voronoi_generation(map_obj, tile_chars, num_points=20, seed=None):
    """Generate a Voronoi diagram and colour each region with a random tile character."""
    if seed is not None:
        np.random.seed(seed)

    width, height = map_obj.width, map_obj.height

    # Randomly place seed points
    points_x = np.random.randint(0, width, size=num_points)
    points_y = np.random.randint(0, height, size=num_points)

    # Create a grid of coordinates
    xv, yv = np.meshgrid(np.arange(width), np.arange(height))  # both shape (height, width)

    # Compute squared distance to every seed point for all cells
    # Shape of distances: (height, width, num_points)
    distances = (xv[..., np.newaxis] - points_x) ** 2 + (yv[..., np.newaxis] - points_y) ** 2

    # For each cell, find the index of the closest seed point
    region_indices = np.argmin(distances, axis=-1)   # shape (height, width)

    # Assign a random tile character to each Voronoi region
    point_chars = np.random.choice(tile_chars, size=num_points)

    # Write to map
    for y in range(height):
        for x in range(width):
            region = region_indices[y, x]
            map_obj.set(x, y, point_chars[region])
