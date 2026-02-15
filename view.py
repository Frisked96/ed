import pygame
import sys
import time
from utils import get_key_name, get_distance
from drawing import get_line_points, get_rect_points, get_circle_points
from tiles import REGISTRY
from core import COLOR_MAP

class Renderer:
    def __init__(self, width=None, height=None, tile_size=20):
        pygame.init()
        self.tile_size = tile_size
        
        # Get display info for intelligent defaults
        display_info = pygame.display.Info()
        screen_w = display_info.current_w
        screen_h = display_info.current_h
        
        # Use provided dimensions or sensible defaults that fit the screen
        self.width = width if width is not None else int(screen_w * 0.9)
        self.height = height if height is not None else int(screen_h * 0.8)
        
        self.screen = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        pygame.display.set_caption("Advanced Map Editor")
        
        self.manager = None # Set by Main
        self.font_size = 20
        try:
            self.font = pygame.font.SysFont("Courier New", self.font_size, bold=True)
            if not self.font:
                self.font = pygame.font.SysFont("monospace", self.font_size, bold=True)
        except:
            self.font = pygame.font.Font(None, self.font_size)
            
        self.clock = pygame.time.Clock()
        self.glyph_cache = {}
        self.chunk_cache = {} # (chunk_x, chunk_y) -> Surface
        self.chunk_size = 32
        self.notifications = [] # List of (text, expiry_time, color)
        pygame.key.set_repeat(300, 50)
        
        # Subscribe to tile changes
        REGISTRY.subscribe(self.invalidate_cache)

    def invalidate_cache(self):
        self.glyph_cache = {}
        self.chunk_cache = {}

    def invalidate_chunk(self, map_x, map_y):
        cx = map_x // self.chunk_size
        cy = map_y // self.chunk_size
        if (cx, cy) in self.chunk_cache:
            del self.chunk_cache[(cx, cy)]

    def add_notification(self, text, duration=2.0, color=(0, 255, 0)):
        self.notifications.append({
            "text": text,
            "expiry": time.time() + duration,
            "color": color,
            "start": duration
        })

    def draw_notifications(self):
        now = time.time()
        # Filter out expired ones
        self.notifications = [n for n in self.notifications if n["expiry"] > now]
        
        y = 10
        for n in self.notifications:
            time_left = n["expiry"] - now
            alpha = int(min(1.0, time_left / 0.5) * 255) # Fade out in last 0.5s
            
            surf = self.font.render(n["text"], True, n["color"])
            self.screen.blit(surf, (self.width - surf.get_width() - 10, y))
            y += surf.get_height() + 5

    def get_glyph(self, tile_id, bg_color=None):
        # Optimized lookup
        key = (tile_id, bg_color)
        if key in self.glyph_cache:
            return self.glyph_cache[key]

        tile_def = REGISTRY.get(tile_id)
        if not tile_def:
            return None
        
        char = tile_def.char
        
        # Handle color parsing
        color_val = tile_def.color
        if isinstance(color_val, str):
            color = COLOR_MAP.get(color_val.lower(), (255, 255, 255))
        else:
            color = color_val

        surf = self.font.render(char, True, color, bg_color)
        self.glyph_cache[key] = surf
        return surf

    def clear(self):
        self.screen.fill((0, 0, 0))

    def flip(self):
        pygame.display.flip()
        self.clock.tick(60)

    def update_dimensions(self):
        w, h = self.screen.get_size()
        self.width, self.height = w, h

    def _render_chunk(self, session, cx, cy):
        ts = self.tile_size
        surf = pygame.Surface((self.chunk_size * ts, self.chunk_size * ts))
        surf.fill((0, 0, 0))
        
        start_x = cx * self.chunk_size
        start_y = cy * self.chunk_size
        
        # Get slice of map data
        data = session.map_obj.data[start_y : start_y + self.chunk_size, start_x : start_x + self.chunk_size]
        
        for y_rel, row in enumerate(data):
            py = y_rel * ts
            for x_rel, tid in enumerate(row):
                px = x_rel * ts
                glyph = self.get_glyph(tid)
                if glyph:
                    surf.blit(glyph, (px, py))
        
        return surf

    def draw_map(self, session):
        # Clear the whole screen first to ensure no bleeding behind status bar
        self.screen.fill((0, 0, 0))
        
        # Set clipping to viewport
        viewport_rect = pygame.Rect(0, 0, session.viewport_px_w, session.viewport_px_h)
        self.screen.set_clip(viewport_rect)
        
        map_data = session.map_obj.data
        cam_x, cam_y = session.camera_x, session.camera_y
        view_w = session.view_width
        view_h = session.view_height
        tile_size = self.tile_size
        tool_state = session.tool_state
        
        # 1. Determine visible chunks
        # Use floor/ceil to ensure we cover every visible pixel
        start_cx = int(cam_x // self.chunk_size)
        start_cy = int(cam_y // self.chunk_size)
        
        # Calculate how many chunks are needed to cover the view width/height
        # Adding 1 or 2 as a buffer to avoid "rendering in" artifacts at edges
        end_cx = int((cam_x + view_w + 1) // self.chunk_size)
        end_cy = int((cam_y + view_h + 1) // self.chunk_size)
        
        # 2. Draw visible chunks
        for cy in range(start_cy, end_cy + 1):
            if cy < 0 or cy * self.chunk_size >= session.map_obj.height: continue
            for cx in range(start_cx, end_cx + 1):
                if cx < 0 or cx * self.chunk_size >= session.map_obj.width: continue
                
                if (cx, cy) not in self.chunk_cache:
                    self.chunk_cache[(cx, cy)] = self._render_chunk(session, cx, cy)
                
                chunk_surf = self.chunk_cache[(cx, cy)]
                px = (cx * self.chunk_size - cam_x) * tile_size
                py = (cy * self.chunk_size - cam_y) * tile_size
                self.screen.blit(chunk_surf, (px, py))

        # Clipping bounds for overlays (UI area check)
        # We don't want to draw map overlays over the status bar
        
        # Pre-calculate viewport bounds within the map for overlays
        start_vx = max(0, -cam_x)
        start_vy = max(0, -cam_y)
        end_vx = min(view_w, session.map_obj.width - cam_x)
        end_vy = min(view_h, session.map_obj.height - cam_y)

        # Selection highlight
        if session.selection_start:
            x0, y0 = session.selection_start
            # Use cursor for end point if selection is in progress
            x1, y1 = session.selection_end if session.selection_end else (session.cursor_x, session.cursor_y)
            
            sx0, sx1 = (x0, x1) if x0 < x1 else (x1, x0)
            sy0, sy1 = (y0, y1) if y0 < y1 else (y1, y0)
            
            # Intersection of selection and viewport
            ix0 = max(sx0, cam_x + start_vx)
            iy0 = max(sy0, cam_y + start_vy)
            ix1 = min(sx1, cam_x + end_vx - 1)
            iy1 = min(sy1, cam_y + end_vy - 1)
            
            if ix0 <= ix1 and iy0 <= iy1:
                sel_px = (ix0 - cam_x) * tile_size
                sel_py = (iy0 - cam_y) * tile_size
                sel_pw = (ix1 - ix0 + 1) * tile_size
                sel_ph = (iy1 - iy0 + 1) * tile_size
                
                # Draw filled rect and border
                color = (60, 60, 120) if session.selection_end else (60, 60, 180, 100)
                # Use surface for alpha if needed, or just solid
                pygame.draw.rect(self.screen, color, (sel_px, sel_py, sel_pw, sel_ph))
                pygame.draw.rect(self.screen, (100, 100, 255), (sel_px, sel_py, sel_pw, sel_ph), 2)

        # Brush bounds for ghosting
        br = tool_state.brush_size
        offset = br // 2
        bx0, by0 = session.cursor_x - offset, session.cursor_y - offset
        bx1, by1 = bx0 + br - 1, by0 + br - 1
        
        # Intersection of brush and viewport
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
            
            # Bright cursor center
            if ibx0 <= session.cursor_x <= ibx1 and iby0 <= session.cursor_y <= iby1:
                c_px = (session.cursor_x - cam_x) * tile_size
                c_py = (session.cursor_y - cam_y) * tile_size
                pygame.draw.rect(self.screen, (200, 200, 200), (c_px, c_py, tile_size, tile_size))

        self._draw_tool_preview(session)
        self._draw_measurement_overlay(session)
        
        # Reset clipping for UI elements
        self.screen.set_clip(None)
        
        session.status_y = self.height - 110
        self.draw_notifications()

    def _draw_measurement_overlay(self, session):
        if not session.tool_state.measurement_active: return
        
        cfg = session.tool_state.measurement_config
        grid_size = int(cfg.get('grid_size', 100))
        show_coords = cfg.get('show_coords', True)
        color = cfg.get('color', (0, 255, 255))
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

        # Performance guard: Don't render too many labels
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
                
                if 0 <= px <= self.width and 0 <= py <= self.height - 120:
                    pygame.draw.circle(self.screen, (255, 100, 100), (int(px), int(py)), 5)
                    
                    if last_p:
                        lpx = (last_p[0] - cam_x) * self.tile_size + self.tile_size // 2
                        lpy = (last_p[1] - cam_y) * self.tile_size + self.tile_size // 2
                        pygame.draw.line(self.screen, (255, 100, 100), (int(lpx), int(lpy)), (int(px), int(py)), 2)
                        
                        dist = get_distance(last_p, p)
                        mid_x, mid_y = (lpx + px) // 2, (lpy + py) // 2
                        if 0 <= mid_x <= self.width and 0 <= mid_y <= self.height - 120:
                            d_surf = self.font.render(f"{dist:.1f}", True, (255, 200, 200))
                            self.screen.blit(d_surf, (int(mid_x), int(mid_y)))
                last_p = p

        # Live Sector Info
        sec_x = session.cursor_x // grid_size
        sec_y = session.cursor_y // grid_size
        rel_x = session.cursor_x % grid_size
        rel_y = session.cursor_y % grid_size
        
        info_lines = [
            f"SECTOR: {sec_x}, {sec_y}",
            f"LOCAL:  {rel_x}, {rel_y}",
            f"TOTAL:  {session.cursor_x}, {session.cursor_y}"
        ]
        
        y_off = self.height - 180
        for line in info_lines:
            surf = self.font.render(line, True, color)
            self.screen.blit(surf, (self.width - surf.get_width() - 10, y_off))
            y_off += 22

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
        
        color = (255, 255, 0) # Yellow for preview
        if ts.mode == 'select': color = (100, 100, 255) # Blue for selection
        
        # Draw each point as a tile highlight
        for px, py in points:
            # Simple bounds check to avoid drawing off-screen too much
            # (Pygame handles off-screen drawing, but no need to process huge lists if way off)
            if px < cam_x - 1 or py < cam_y - 1 or \
               px > cam_x + (self.width // self.tile_size) + 1 or \
               py > cam_y + (self.height // self.tile_size) + 1:
                continue

            scr_x = (px - cam_x) * self.tile_size
            scr_y = (py - cam_y) * self.tile_size
            
            # Draw a hollow square for the tile
            pygame.draw.rect(self.screen, color, (scr_x, scr_y, self.tile_size, self.tile_size), 1)

    def draw_status(self, session):
        y_base = session.status_y + 10
        ts = session.tool_state
        
        # 1. Active Tile Preview Box
        preview_rect = (10, y_base, 60, 60)
        pygame.draw.rect(self.screen, (30, 30, 30), preview_rect)
        pygame.draw.rect(self.screen, (150, 150, 150), preview_rect, 1)
        
        sel_tile = REGISTRY.get(session.selected_tile_id)
        if sel_tile:
            # Draw a larger version of the tile character
            big_font = pygame.font.SysFont("Courier New", 40, bold=True)
            char_surf = big_font.render(sel_tile.char, True, 
                                        COLOR_MAP.get(sel_tile.color.lower(), (255, 255, 255)) 
                                        if isinstance(sel_tile.color, str) else sel_tile.color)
            self.screen.blit(char_surf, (preview_rect[0] + 15, preview_rect[1] + 5))
            
            name_surf = self.font.render(sel_tile.name[:10], True, (150, 150, 150))
            self.screen.blit(name_surf, (preview_rect[0], preview_rect[1] + 65))

        # 2. Detailed Info Columns
        col1_x = 85
        col2_x = 350
        col3_x = 650

        # Column 1: Mode and Position
        mode_display = ts.mode.upper()
        if ts.recording: mode_display += " (REC)"
        
        lines_c1 = [
            f"MODE:   {mode_display}",
            f"CURSOR: {session.cursor_x}, {session.cursor_y}",
            f"CAMERA: {session.camera_x}, {session.camera_y}"
        ]

        # Column 2: Tools Settings
        lines_c2 = [
            f"BRUSH:     {ts.brush_size}x{ts.brush_size} {'(Custom)' if ts.brush_shape else ''}",
            f"AUTO-TILE: {'ENABLED' if ts.auto_tiling else 'DISABLED'}",
            f"SNAP:      {'ON' if ts.snap_size > 1 else 'OFF'} ({ts.snap_size})"
        ]

        # Column 3: Stats & Quick Keys
        lines_c3 = [
            f"MAP:  {session.map_obj.width}x{session.map_obj.height}",
            f"UNDO: {session.undo_stack.undo_count} / REDO: {session.undo_stack.redo_count}",
            "[F1] Menu | [?] Help | [Q] Quit"
        ]

        for i, line in enumerate(lines_c1):
            self.screen.blit(self.font.render(line, True, (255, 255, 255)), (col1_x, y_base + i * 22))
        for i, line in enumerate(lines_c2):
            self.screen.blit(self.font.render(line, True, (200, 200, 255) if "ENABLED" in line or "ON" in line else (200, 200, 200)), (col2_x, y_base + i * 22))
        for i, line in enumerate(lines_c3):
            self.screen.blit(self.font.render(line, True, (200, 255, 200)), (col3_x, y_base + i * 22))

    def draw_palette(self, session):
        if not session.tool_state.show_palette: return None

        all_tiles = list(REGISTRY.get_all())
        if not all_tiles: return None
        
        # Layout
        cols = 5
        tile_spacing = 35
        # Calculate height based on rows
        rows = (len(all_tiles) + cols - 1) // cols
        palette_w = cols * tile_spacing + 30
        palette_h = rows * tile_spacing + 60
        palette_h = min(palette_h, self.height - 100) # Cap height
        
        x_base = self.width - palette_w - 20
        y_base = 60 # Below top bar/status
        
        # Background
        s = pygame.Surface((palette_w, palette_h), pygame.SRCALPHA)
        s.fill((30, 30, 30, 230))
        self.screen.blit(s, (x_base, y_base))
        pygame.draw.rect(self.screen, (200, 200, 200), (x_base, y_base, palette_w, palette_h), 2)
        
        # Title
        title = self.font.render("PALETTE", True, (255, 255, 0))
        self.screen.blit(title, (x_base + (palette_w - title.get_width())//2, y_base + 10))
        
        clickable_rects = []
        
        start_x = x_base + 15
        start_y = y_base + 40
        
        for i, tile in enumerate(all_tiles):
            c = i % cols
            r = i // cols
            
            px = start_x + c * tile_spacing
            py = start_y + r * tile_spacing
            
            if py + tile_spacing > y_base + palette_h: break
            
            rect = pygame.Rect(px, py, self.tile_size, self.tile_size)
            clickable_rects.append((rect, tile.id))
            
            # Highlight selected
            if tile.id == session.selected_tile_id:
                pygame.draw.rect(self.screen, (255, 255, 0), (px-2, py-2, self.tile_size+4, self.tile_size+4), 2)
            
            glyph = self.get_glyph(tile.id)
            if glyph:
                self.screen.blit(glyph, (px, py))
                
        return pygame.Rect(x_base, y_base, palette_w, palette_h), clickable_rects

