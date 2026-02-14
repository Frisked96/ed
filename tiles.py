from typing import List, Optional, Dict, Any, Tuple, Union
from pydantic import BaseModel, Field
import pygame

class TileAnimation(BaseModel):
    frames: List[int]  # List of tile IDs (or indices if self-referential)
    frame_duration: float = 0.2
    loop: bool = True

class TileDefinition(BaseModel):
    id: int
    char: str
    name: str
    color: Union[str, Tuple[int, int, int]] = "white"
    bg_color: Optional[Union[str, Tuple[int, int, int]]] = None
    blocks_movement: bool = False
    blocks_sight: bool = False
    properties: Dict[str, Any] = Field(default_factory=dict)
    animation: Optional[TileAnimation] = None

class TileRegistry:
    def __init__(self):
        self._tiles: Dict[int, TileDefinition] = {}
        self._char_map: Dict[str, int] = {}
        self._next_id = 1  # 0 is usually reserved for "void" or "empty"
        self._subscribers = []

    def subscribe(self, callback):
        self._subscribers.append(callback)

    def _notify(self):
        for callback in self._subscribers:
            callback()

    def register(self, char: str, name: str, color="white", persist=True, **kwargs) -> int:
        if char in self._char_map:
             tid = self._char_map[char]
             self._tiles[tid] = TileDefinition(id=tid, char=char, name=name, color=color, **kwargs)
        else:
             tid = self._next_id
             self._next_id += 1
             tile = TileDefinition(id=tid, char=char, name=name, color=color, **kwargs)
             self._tiles[tid] = tile
             self._char_map[char] = tid
        
        if persist:
            self.save_to_disk()
        self._notify()
        return tid

    def save_to_disk(self):
        from map_io import save_tiles
        # Only persist non-default tiles or just persist all? 
        # For simplicity, we can save all tiles.
        tile_data = [t.model_dump() for t in self._tiles.values()]
        save_tiles(tile_data)

    def delete(self, tile_id: int):
        if tile_id in self._tiles:
            char = self._tiles[tile_id].char
            del self._tiles[tile_id]
            if char in self._char_map:
                del self._char_map[char]
            self.save_to_disk()
            self._notify()

    def update_tile(self, tile_id: int, name: Optional[str] = None, color: Optional[Union[str, Tuple[int, int, int]]] = None):
        if tile_id in self._tiles:
            if name is not None:
                self._tiles[tile_id].name = name
            if color is not None:
                self._tiles[tile_id].color = color
            self.save_to_disk()
            self._notify()

    def get(self, tile_id: int) -> Optional[TileDefinition]:
        return self._tiles.get(tile_id)

    def get_by_char(self, char: str) -> int:
        return self._char_map.get(char, 0)

    def get_all(self) -> List[TileDefinition]:
        return list(self._tiles.values())

# Global registry instance
REGISTRY = TileRegistry()

# Initialize defaults
def init_default_tiles():
    from map_io import load_tiles
    custom_tiles = load_tiles()
    
    # Track which chars we already have
    for t_data in custom_tiles:
        # Pydantic v2 uses model_validate
        tile = TileDefinition.model_validate(t_data)
        REGISTRY._tiles[tile.id] = tile
        REGISTRY._char_map[tile.char] = tile.id
        if tile.id >= REGISTRY._next_id:
            REGISTRY._next_id = tile.id + 1

    # Ensure essential defaults exist if not already loaded
    if '.' not in REGISTRY._char_map:
        REGISTRY.register('.', "Floor", color="darkgray", persist=False)
    if '#' not in REGISTRY._char_map:
        REGISTRY.register('#', "Wall", color="lightgray", blocks_movement=True, blocks_sight=True, persist=False)
    if '~' not in REGISTRY._char_map:
        REGISTRY.register('~', "Water", color="blue", properties={"liquid": True}, persist=False)
    if 'T' not in REGISTRY._char_map:
        REGISTRY.register('T', "Tree", color="green", blocks_movement=True, persist=False)
    if 'G' not in REGISTRY._char_map:
        REGISTRY.register('G', "Grass", color="green", persist=False)
