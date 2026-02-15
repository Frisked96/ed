import sys
import pygame
from view import Renderer
from state_engine import StateManager
from tiles import init_default_tiles
from menu_state import MainMenuState

def main():
    # 1. Initialize Pygame and Tiles
    pygame.init()
    init_default_tiles()
    
    # 2. Setup Display
    display_info = pygame.display.Info()
    width = int(display_info.current_w * 0.9)
    height = int(display_info.current_h * 0.8)
    screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
    pygame.display.set_caption("Advanced Map Editor")
    pygame.key.set_repeat(300, 50)
    
    # 3. Setup Renderer & State Manager
    renderer = Renderer(screen)
    state_manager = StateManager(screen)
    
    # 4. Setup Centralized Flow Controller
    from flow import AppFlow
    flow = AppFlow(state_manager, renderer)
    state_manager.flow = flow
    
    # 5. Run loop
    state_manager.run(renderer)

if __name__ == '__main__':
    main()
