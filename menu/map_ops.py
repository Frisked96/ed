import os
from state_engine import State
from tiles import REGISTRY
from map_io import export_to_image
from menu.base import TextInputState, FormState

class NewMapState(FormState):
    def __init__(self, manager, context, view_width, view_height, callback):
        self.view_width = view_width
        self.view_height = view_height
        fields = [
            ["Width", str(view_width), "width"],
            ["Height", str(view_height), "height"],
            ["Border", "#", "border"]
        ]
        
        def on_submit(res):
            if not res:
                callback(None)
                return
            
            from core import Map
            try:
                w = max(self.view_width, int(res["width"]))
                h = max(self.view_height, int(res["height"]))
                map_obj = Map(w, h)
                border_char = res["border"][0] if res["border"] and res["border"] != "." else None
                if border_char:
                    tid = REGISTRY.get_by_char(border_char)
                    if tid:
                        for x in range(w):
                            map_obj.set(x, 0, tid); map_obj.set(x, h-1, tid)
                        for y in range(h):
                            map_obj.set(0, y, tid); map_obj.set(w-1, y, tid)
                
                callback(map_obj)
            except Exception as e:
                print(f"Error creating map: {e}")
                callback(None)

        super().__init__(manager, context, "NEW MAP SETTINGS", fields, on_submit)

class LoadMapState(State):
    def __init__(self, manager, context, view_width, view_height, callback):
        super().__init__(manager)
        self.context = context
        self.view_width = view_width
        self.view_height = view_height
        self.callback = callback

    def enter(self, **kwargs):
        def on_filename(filename):
            if filename and os.path.exists(filename):
                from core import Map
                try:
                    with open(filename, "r") as f:
                        lines = [line.rstrip("\n") for line in f]
                    if lines:
                        w = max(len(l) for l in lines); h = len(lines)
                        w = max(w, self.view_width); h = max(h, self.view_height)
                        m = Map(w, h)
                        for y, line in enumerate(lines):
                            for x, ch in enumerate(line):
                                m.set(x, y, REGISTRY.get_by_char(ch))
                        self.callback(m)
                        return
                except: pass
            self.callback(None)

        self.manager.push(TextInputState(self.manager, self.context, "Load map from: ", on_filename))

    def draw(self, surface):
        pass

class ExportMapState(State):
    def __init__(self, manager, context, map_obj):
        super().__init__(manager)
        self.context = context
        self.map_obj = map_obj

    def enter(self, **kwargs):
        def on_filename(filename):
            if not filename:
                return
            
            if not filename.endswith('.png') and not filename.endswith('.csv'):
                filename += '.png'

            if filename.endswith('.png'):
                def on_ts(ts_in):
                    tile_size = int(ts_in) if ts_in else 8
                    try:
                        export_to_image(self.map_obj.data, {}, filename, tile_size)
                    except Exception as e: print(e)
                self.manager.push(TextInputState(self.manager, self.context, "Tile size (default 8): ", on_ts))
            elif filename.endswith('.csv'):
                try:
                    with open(filename, 'w') as f:
                        for row in self.map_obj.data:
                            f.write(','.join(map(str, row)) + '\n')
                except Exception as e: print(e)
        
        self.manager.push(TextInputState(self.manager, self.context, "Export as (.png/.csv): ", on_filename))

    def draw(self, surface):
        pass

class ResizeMapState(FormState):
    def __init__(self, manager, context, map_obj, view_width, view_height, callback):
        self.view_width = view_width
        self.view_height = view_height
        self.map_obj = map_obj
        fields = [
            ["Width", str(map_obj.width), "width"],
            ["Height", str(map_obj.height), "height"]
        ]

        def on_submit(res):
            if not res:
                callback(None)
                return
            
            from core import Map
            try:
                w = max(self.view_width, int(res["width"]))
                h = max(self.view_height, int(res["height"]))
                new_map = Map(w, h)
                copy_h = min(h, self.map_obj.height)
                copy_w = min(w, self.map_obj.width)
                new_map.data[:copy_h, :copy_w] = self.map_obj.data[:copy_h, :copy_w]
                new_map.undo_stack = self.map_obj.undo_stack
                
                callback(new_map)
            except Exception as e:
                print(f"Error resizing map: {e}")
                callback(None)

        super().__init__(manager, context, "RESIZE MAP", fields, on_submit)



def menu_save_map(context, map_obj, filename=None):
    if filename:
        from map_io import autosave_map as io_save
        return io_save(map_obj, filename)
    
    def on_filename(fname):
        if fname:
            from map_io import autosave_map as io_save
            io_save(map_obj, fname)
            map_obj.dirty = False
    context.manager.push(TextInputState(context.manager, context, "Save map as: ", on_filename))
    return True

def menu_resize_map(context, map_obj, view_width, view_height, callback):
    context.manager.push(ResizeMapState(context.manager, context, map_obj, view_width, view_height, callback))
