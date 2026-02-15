import pygame
import sys
from utils import get_key_name, get_distance
from drawing import get_line_points, get_rect_points, get_circle_points
from tiles import REGISTRY
from core import COLOR_MAP

class Renderer:
    def __init__(self, width=1200, height=800, tile_size=20):
        pygame.init()
        self.tile_size = tile_size
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
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
        self.notifications = [] # List of (text, expiry_time, color)
        pygame.key.set_repeat(300, 50)
        
        # Subscribe to tile changes
        REGISTRY.subscribe(self.invalidate_cache)

    def add_notification(self, text, duration=2.0, color=(0, 255, 0)):
        import time
        self.notifications.append({
            "text": text,
            "expiry": time.time() + duration,
            "color": color,
            "start": duration
        })

    def draw_notifications(self):
        import time
        now = time.time()
        # Filter out expired ones
        self.notifications = [n for n in self.notifications if n["expiry"] > now]
        
        y = 10
        for n in self.notifications:
            time_left = n["expiry"] - now
            alpha = int(min(1.0, time_left / 0.5) * 255) # Fade out in last 0.5s
            
            surf = self.font.render(n["text"], True, n["color"])
            # Pygame doesn't easily do alpha on rendered text without a temporary surface
            # but we can at least draw them
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

    def draw_map(self, session):
        map_data = session.map_obj.data
        cam_x, cam_y = session.camera_x, session.camera_y
        view_w = session.view_width
        view_h = session.view_height
        ts = session.tool_state
        
        # Pre-calculate viewport bounds within the map
        start_vx = max(0, -cam_x)
        start_vy = max(0, -cam_y)
        end_vx = min(view_w, session.map_obj.width - cam_x)
        end_vy = min(view_h, session.map_obj.height - cam_y)

        # Selection highlight
        if session.selection_start and session.selection_end:
            x0, y0 = session.selection_start
            x1, y1 = session.selection_end
            sx0, sx1 = (x0, x1) if x0 < x1 else (x1, x0)
            sy0, sy1 = (y0, y1) if y0 < y1 else (y1, y0)
            
            # Intersection of selection and viewport
            ix0 = max(sx0, cam_x + start_vx)
            iy0 = max(sy0, cam_y + start_vy)
            ix1 = min(sx1, cam_x + end_vx - 1)
            iy1 = min(sy1, cam_y + end_vy - 1)
            
            if ix0 <= ix1 and iy0 <= iy1:
                sel_px = (ix0 - cam_x) * self.tile_size
                sel_py = (iy0 - cam_y) * self.tile_size
                sel_pw = (ix1 - ix0 + 1) * self.tile_size
                sel_ph = (iy1 - iy0 + 1) * self.tile_size
                pygame.draw.rect(self.screen, (60, 60, 120), (sel_px, sel_py, sel_pw, sel_ph))

        # Brush bounds for ghosting
        br = ts.brush_size
        offset = br // 2
        bx0, by0 = session.cursor_x - offset, session.cursor_y - offset
        bx1, by1 = bx0 + br - 1, by0 + br - 1
        
        # Intersection of brush and viewport
        ibx0 = max(bx0, cam_x + start_vx)
        iby0 = max(by0, cam_y + start_vy)
        ibx1 = min(bx1, cam_x + end_vx - 1)
        iby1 = min(by1, cam_y + end_vy - 1)

        if ibx0 <= ibx1 and iby0 <= iby1:
            b_px = (ibx0 - cam_x) * self.tile_size
            b_py = (iby0 - cam_y) * self.tile_size
            b_pw = (ibx1 - ibx0 + 1) * self.tile_size
            b_ph = (iby1 - iby0 + 1) * self.tile_size
            pygame.draw.rect(self.screen, (100, 100, 100), (b_px, b_py, b_pw, b_ph))
            
            # Bright cursor center
            if ibx0 <= session.cursor_x <= ibx1 and iby0 <= session.cursor_y <= iby1:
                c_px = (session.cursor_x - cam_x) * self.tile_size
                c_py = (session.cursor_y - cam_y) * self.tile_size
                pygame.draw.rect(self.screen, (200, 200, 200), (c_px, c_py, self.tile_size, self.tile_size))

        # Draw actual tiles
        # We can further optimize by fetching the sub-array once
        visible_data = map_data[cam_y + start_vy : cam_y + end_vy, cam_x + start_vx : cam_x + end_vx]
        
        for vy_rel, row in enumerate(visible_data):
            py = (start_vy + vy_rel) * self.tile_size
            if py >= self.height: break
            for vx_rel, tid in enumerate(row):
                px = (start_vx + vx_rel) * self.tile_size
                if px >= self.width: break
                glyph = self.get_glyph(tid)
                if glyph:
                    self.screen.blit(glyph, (px, py))
        
        session.status_y = view_h * self.tile_size
        self._draw_tool_preview(session)
        self.draw_notifications()

    def _draw_tool_preview(self, session):
        ts = session.tool_state
        if not ts.start_point: return

        sx, sy = ts.start_point
        cx, cy = session.cursor_x, session.cursor_y
        cam_x, cam_y = session.camera_x, session.camera_y
        
        points = []
        if ts.mode == 'rect':
            points = get_rect_points(sx, sy, cx, cy, filled=False)
        elif ts.mode == 'line':
            points = get_line_points(sx, sy, cx, cy)
        elif ts.mode == 'circle':
            radius = int(get_distance((sx, sy), (cx, cy)))
            points = get_circle_points(sx, sy, radius, filled=False)
        
        color = (255, 255, 0) # Yellow for preview
        
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

    def invalidate_cache(self):
        self.glyph_cache = {}

