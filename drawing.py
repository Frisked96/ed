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
        for by in range(y - offset, y + offset + 1):
            for bx in range(x - offset, x + offset + 1):
                map_obj.set(bx, by, final_char(bx, by, char))

def flood_fill(map_obj, x, y, new_char):
    old_char = map_obj.get(x, y)
    if old_char is None or old_char == new_char: return

    queue = deque([(x, y)])
    visited = set([(x, y)])

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
    min_x, max_x = min(x0, x1), max(x0, x1)
    min_y, max_y = min(y0, y1), max(y0, y1)

    if filled:
        for y in range(max(0, min_y), min(map_obj.height - 1, max_y) + 1):
            for x in range(max(0, min_x), min(map_obj.width - 1, max_x) + 1):
                map_obj.set(x, y, char)
    else:
        for x in range(max(0, min_x), min(map_obj.width - 1, max_x) + 1):
            place_tile_at(map_obj, x, min_y, char, brush_size, brush_shape, tool_state)
            place_tile_at(map_obj, x, max_y, char, brush_size, brush_shape, tool_state)
        for y in range(max(0, min_y), min(map_obj.height - 1, max_y) + 1):
            place_tile_at(map_obj, min_x, y, char, brush_size, brush_shape, tool_state)
            place_tile_at(map_obj, max_x, y, char, brush_size, brush_shape, tool_state)

def draw_circle(map_obj, cx, cy, radius, char, filled, brush_size=1, brush_shape=None, tool_state=None):
    if filled:
        for y in range(max(0, cy - radius), min(map_obj.height - 1, cy + radius) + 1):
            for x in range(max(0, cx - radius), min(map_obj.width - 1, cx + radius) + 1):
                if ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5 <= radius:
                    map_obj.set(x, y, char)
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
    p_h, p_w = len(pattern), len(pattern[0])
    min_x, max_x = min(x0, x1), max(x0, x1)
    min_y, max_y = min(y0, y1), max(y0, y1)

    for y in range(max(0, min_y), min(map_obj.height - 1, max_y) + 1):
        for x in range(max(0, min_x), min(map_obj.width - 1, max_x) + 1):
            map_obj.set(x, y, pattern[(y - min_y) % p_h][(x - min_x) % p_w])
