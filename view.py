import pygame
import sys
from utils import get_key_name, get_distance
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
        self.draw_notifications()

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

    def draw_help_overlay(self, bindings):
        help_sections = [
            ("MOVEMENT", [
                f"View: {get_key_name(bindings.get('move_view_up'))}/{get_key_name(bindings.get('move_view_down'))}/{get_key_name(bindings.get('move_view_left'))}/{get_key_name(bindings.get('move_view_right'))}",
                f"Cursor: Arrow Keys"
            ]),
            ("DRAWING TOOLS", [
                f"{get_key_name(bindings.get('place_tile'))}=Place tile | {get_key_name(bindings.get('cycle_tile'))}=Cycle tiles | {get_key_name(bindings.get('pick_tile'))}=Pick from menu",
                f"{get_key_name(bindings.get('toggle_palette', 9))}=Quick Tile Palette",
                f"{get_key_name(bindings.get('flood_fill'))}=Flood fill | {get_key_name(bindings.get('line_tool'))}=Line | {get_key_name(bindings.get('rect_tool'))}=Rectangle",
                f"{get_key_name(bindings.get('circle_tool'))}=Circle | {get_key_name(bindings.get('pattern_tool'))}=Pattern mode",
                f"Brush: {get_key_name(bindings.get('decrease_brush'))}/{get_key_name(bindings.get('increase_brush'))} (Size) | {get_key_name(bindings.get('define_brush'))}=Define shape",
                f"Patterns: {get_key_name(bindings.get('define_pattern'))}=Define pattern"
            ]),
            ("SELECTION & CLIPBOARD", [
                f"{get_key_name(bindings.get('select_start'))}=Start/End selection | {get_key_name(bindings.get('clear_selection'))}=Clear",
                f"{get_key_name(bindings.get('copy_selection'))}=Copy | {get_key_name(bindings.get('paste_selection'))}=Paste",
                f"{get_key_name(bindings.get('clear_area'))}=Clear selected area"
            ]),
            ("EDIT OPERATIONS", [
                f"{get_key_name(bindings.get('undo'))}=Undo | {get_key_name(bindings.get('redo'))}=Redo",
                f"{get_key_name(bindings.get('replace_all'))}=Replace all tiles | {get_key_name(bindings.get('statistics'))}=Show statistics"
            ]),
            ("MAP TRANSFORMATIONS", [
                f"{get_key_name(bindings.get('map_rotate'))}=Rotate map 90° | {get_key_name(bindings.get('map_flip_h'))}=Flip H | {get_key_name(bindings.get('map_flip_v'))}=Flip V",
                f"Shift Map: Arrows (while in shift mode/config keys) to shift content"
            ]),
            ("PROCEDURAL GENERATION", [
                f"{get_key_name(bindings.get('random_gen'))}=Cellular Cave | {get_key_name(bindings.get('perlin_noise'))}=Perlin Noise",
                f"{get_key_name(bindings.get('voronoi'))}=Voronoi regions | {get_key_name(bindings.get('set_seed'))}=Set random seed"
            ]),
            ("FILE OPERATIONS", [
                f"{get_key_name(bindings.get('new_map'))}=New map | {get_key_name(bindings.get('load_map'))}=Load | {get_key_name(bindings.get('save_map'))}=Save",
                f"{get_key_name(bindings.get('resize_map'))}=Resize map | {get_key_name(bindings.get('export_image'))}=Export PNG/CSV"
            ]),
            ("MACROS & AUTOMATION", [
                f"{get_key_name(bindings.get('macro_record_toggle'))}=Toggle Macro Record | {get_key_name(bindings.get('macro_play'))}=Play Macro",
                f"{get_key_name(bindings.get('toggle_autotile'))}=Toggle Auto-Tiling"
            ]),
            ("SYSTEM", [
                f"{get_key_name(bindings.get('toggle_snap'))}=Set Snap | {get_key_name(bindings.get('set_measure'))}=Measure Dist",
                f"{get_key_name(bindings.get('editor_menu'))}=Pause Menu (F1) | {get_key_name(bindings.get('quit'))}=Quit Editor",
                f"{get_key_name(bindings.get('show_help'))}=Toggle Help (?)"
            ])
        ]
        
        all_lines = ["=== HELP (ESC to close) ==="]
        all_lines.append("Macros: Record actions and play them back. Useful for repetitive tasks.")
        all_lines.append("Auto-Tiling: Automatically picks tile variants based on neighbors.")
        all_lines.append("")
        for section, lines in help_sections:
            all_lines.append(f"--- {section} ---")
            all_lines.extend(lines)
            all_lines.append("")

        overlay_w, overlay_h = self.width - 100, self.height - 100
        ox, oy = 50, 50
        line_h = self.tile_size + 2
        max_lines = (overlay_h - 20) // line_h
        scroll = 0

        while True:
            pygame.draw.rect(self.screen, (30, 30, 30), (ox, oy, overlay_w, overlay_h))
            pygame.draw.rect(self.screen, (200, 200, 200), (ox, oy, overlay_w, overlay_h), 2)

            for i in range(max_lines):
                idx = scroll + i
                if idx < len(all_lines):
                    surf = self.font.render(all_lines[idx], True, (255, 255, 255))
                    self.screen.blit(surf, (ox + 10, oy + 10 + i * line_h))
            
            pygame.display.flip()
            event = pygame.event.wait()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: break
                elif event.key == pygame.K_UP: scroll = max(0, scroll - 1)
                elif event.key == pygame.K_DOWN: scroll = min(len(all_lines) - max_lines, scroll + 1)
            elif event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

