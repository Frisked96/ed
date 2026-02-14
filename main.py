import sys
from view import Renderer
from state_engine import StateManager
from tiles import init_default_tiles
from menu_state import MainMenuState

def main():
    # 1. Initialize Tiles
    init_default_tiles()
    
    # 2. Setup Renderer & State Manager
    renderer = Renderer()
    state_manager = StateManager(renderer.screen)
    
    # 3. Push Main Menu State
    menu_state = MainMenuState(state_manager, renderer)
    state_manager.push(menu_state)
    
    # 4. Run loop
    state_manager.run()

if __name__ == '__main__':
    main()
