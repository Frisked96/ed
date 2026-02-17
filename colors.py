import os
import json

class Colors:
    """Central registry for colors, loaded from colors.json."""
    _colors = {}

    @classmethod
    def load(cls):
        # Default fallback colors
        cls._colors = {
            'black': (0, 0, 0),
            'white': (255, 255, 255),
            'red': (255, 0, 0),
            'green': (0, 255, 0),
            'blue': (0, 0, 255),
            'yellow': (255, 255, 0),
            'magenta': (255, 0, 255),
            'cyan': (0, 255, 255),
            'gray': (128, 128, 128),
            'darkgray': (64, 64, 64),
            'lightgray': (192, 192, 192),
            'red_light': (255, 100, 100),
            'red_very_light': (255, 200, 200),
            'blue_light': (100, 100, 255),
        }
        
        colors_path = os.path.join(os.getcwd(), 'colors.json')
        if os.path.exists(colors_path):
            try:
                with open(colors_path, 'r') as f:
                    loaded = json.load(f)
                    for name, val in loaded.items():
                        cls._colors[name.lower()] = tuple(val)
            except:
                pass
        
        # Add attributes for direct access: Colors.WHITE, Colors.BLACK, etc.
        for name, val in cls._colors.items():
            setattr(cls, name.upper(), val)

    @classmethod
    def get(cls, name, default=(255, 255, 255)):
        if not isinstance(name, str):
            return name
        return cls._colors.get(name.lower(), default)

    @classmethod
    def all(cls):
        return dict(cls._colors)

# Initialize on import
Colors.load()
