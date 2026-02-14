import curses
from core import COLOR_MAP

def parse_color_name(name):
    return COLOR_MAP.get(name.lower(), curses.COLOR_WHITE)

def get_key_name(key):
    if key == ord(' '): return 'SPACE'
    elif key == 27: return 'ESC'
    elif key == 127 or key == curses.KEY_BACKSPACE: return 'BKSP'
    else:
        try:
            name = curses.keyname(key)
            if name:
                decoded = name.decode('utf-8', 'ignore').upper()
                if decoded.startswith('KEY_'):
                    decoded = decoded[4:]
                return decoded
        except: pass
        if 32 <= key <= 126: return chr(key).upper()
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

def get_user_input(stdscr, y, x, prompt, echo=True):
    if y is not None and x is not None:
        stdscr.addstr(y, x, prompt)
        stdscr.clrtoeol()
        stdscr.refresh()
    
    stdscr.timeout(-1)
    curses.flushinp()
    if echo:
        curses.echo()
        curses.curs_set(1)
    
    try:
        result = stdscr.getstr().decode().strip()
    except:
        result = ""
        
    if echo:
        curses.noecho()
        curses.curs_set(0)
    
    return result

def get_user_confirmation(stdscr, y, x, prompt):
    if y is not None and x is not None:
        stdscr.addstr(y, x, prompt)
        stdscr.clrtoeol()
        stdscr.refresh()
    
    stdscr.timeout(-1)
    key = stdscr.getch()
    # Timeout will be restored by the main loop in next iteration
    
    return key in (ord('y'), ord('Y'))
