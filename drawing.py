import numpy as np
from collections import deque
from tiles import REGISTRY

def apply_autotiling(map_obj, x, y, base_tile_id, _rules):
    # TODO: Refactor autotiling for ID based rules
    # For now, just return the base tile
    return base_tile_id

def place_tile_at(map_obj, x, y, tile_id, brush_size=1, brush_shape=None, tool_state=None):
    def final_tile(cx, cy, base):
        if tool_state and tool_state.auto_tiling:
            return apply_autotiling(map_obj, cx, cy, base, tool_state.tiling_rules)
        return base

    if brush_shape:
        h = len(brush_shape)
        w = len(brush_shape[0])
        off_y = h // 2
        off_x = w // 2
        for dy in range(h):
            for dx in range(w):
                if brush_shape[dy][dx]:
                    nx, ny = x + dx - off_x, y + dy - off_y
                    map_obj.set(nx, ny, final_tile(nx, ny, tile_id))
    elif brush_size <= 1:
        map_obj.set(x, y, final_tile(x, y, tile_id))
    else:
        offset = brush_size // 2
        y0, y1 = max(0, y - offset), min(map_obj.height, y + offset + 1)
        x0, x1 = max(0, x - offset), min(map_obj.width, x + offset + 1)
        
        if tool_state and tool_state.auto_tiling:
            for by in range(y0, y1):
                for bx in range(x0, x1):
                    map_obj.set(bx, by, final_tile(bx, by, tile_id))
        else:
            # Faster bulk set if no autotiling
            map_obj.data[y0:y1, x0:x1] = tile_id
            map_obj.dirty = True
            map_obj.trigger_full_update()

def flood_fill(map_obj, x, y, new_tile_id):
    old_tile_id = map_obj.get(x, y)
    if old_tile_id is None or old_tile_id == new_tile_id: return

    queue = deque([(x, y)])
    visited = {(x, y)}

    while queue:
        cx, cy = queue.popleft()
        map_obj.set(cx, cy, new_tile_id)

        for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
            if map_obj.is_inside(nx, ny) and (nx, ny) not in visited:
                if map_obj.get(nx, ny) == old_tile_id:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

def get_line_points(x0, y0, x1, y1):
    points = []
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    x, y = x0, y0
    while True:
        points.append((x, y))
        if x == x1 and y == y1: break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy
    return points

def draw_line(map_obj, x0, y0, x1, y1, tile_id, brush_size=1, brush_shape=None, tool_state=None):
    for x, y in get_line_points(x0, y0, x1, y1):
        place_tile_at(map_obj, x, y, tile_id, brush_size, brush_shape, tool_state)

def get_rect_points(x0, y0, x1, y1, filled=False):
    points = []
    min_x, max_x = (x0, x1) if x0 < x1 else (x1, x0)
    min_y, max_y = (y0, y1) if y0 < y1 else (y1, y0)

    if filled:
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                points.append((x, y))
    else:
        for x in range(min_x, max_x + 1):
            points.append((x, min_y))
            points.append((x, max_y))
        for y in range(min_y + 1, max_y):
            points.append((min_x, y))
            points.append((max_x, y))
    return points

def draw_rectangle(map_obj, x0, y0, x1, y1, tile_id, filled, brush_size=1, brush_shape=None, tool_state=None):
    if filled:
        # Optimized filled draw
        min_x, max_x = (x0, x1) if x0 < x1 else (x1, x0)
        min_y, max_y = (y0, y1) if y0 < y1 else (y1, y0)
        y0_f, y1_f = max(0, min_y), min(map_obj.height, max_y + 1)
        x0_f, x1_f = max(0, min_x), min(map_obj.width, max_x + 1)
        map_obj.data[y0_f:y1_f, x0_f:x1_f] = tile_id
        map_obj.dirty = True
        map_obj.trigger_full_update()
    else:
        for x, y in get_rect_points(x0, y0, x1, y1, filled=False):
            place_tile_at(map_obj, x, y, tile_id, brush_size, brush_shape, tool_state)

def get_circle_points(cx, cy, radius, filled=False):
    points = []
    if filled:
        # Note: Filled circle usually handled by mask optimization in main draw,
        # but for preview we might need points. However, user asked for hollow preview.
        # We'll implement a basic filled circle point generator just in case.
        for y in range(cy - radius, cy + radius + 1):
            for x in range(cx - radius, cx + radius + 1):
                if (x - cx)**2 + (y - cy)**2 <= radius**2:
                    points.append((x, y))
    else:
        x, y = radius, 0
        err = 0
        while x >= y:
            p = [
                (cx + x, cy + y), (cx + y, cy + x),
                (cx - y, cy + x), (cx - x, cy + y),
                (cx - x, cy - y), (cx - y, cy - x),
                (cx + y, cy - x), (cx + x, cy - y)
            ]
            points.extend(p)

            y += 1
            if err <= 0:
                err += 2*y + 1
            else:
                x -= 1
                err += 2*(y - x) + 1
    return points

def draw_circle(map_obj, cx, cy, radius, tile_id, filled, brush_size=1, brush_shape=None, tool_state=None):
    if filled:
        y0, y1 = max(0, cy - radius), min(map_obj.height, cy + radius + 1)
        x0, x1 = max(0, cx - radius), min(map_obj.width, cx + radius + 1)
        Y, X = np.ogrid[y0:y1, x0:x1]
        dist_sq = (X - cx)**2 + (Y - cy)**2
        mask = dist_sq <= radius**2
        map_obj.data[y0:y1, x0:x1][mask] = tile_id
        map_obj.dirty = True
        map_obj.trigger_full_update()
    else:
        for x, y in get_circle_points(cx, cy, radius, filled=False):
            place_tile_at(map_obj, x, y, tile_id, brush_size, brush_shape, tool_state)

def draw_pattern_rectangle(map_obj, x0, y0, x1, y1, pattern):
    # Pattern also needs to be updated to support IDs if it's not already
    # For now, we disable pattern drawing to avoid crashing
    pass
