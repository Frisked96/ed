import pygame
import sys
import time
from utils import get_key_name, get_distance
from drawing import get_line_points, get_rect_points, get_circle_points
from tiles import REGISTRY
from colors import Colors

# procedural box drawing
BOX_DRAWING_CHARS = {
    # Light (Single) - (Top, Right, Bottom, Left)
    '─': (0, 1, 0, 1), '│': (1, 0, 1, 0),
    '┌': (0, 1, 1, 0), '┐': (0, 0, 1, 1),
    '└': (1, 1, 0, 0), '┘': (1, 0, 0, 1),
    '├': (1, 1, 1, 0), '┤': (1, 0, 1, 1),
    '┬': (0, 1, 1, 1), '┴': (1, 1, 0, 1),
    '┼': (1, 1, 1, 1),
    
    # Heavy - (Top, Right, Bottom, Left)
    '━': (0, 3, 0, 3), '┃': (3, 0, 3, 0),
    '┏': (0, 3, 3, 0), '┓': (0, 0, 3, 3),
    '┗': (3, 3, 0, 0), '┛': (3, 0, 0, 3),
    '┣': (3, 3, 3, 0), '┫': (3, 0, 3, 3),
    '┳': (0, 3, 3, 3), '┻': (3, 3, 0, 3),
    '╋': (3, 3, 3, 3),

    # Double - (Top, Right, Bottom, Left)
    '═': (0, 2, 0, 2), '║': (2, 0, 2, 0),
    '╔': (0, 2, 2, 0), '╗': (0, 0, 2, 2),
    '╚': (2, 2, 0, 0), '╝': (2, 0, 0, 2),
    '╠': (2, 2, 2, 0), '╣': (2, 0, 2, 2),
    '╦': (0, 2, 2, 2), '╩': (2, 2, 0, 2),
    '╬': (2, 2, 2, 2),
    
    # Mixed Light/Heavy
    '┍': (0, 3, 1, 0), '┎': (0, 1, 3, 0),
    '┑': (0, 0, 1, 3), '┒': (0, 0, 3, 1),
    '┕': (1, 3, 0, 0), '┖': (3, 1, 0, 0),
    '┙': (1, 0, 0, 3), '┚': (3, 0, 0, 1),
    '┝': (1, 3, 1, 0), '┞': (1, 1, 3, 0), '┟': (3, 1, 1, 0),
    '┠': (3, 1, 3, 0), '┡': (1, 3, 3, 0), '┢': (3, 3, 1, 0),
    '┥': (1, 0, 1, 3), '┦': (1, 0, 3, 1), '┧': (3, 0, 1, 1),
    '┨': (3, 0, 3, 1), '┩': (1, 0, 3, 3), '┪': (3, 0, 1, 3),
    '┭': (0, 3, 1, 1), '┮': (0, 1, 1, 3), '┯': (0, 3, 1, 3),
    '┰': (0, 1, 3, 1), '┱': (0, 3, 3, 1), '┲': (0, 1, 3, 3),
    '┵': (1, 1, 0, 3), '┶': (1, 3, 0, 1), '┷': (1, 3, 0, 3),
    '┸': (3, 1, 0, 1), '┹': (1, 1, 0, 3), '┺': (3, 1, 0, 3),
    # Single-ended
    '╴': (0, 0, 0, 1), '╵': (1, 0, 0, 0), '╶': (0, 1, 0, 0), '╷': (0, 0, 1, 0),
    '╸': (0, 0, 0, 3), '╹': (3, 0, 0, 0), '╺': (0, 3, 0, 0), '╻': (0, 0, 3, 0),
    # Rounded (drawn as sharp for now to ensure connectivity)
    '╭': (0, 1, 1, 0), '╮': (0, 0, 1, 1), '╯': (1, 0, 0, 1), '╰': (1, 1, 0, 0),
}

class Renderer:
    def __init__(self, screen, tile_size=20):
        self.tile_size = tile_size
        self.screen = screen
        self.width, self.height = screen.get_size()
        
        self.font_size = 32 # Larger font for better fill
        font_names = ["DejaVu Sans Mono", "FreeMono", "Courier New", "monospace", "Arial Unicode MS", "Segoe UI Symbol"]
        self.font = None
        for name in font_names:
            try:
                self.font = pygame.font.SysFont(name, self.font_size, bold=True)
                if self.font and self.font.get_height() > 0:
                    break
            except:
                continue
        
        if not self.font:
            self.font = pygame.font.Font(None, self.font_size)
            
        self.glyph_cache = {}
        self.chunk_cache = {} # (chunk_x, chunk_y) -> Surface
        self.chunk_size = 32
        self.start_time = time.time()
        
        # Subscribe to tile changes
        REGISTRY.subscribe(self.invalidate_cache)

    def _render_box_char(self, char, color, bg_color):
        s = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)
        if bg_color:
            s.fill(bg_color)
        
        ts = self.tile_size
        cx, cy = ts // 2, ts // 2
        
        # Widths
        sw = max(1, int(ts * 0.1))   # Single line
        dw = max(3, int(ts * 0.3))   # Double line total
        gap = max(1, int(ts * 0.1))  # Double line gap
        hw = max(2, int(ts * 0.25))  # Heavy line
        
        # Draw full block
        if char == '█':
            s.fill(color)
            return s

        # Draw partial blocks (U+2580 - U+259F)
        if '\u2580' <= char <= '\u259f':
            # Block elements range: 2580-259F
            # We already handle █ (2588)
            
            # Helper for block rendering
            def draw_block(x_fracs, y_fracs):
                # x_fracs/y_fracs are (start, end) where 0.0 is top/left and 1.0 is bottom/right
                rx = int(x_fracs[0] * ts)
                ry = int(y_fracs[0] * ts)
                rw = int((x_fracs[1] - x_fracs[0]) * ts)
                rh = int((y_fracs[1] - y_fracs[0]) * ts)
                if rw > 0 and rh > 0:
                    pygame.draw.rect(s, color, (rx, ry, rw, rh))

            if char == '▀': draw_block((0, 1), (0, 0.5))
            elif char == '▂': draw_block((0, 1), (0.875, 1))
            elif char == '▃': draw_block((0, 1), (0.75, 1))
            elif char == '▄': draw_block((0, 1), (0.5, 1))
            elif char == '▅': draw_block((0, 1), (0.375, 1))
            elif char == '▆': draw_block((0, 1), (0.25, 1))
            elif char == '▇': draw_block((0, 1), (0.125, 1))
            elif char == '█': draw_block((0, 1), (0, 1))
            elif char == '▉': draw_block((0, 0.875), (0, 1))
            elif char == '▊': draw_block((0, 0.75), (0, 1))
            elif char == '▋': draw_block((0, 0.625), (0, 1))
            elif char == '▌': draw_block((0, 0.5), (0, 1))
            elif char == '▍': draw_block((0, 0.375), (0, 1))
            elif char == '▎': draw_block((0, 0.25), (0, 1))
            elif char == '▏': draw_block((0, 0.125), (0, 1))
            elif char == '▐': draw_block((0.5, 1), (0, 1))
            elif char == '▔': draw_block((0, 1), (0, 0.125))
            elif char == '▕': draw_block((0.875, 1), (0, 1))
            # Quadrants (2596 - 259F)
            elif char == '▖': draw_block((0, 0.5), (0.5, 1))
            elif char == '▗': draw_block((0.5, 1), (0.5, 1))
            elif char == '▘': draw_block((0, 0.5), (0, 0.5))
            elif char == '▙': 
                draw_block((0, 0.5), (0, 1))
                draw_block((0.5, 1), (0.5, 1))
            elif char == '▚':
                draw_block((0, 0.5), (0, 0.5))
                draw_block((0.5, 1), (0.5, 1))
            elif char == '▛':
                draw_block((0, 0.5), (0, 1))
                draw_block((0.5, 1), (0, 0.5))
            elif char == '▜':
                draw_block((0, 1), (0, 0.5))
                draw_block((0.5, 1), (0.5, 1))
            elif char == '▝': draw_block((0.5, 1), (0, 0.5))
            elif char == '▞':
                draw_block((0.5, 1), (0, 0.5))
                draw_block((0, 0.5), (0.5, 1))
            elif char == '▟':
                draw_block((0.5, 1), (0, 1))
                draw_block((0, 0.5), (0.5, 1))
            
            return s

        # Draw shades
        if char in ('░', '▒', '▓'):
            s.fill(bg_color if bg_color else (0, 0, 0, 0))
            # Determine density
            if char == '░': density = 0.25
            elif char == '▒': density = 0.5
            else: density = 0.75
            
            # Draw a stipple pattern that fills the tile
            for y in range(ts):
                for x in range(ts):
                    if char == '▒': # Medium shade - checkerboard
                        if (x + y) % 2 == 0:
                            s.set_at((x, y), color)
                    elif char == '░': # Light shade - 1/4 pixels
                        if x % 2 == 0 and y % 2 == 0:
                            s.set_at((x, y), color)
                    elif char == '▓': # Dark shade - 3/4 pixels
                        if not (x % 2 == 1 and y % 2 == 1):
                            s.set_at((x, y), color)
            return s
            
        # Diagonals
        if char == '╱':
            pygame.draw.line(s, color, (0, ts), (ts, 0), sw)
            return s
        elif char == '╲':
            pygame.draw.line(s, color, (0, 0), (ts, ts), sw)
            return s
        elif char == '╳':
            pygame.draw.line(s, color, (0, 0), (ts, ts), sw)
            pygame.draw.line(s, color, (0, ts), (ts, 0), sw)
            return s

        # Draw box lines
        dirs = BOX_DRAWING_CHARS.get(char)
        if not dirs:
            return None
            
        top, right, bottom, left = dirs
        
        # Helper for rects
        def draw_rect(r):
            pygame.draw.rect(s, color, r)
            
        # Top
        if top == 1:
            draw_rect((cx - sw//2, 0, sw, cy + sw//2))
        elif top == 2:
            draw_rect((cx - dw//2, 0, (dw-gap)//2, cy + dw//2))
            draw_rect((cx + gap//2, 0, (dw-gap)//2, cy + dw//2))
        elif top == 3:
            draw_rect((cx - hw//2, 0, hw, cy + hw//2))

        # Bottom
        if bottom == 1:
            draw_rect((cx - sw//2, cy - sw//2, sw, ts - cy + sw//2))
        elif bottom == 2:
            draw_rect((cx - dw//2, cy - dw//2, (dw-gap)//2, ts - cy + dw//2))
            draw_rect((cx + gap//2, cy - dw//2, (dw-gap)//2, ts - cy + dw//2))
        elif bottom == 3:
            draw_rect((cx - hw//2, cy - hw//2, hw, ts - cy + hw//2))

        # Left
        if left == 1:
            draw_rect((0, cy - sw//2, cx + sw//2, sw))
        elif left == 2:
            draw_rect((0, cy - dw//2, cx + dw//2, (dw-gap)//2))
            draw_rect((0, cy + gap//2, cx + dw//2, (dw-gap)//2))
        elif left == 3:
            draw_rect((0, cy - hw//2, cx + hw//2, hw))

        # Right
        if right == 1:
            draw_rect((cx - sw//2, cy - sw//2, ts - cx + sw//2, sw))
        elif right == 2:
            draw_rect((cx - dw//2, cy - dw//2, ts - cx + dw//2, (dw-gap)//2))
            draw_rect((cx - dw//2, cy + gap//2, ts - cx + dw//2, (dw-gap)//2))
        elif right == 3:
            draw_rect((cx - hw//2, cy - hw//2, ts - cx + hw//2, hw))
            
        return s

    def draw_notifications(self, notifications):
        """Purely visual: takes a list of active notification objects and draws them."""
        # This is handled by StateManager in main loop usually, but passed here?
        # StateManager calls renderer.draw_notifications
        y = 10
        now = time.time()
        for n in notifications:
            time_left = n["expiry"] - now
            alpha = int(min(1.0, time_left / 0.5) * 255)
            surf = self.font.render(n["text"], True, n["color"])
            self.screen.blit(surf, (self.width - surf.get_width() - 10, y))
            y += surf.get_height() + 5

    def invalidate_cache(self):
        self.glyph_cache = {}
        self.chunk_cache = {}

    def invalidate_chunk(self, map_x, map_y):
        cx = map_x // self.chunk_size
        cy = map_y // self.chunk_size
        if (cx, cy) in self.chunk_cache:
            del self.chunk_cache[(cx, cy)]

    def get_glyph(self, tile_id, bg_color=None, char_override=None, color_override=None):
        # Optimized lookup for static tiles
        key = (tile_id, bg_color, char_override, color_override)
        # Only cache if no overrides, or maybe cache overrides too if we want (but they change often)
        # For now, bypassing cache for animations ensures correctness without memory bloat
        if char_override is None and color_override is None and key in self.glyph_cache:
            return self.glyph_cache[key]

        tile_def = REGISTRY.get(tile_id)
        if not tile_def:
            return None
        
        char = char_override if char_override is not None else tile_def.char
        
        # Handle color parsing
        def parse_color(c):
            if isinstance(c, str):
                if c.startswith('#'):
                    try:
                        return pygame.Color(c)
                    except:
                        return (255, 255, 255)
                return COLOR_MAP.get(c.lower(), (255, 255, 255))
            return c

        if color_override is not None:
             color = parse_color(color_override)
        else:
             color = parse_color(tile_def.color)

        # Try procedural rendering first for box/block/shade chars
        if char in BOX_DRAWING_CHARS or '\u2500' <= char <= '\u259f' or char in ('█', '░', '▒', '▓', '▔', '▕'):
            box_surf = self._render_box_char(char, color, bg_color)
            if box_surf:
                # Only cache static glyphs
                if char_override is None and color_override is None:
                    self.glyph_cache[key] = box_surf
                return box_surf

        # Font Rendering
        raw_surf = self.font.render(char, True, color) # No BG here to avoid filling large rect
        
        # Center on a square surface of 'tile_size'
        s = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)
        if bg_color: s.fill(bg_color)
        
        rect = raw_surf.get_rect(center=(self.tile_size//2, self.tile_size//2))
        s.blit(raw_surf, rect)
        
        # Only cache static glyphs
        if char_override is None and color_override is None:
            self.glyph_cache[key] = s
        return s

    def clear(self):
        self.screen.fill(Colors.BLACK)

    def flip(self):
        pygame.display.flip()
        self.clock.tick(60)

    def update_dimensions(self):
        w, h = self.screen.get_size()
        self.width, self.height = w, h

    def _render_chunk(self, session, cx, cy):
        ts = self.tile_size
        surf = pygame.Surface((self.chunk_size * ts, self.chunk_size * ts))
        surf.fill(Colors.BLACK)
        
        start_x = cx * self.chunk_size
        start_y = cy * self.chunk_size
        
        z = session.active_z_level
        
        # Layers to draw: previous level (ghosted), current level (normal)
        layers_to_draw = []
        if z > 0:
            layers_to_draw.append((z - 1, 80)) # Ghost previous level
        layers_to_draw.append((z, 255))      # Current level

        contains_animation = False
        elapsed = time.time() - self.start_time

        for layer_z, alpha in layers_to_draw:
            if layer_z not in session.map_obj.layers:
                continue

            data = session.map_obj.layers[layer_z][start_y : start_y + self.chunk_size, start_x : start_x + self.chunk_size]

            for y_rel, row in enumerate(data):
                py = y_rel * ts
                map_y = start_y + y_rel

                for x_rel, tid in enumerate(row):
                    if tid == 0: continue

                    map_x = start_x + x_rel
                    px = x_rel * ts

                    # Check animation
                    char_ov = None
                    col_ov = None

                    if REGISTRY.is_animated(tid):
                        contains_animation = True
                        tile_def = REGISTRY.get(tid)
                        anim = tile_def.animation
                        if anim:
                            # Sequence Animation (Char Loop)
                            if anim.mode == 'sequence' and anim.frames:
                                f_idx = int(elapsed / anim.frame_duration) % len(anim.frames)
                                val = anim.frames[f_idx]
                                if isinstance(val, int):
                                    ref_tile = REGISTRY.get(val)
                                    char_ov = ref_tile.char if ref_tile else '?'
                                else:
                                    char_ov = str(val)

                            # Flow Animation (Color Wave)
                            elif anim.mode == 'flow' and anim.flow_colors:
                                phase = 0
                                if anim.flow_direction == 'horizontal':
                                    phase = map_x * 0.2
                                elif anim.flow_direction == 'vertical':
                                    phase = map_y * 0.2
                                else: # diagonal
                                    phase = (map_x + map_y) * 0.1

                                c_idx = int((elapsed * anim.flow_speed + phase)) % len(anim.flow_colors)
                                col_ov = anim.flow_colors[c_idx]

                    glyph = self.get_glyph(tid, char_override=char_ov, color_override=col_ov)
                    if glyph:
                        if alpha < 255:
                            temp = glyph.copy()
                            temp.set_alpha(alpha)
                            surf.blit(temp, (px, py))
                        else:
                            surf.blit(glyph, (px, py))
        
        return surf, contains_animation

    def draw_map(self, session):
        # Clear the whole screen first
        self.screen.fill((0, 0, 0))
        
        # Set clipping to viewport (handled by session.viewport_px_w/h)
        viewport_rect = pygame.Rect(0, 0, session.viewport_px_w, session.viewport_px_h)
        self.screen.set_clip(viewport_rect)
        
        map_data = session.map_obj.data
        cam_x, cam_y = session.camera_x, session.camera_y
        view_w = session.view_width
        view_h = session.view_height
        tile_size = self.tile_size
        tool_state = session.tool_state
        
        # 1. Determine visible chunks
        start_cx = int(cam_x // self.chunk_size)
        start_cy = int(cam_y // self.chunk_size)
        
        end_cx = int((cam_x + view_w + 1) // self.chunk_size)
        end_cy = int((cam_y + view_h + 1) // self.chunk_size)
        
        # 2. Draw visible chunks
        for cy in range(start_cy, end_cy + 1):
            if cy < 0 or cy * self.chunk_size >= session.map_obj.height: continue
            for cx in range(start_cx, end_cx + 1):
                if cx < 0 or cx * self.chunk_size >= session.map_obj.width: continue
                
                if (cx, cy) not in self.chunk_cache:
                    chunk_surf, is_anim = self._render_chunk(session, cx, cy)
                    if not is_anim:
                        self.chunk_cache[(cx, cy)] = chunk_surf
                else:
                    chunk_surf = self.chunk_cache[(cx, cy)]
                
                px = (cx * self.chunk_size - cam_x) * tile_size
                py = (cy * self.chunk_size - cam_y) * tile_size
                self.screen.blit(chunk_surf, (px, py))

        # Clipping bounds for overlays (UI area check)
        start_vx = max(0, -cam_x)
        start_vy = max(0, -cam_y)
        end_vx = min(view_w, session.map_obj.width - cam_x)
        end_vy = min(view_h, session.map_obj.height - cam_y)

        # Selection highlight
        if session.selection_start:
            x0, y0 = session.selection_start
            x1, y1 = session.selection_end if session.selection_end else (session.cursor_x, session.cursor_y)
            
            sx0, sx1 = (x0, x1) if x0 < x1 else (x1, x0)
            sy0, sy1 = (y0, y1) if y0 < y1 else (y1, y0)
            
            ix0 = max(sx0, cam_x + start_vx)
            iy0 = max(sy0, cam_y + start_vy)
            ix1 = min(sx1, cam_x + end_vx - 1)
            iy1 = min(sy1, cam_y + end_vy - 1)
            
            if ix0 <= ix1 and iy0 <= iy1:
                sel_px = (ix0 - cam_x) * tile_size
                sel_py = (iy0 - cam_y) * tile_size
                sel_pw = (ix1 - ix0 + 1) * tile_size
                sel_ph = (iy1 - iy0 + 1) * tile_size
                
                color = (60, 60, 120) if session.selection_end else (60, 60, 180, 100)
                pygame.draw.rect(self.screen, color, (sel_px, sel_py, sel_pw, sel_ph))
                pygame.draw.rect(self.screen, (100, 100, 255), (sel_px, sel_py, sel_pw, sel_ph), 2)

        # Brush bounds for ghosting
        br = tool_state.brush_size
        offset = br // 2
        bx0, by0 = session.cursor_x - offset, session.cursor_y - offset
        bx1, by1 = bx0 + br - 1, by0 + br - 1
        
        ibx0 = max(bx0, cam_x + start_vx)
        iby0 = max(by0, cam_y + start_vy)
        ibx1 = min(bx1, cam_x + end_vx - 1)
        iby1 = min(by1, cam_y + end_vy - 1)

        if ibx0 <= ibx1 and iby0 <= iby1:
            b_px = (ibx0 - cam_x) * tile_size
            b_py = (iby0 - cam_y) * tile_size
            b_pw = (ibx1 - ibx0 + 1) * tile_size
            b_ph = (iby1 - iby0 + 1) * tile_size
            pygame.draw.rect(self.screen, (100, 100, 100), (b_px, b_py, b_pw, b_ph))
            
            if ibx0 <= session.cursor_x <= ibx1 and iby0 <= session.cursor_y <= iby1:
                c_px = (session.cursor_x - cam_x) * tile_size
                c_py = (session.cursor_y - cam_y) * tile_size
                pygame.draw.rect(self.screen, (200, 200, 200), (c_px, c_py, tile_size, tile_size))

        self._draw_tool_preview(session)
        self._draw_macro_preview(session)
        self._draw_measurement_overlay(session)
        
        self.screen.set_clip(None)

    def _draw_macro_preview(self, session):
        ts = session.tool_state
        if ts.mode != 'macro' or not ts.selected_macro:
            return
            
        if ts.selected_macro not in ts.macros:
            return
            
        macro = ts.macros[ts.selected_macro]
        tiles = macro['tiles']
        
        cam_x, cam_y = session.camera_x, session.camera_y
        tile_size = self.tile_size
        
        start_x, start_y = session.cursor_x, session.cursor_y
        
        iterations = ts.macro_iterations
        if ts.macro_until_end:
            # Heuristic for preview (don't draw 1000 tiles, maybe just 20 or until screen edge)
            ox, oy = ts.macro_offset
            if ox == 0 and oy == 0:
                iterations = 1
            else:
                iterations = 20 # Cap preview for performance
        
        # Create a semi-transparent surface for the ghosting effect
        for i in range(iterations):
            base_x = start_x + i * ts.macro_offset[0]
            base_y = start_y + i * ts.macro_offset[1]
            
            for dx, dy, tid in tiles:
                map_x, map_y = base_x + dx, base_y + dy
                
                # Check visibility
                if map_x < cam_x or map_y < cam_y or \
                   map_x >= cam_x + session.view_width or \
                   map_y >= cam_y + session.view_height:
                    continue
                
                glyph = self.get_glyph(tid)
                if glyph:
                    px = (map_x - cam_x) * tile_size
                    py = (map_y - cam_y) * tile_size
                    
                    # Optional: apply some alpha to the preview
                    # For now just blit
                    self.screen.blit(glyph, (px, py))
                    # Draw a faint border to indicate it's a preview
                    pygame.draw.rect(self.screen, (255, 255, 0), (px, py, tile_size, tile_size), 1)

    def _draw_measurement_overlay(self, session):
        if not session.tool_state.measurement_active: return
        
        cfg = session.tool_state.measurement_config
        grid_size = int(cfg.get('grid_size', 100))
        show_coords = cfg.get('show_coords', True)
        color = cfg.get('color', Colors.CYAN)
        points = cfg.get('points', [])
        
        if grid_size <= 0: return

        cam_x, cam_y = int(session.camera_x), int(session.camera_y)
        view_w, view_h = int(session.view_width), int(session.view_height)
        
        vx0 = max(0, -cam_x) * self.tile_size
        vy0 = max(0, -cam_y) * self.tile_size
        vx1 = min(view_w, session.map_obj.width - cam_x) * self.tile_size
        vy1 = min(view_h, session.map_obj.height - cam_y) * self.tile_size

        start_x = (cam_x // grid_size) * grid_size
        start_y = (cam_y // grid_size) * grid_size
        end_x = cam_x + view_w
        end_y = cam_y + view_h
        
        end_x = min(end_x, session.map_obj.width)
        end_y = min(end_y, session.map_obj.height)

        pixel_grid = grid_size * self.tile_size
        render_labels = show_coords and (pixel_grid > 20)

        for x in range(int(start_x), int(end_x) + 1, grid_size):
            if x < cam_x or x > end_x: continue
            px = (x - cam_x) * self.tile_size
            pygame.draw.line(self.screen, color, (int(px), int(vy0)), (int(px), int(vy1)), 2)
            if render_labels:
                 surf = self.font.render(f"X:{x}", True, color)
                 self.screen.blit(surf, (int(px) + 4, int(vy0) + 5))

        for y in range(int(start_y), int(end_y) + 1, grid_size):
            if y < cam_y or y > end_y: continue
            py = (y - cam_y) * self.tile_size
            pygame.draw.line(self.screen, color, (int(vx0), int(py)), (int(vx1), int(py)), 2)
            if render_labels:
                 surf = self.font.render(f"Y:{y}", True, color)
                 self.screen.blit(surf, (int(vx0) + 5, int(py) + 4))

        if points:
            last_p = None
            for p in points:
                px = (p[0] - cam_x) * self.tile_size + self.tile_size // 2
                py = (p[1] - cam_y) * self.tile_size + self.tile_size // 2
                
                if 0 <= px <= self.width and 0 <= py <= self.height:
                    pygame.draw.circle(self.screen, Colors.RED_LIGHT, (int(px), int(py)), 5)
                    
                    if last_p:
                        lpx = (last_p[0] - cam_x) * self.tile_size + self.tile_size // 2
                        lpy = (last_p[1] - cam_y) * self.tile_size + self.tile_size // 2
                        pygame.draw.line(self.screen, Colors.RED_LIGHT, (int(lpx), int(lpy)), (int(px), int(py)), 2)
                        
                        dist = get_distance(last_p, p)
                        mid_x, mid_y = (lpx + px) // 2, (lpy + py) // 2
                        if 0 <= mid_x <= self.width and 0 <= mid_y <= self.height:
                            d_surf = self.font.render(f"{dist:.1f}", True, Colors.RED_VERY_LIGHT)
                            self.screen.blit(d_surf, (int(mid_x), int(mid_y)))
                last_p = p

    def _draw_tool_preview(self, session):
        ts = session.tool_state
        if not ts.start_point: return

        sx, sy = ts.start_point
        cx, cy = session.cursor_x, session.cursor_y
        cam_x, cam_y = session.camera_x, session.camera_y
        
        points = []
        if ts.mode == 'rect' or ts.mode == 'select':
            points = get_rect_points(sx, sy, cx, cy, filled=False)
        elif ts.mode == 'line':
            points = get_line_points(sx, sy, cx, cy)
        elif ts.mode == 'circle':
            radius = int(get_distance((sx, sy), (cx, cy)))
            points = get_circle_points(sx, sy, radius, filled=False)
        
        color = Colors.YELLOW # Yellow for preview
        if ts.mode == 'select': color = Colors.BLUE_LIGHT # Blue for selection
        
        for px, py in points:
            if px < cam_x - 1 or py < cam_y - 1 or \
               px > cam_x + (self.width // self.tile_size) + 1 or \
               py > cam_y + (self.height // self.tile_size) + 1:
                continue

            scr_x = (px - cam_x) * self.tile_size
            scr_y = (py - cam_y) * self.tile_size
            
            pygame.draw.rect(self.screen, color, (scr_x, scr_y, self.tile_size, self.tile_size), 1)
