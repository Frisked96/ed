import numpy as np
from collections import deque

def apply_autotiling(map_obj, x, y, base_char, rules):
    if base_char not in rules: return base_char
    mask = 0
    target_set = set(rules[base_char].values()) | {base_char}
    
    # Check neighbors using map_obj
    if map_obj.get(x, y-1) in target_set: mask |= 1
    if map_obj.get(x+1, y) in target_set: mask |= 2
    if map_obj.get(x, y+1) in target_set: mask |= 4
    if map_obj.get(x-1, y) in target_set: mask |= 8
    
    return rules[base_char].get(mask, base_char)

def place_tile_at(map_obj, x, y, char, brush_size=1, brush_shape=None, tool_state=None):
    def final_char(cx, cy, base):
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
                    map_obj.set(nx, ny, final_char(nx, ny, char))
    elif brush_size <= 1:
        map_obj.set(x, y, final_char(x, y, char))
    else:
        offset = brush_size // 2
        y0, y1 = max(0, y - offset), min(map_obj.height, y + offset + 1)
        x0, x1 = max(0, x - offset), min(map_obj.width, x + offset + 1)
        
        if tool_state and tool_state.auto_tiling:
            for by in range(y0, y1):
                for bx in range(x0, x1):
                    map_obj.set(bx, by, final_char(bx, by, char))
        else:
            # Faster bulk set if no autotiling
            map_obj.data[y0:y1, x0:x1] = char
            map_obj.dirty = True

def flood_fill(map_obj, x, y, new_char):
    old_char = map_obj.get(x, y)
    if old_char is None or old_char == new_char: return

    queue = deque([(x, y)])
    visited = {(x, y)}

    while queue:
        cx, cy = queue.popleft()
        map_obj.set(cx, cy, new_char)

        for nx, ny in [(cx+1, cy), (cx-1, cy), (cx, cy+1), (cx, cy-1)]:
            if map_obj.is_inside(nx, ny) and (nx, ny) not in visited:
                if map_obj.get(nx, ny) == old_char:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

def draw_line(map_obj, x0, y0, x1, y1, char, brush_size=1, brush_shape=None, tool_state=None):
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    x, y = x0, y0
    while True:
        place_tile_at(map_obj, x, y, char, brush_size, brush_shape, tool_state)
        if x == x1 and y == y1: break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x += sx
        if e2 < dx:
            err += dx
            y += sy

def draw_rectangle(map_obj, x0, y0, x1, y1, char, filled, brush_size=1, brush_shape=None, tool_state=None):
    min_x, max_x = (x0, x1) if x0 < x1 else (x1, x0)
    min_y, max_y = (y0, y1) if y0 < y1 else (y1, y0)

    if filled:
        y0_f, y1_f = max(0, min_y), min(map_obj.height, max_y + 1)
        x0_f, x1_f = max(0, min_x), min(map_obj.width, max_x + 1)
        map_obj.data[y0_f:y1_f, x0_f:x1_f] = char
        map_obj.dirty = True
    else:
        for x in range(min_x, max_x + 1):
            place_tile_at(map_obj, x, min_y, char, brush_size, brush_shape, tool_state)
            place_tile_at(map_obj, x, max_y, char, brush_size, brush_shape, tool_state)
        for y in range(min_y + 1, max_y):
            place_tile_at(map_obj, min_x, y, char, brush_size, brush_shape, tool_state)
            place_tile_at(map_obj, max_x, y, char, brush_size, brush_shape, tool_state)

def draw_circle(map_obj, cx, cy, radius, char, filled, brush_size=1, brush_shape=None, tool_state=None):
    if filled:
        y0, y1 = max(0, cy - radius), min(map_obj.height, cy + radius + 1)
        x0, x1 = max(0, cx - radius), min(map_obj.width, cx + radius + 1)
        Y, X = np.ogrid[y0:y1, x0:x1]
        dist_sq = (X - cx)**2 + (Y - cy)**2
        mask = dist_sq <= radius**2
        map_obj.data[y0:y1, x0:x1][mask] = char
        map_obj.dirty = True
    else:
        x, y = radius, 0
        err = 0
        while x >= y:
            points = [
                (cx + x, cy + y), (cx + y, cy + x),
                (cx - y, cy + x), (cx - x, cy + y),
                (cx - x, cy - y), (cx - y, cy - x),
                (cx + y, cy - x), (cx + x, cy - y)
            ]
            for px, py in points:
                place_tile_at(map_obj, px, py, char, brush_size, brush_shape, tool_state)

            y += 1
            if err <= 0:
                err += 2*y + 1
            else:
                x -= 1
                err += 2*(y - x) + 1

def draw_pattern_rectangle(map_obj, x0, y0, x1, y1, pattern):
    if not pattern: return
    p = np.array(pattern, dtype='U1')
    ph, pw = p.shape
    min_x, max_x = (x0, x1) if x0 < x1 else (x1, x0)
    min_y, max_y = (y0, y1) if y0 < y1 else (y1, y0)

    y0_f, y1_f = max(0, min_y), min(map_obj.height, max_y + 1)
    x0_f, x1_f = max(0, min_x), min(map_obj.width, max_x + 1)
    
    h, w = y1_f - y0_f, x1_f - x0_f
    if h <= 0 or w <= 0: return
    
    tiled = np.tile(p, (h // ph + 1, w // pw + 1))
    map_obj.data[y0_f:y1_f, x0_f:x1_f] = tiled[:h, :w]
    map_obj.dirty = True
