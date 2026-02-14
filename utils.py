import pygame
import sys
from core import COLOR_MAP

def parse_color_name(name):
    # Returns an RGB tuple
    return COLOR_MAP.get(name.lower(), (255, 255, 255))

def get_key_name(key):
    # key is an integer code
    if key == 32: return 'SPACE'
    elif key == 27: return 'ESC'
    elif key == 8: return 'BKSP'
    elif key == 13: return 'ENTER'
    elif key == 9: return 'TAB'

    # Check Pygame constants
    try:
        name = pygame.key.name(key)
        if name and name != 'unknown key':
            return name.upper()
    except: pass

    # Check ASCII
    if 32 <= key <= 126:
        return chr(key)

    return f'KEY_{key}'

def get_distance(p1, p2):
    return ((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)**0.5

def rotate_selection_90(selection_data):
    if not selection_data: return None
    height = len(selection_data)
    width = len(selection_data[0])
    rotated = [['' for _ in range(height)] for _ in range(width)]
    for y in range(height):
        for x in range(width):
            rotated[x][height - 1 - y] = selection_data[y][x]
    return rotated

def flip_selection_horizontal(selection_data):
    if not selection_data: return None
    return [row[::-1] for row in selection_data]

def flip_selection_vertical(selection_data):
    if not selection_data: return None
    return selection_data[::-1]

def shift_map(map_data, dx, dy):
    height = len(map_data)
    width = len(map_data[0])
    new_map = [['' for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(width):
            new_map[(y + dy) % height][(x + dx) % width] = map_data[y][x]
    return new_map

def get_user_input(context, y, x, prompt, echo=True):
    # context is PygameContext
    screen = context.screen
    font = context.font
    clock = context.clock
    
    px = x * context.tile_size
    py = y * context.tile_size
    
    input_text = ""
    
    # Capture background to restore it each frame (optional, but good for cleanliness)
    # However, since we are in a loop, we might just want to draw a black box
    # mimicking the terminal behavior where the input line clears everything under it.

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    return input_text
                elif event.key == pygame.K_ESCAPE:
                    return ""
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    if event.unicode and event.unicode.isprintable():
                        input_text += event.unicode

        # Draw black box background for the input line
        rect_w = context.width - px
        rect_h = context.tile_size
        pygame.draw.rect(screen, (0, 0, 0), (px, py, rect_w, rect_h))

        # Render text
        text_surf = font.render(prompt + input_text + "_", True, (255, 255, 255))
        screen.blit(text_surf, (px, py))

        pygame.display.flip()
        clock.tick(30)

def get_user_confirmation(context, y, x, prompt):
    # context is PygameContext
    screen = context.screen
    font = context.font
    clock = context.clock

    px = x * context.tile_size
    py = y * context.tile_size

    # Initial draw
    rect_w = context.width - px
    rect_h = context.tile_size
    pygame.draw.rect(screen, (0, 0, 0), (px, py, rect_w, rect_h))
    
    text_surf = font.render(prompt, True, (255, 255, 255))
    screen.blit(text_surf, (px, py))
    pygame.display.flip()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_y:
                    return True
                elif event.key == pygame.K_n or event.key == pygame.K_ESCAPE:
                    return False
        clock.tick(10)
