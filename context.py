# context.py
from __future__ import annotations
from dataclasses import dataclass, field
from functools import lru_cache
import pygame, random, json, os, inspect


LOG = True
endline = False
_z = ["<module>", "_call_with_frames_removed"]

def log(*args):
    if LOG:
        x = []
        if len(args) >= 3:
            from_where, method, text = args
            x = [f" | {from_where:<13}", "|", f"{method:<13}", "|", text]
        else:
            print(*args)
        if endline and x:
            stack = inspect.stack()
            caller = stack[1].function
            if caller not in _z:
                x.append(f"\n | CALLER        | {caller:<13} |")
                if len(stack) > 2:
                     origin = stack[2].function
                     if origin not in _z:
                         x.append(f"ORIGIN {origin} FROM {from_where}")
        print(*x)


def load_config(root=None, path="config.json"):
    try:
        x = path
        if root is not None:
            x = os.path.join(root, path)
        if not os.path.exists(x):
            log("System", "ERROR", f"couldn't find the path: {x}")
            return {}
        with open(x, "r", encoding="utf-8") as f:
            content = json.load(f)
            if not content:
                log("System", "ERRO", f"couldn't load anything from path: {x}")
                return {}
            log("System", "LOAD", f"settings loaded from path: {x}")
            return content
    except Exception as e:
        log("System", "ERROR", f"while loading settings: {e}")
        return {}


@lru_cache(maxsize=32)
def get_cached_sysfont(name, size, bold, italic):
    return pygame.font.SysFont(name, size, bold, italic)


@lru_cache(maxsize=128)
def calculate_bounded_size(size: tuple, msize: tuple) -> tuple:
    w, h = size
    max_w, max_h = msize
    if max_w is not None and w > max_w:
        w = max_w
    if max_h is not None and h > max_h:
        h = max_h
    return (w, h)



@dataclass(slots=True, eq=False)
class MovementHandler:
    enabled:    bool   = True
    debug:      bool   = True
    jumped:     bool   = False
    flying:     bool   = False

    _type:      str    = "<MovementHandler>"
    jumpkey:    int    = pygame.K_SPACE

    speed:      int    = 200
    topspeed:   int    = 200
    step:       int    = 25
    gravity:    int    = 1
    jumpforce:  int    = -20
    velocity_y: int    = 0
    velocity_x: int    = 0

    limit:      object = None # rect

    movset:     list   = field(default_factory=list)
    _base:      list   = field(default_factory=lambda: [pygame.K_w, pygame.K_a, pygame.K_s, pygame.K_d])


    def setup_movset(self, custom_keys: list = None):
        base = custom_keys if custom_keys else self._base
        self.movset = []
        for i in base:
            if isinstance(i, str):
                key_val = getattr(pygame, f"K_{i.lower()}", None)
                if key_val is None:
                    log("Movset", "WARN", f"key: {i} is not a valid key!")
                    continue
                self.movset.append(key_val)
            else:
                self.movset.append(i)
        log("Movset", "ADD", f"Movement keys configured successfully ({len(self.movset)} keys)")


    def update(self, ui_handler, dt, limits=None, margin=2):
        if self.jumpforce >= 0:
            self.flying = True

        if not self.enabled or not self.movset:
            return

        dx = 0
        dy = 0
        key = pygame.key.get_pressed()

        if len(self.movset) >= 4:
            if key[self.movset[0]]: dy = -1  # Cima
            if key[self.movset[1]]: dx = -1  # Esquerda
            if key[self.movset[2]]: dy = 1   # Baixo
            if key[self.movset[3]]: dx = 1   # Direita

        if not self.flying:
            if self.gravity > 0:
                self.velocity_y += self.gravity * dt * 60 
                if key[self.jumpkey] and not self.jumped:
                    self.velocity_y = self.jumpforce
                    self.jumped = True

        z = pygame.math.Vector2(dx, 0)
        if z.length() > 0:
            z = z.normalize() * self.speed * dt

        new_x = ui_handler.pos[0] + z.x
        new_y = ui_handler.pos[1] + (z.y if self.gravity <= 0 else 0) + (self.velocity_y if self.gravity > 0 else dy * self.speed * dt)

        ui_handler.pos = (new_x, new_y)
        if ui_handler.rect:
            ui_handler.rect.topleft = ui_handler.pos

        # Limites da tela
        if limits is not None and ui_handler.rect is not None:
            if isinstance(limits, pygame.Rect):
                if ui_handler.rect.top <= limits.top + margin:
                    ui_handler.rect.top = limits.top + margin
                    self.velocity_y = 0 # Reseta velocidade ao bater no teto
                if ui_handler.rect.bottom >= limits.bottom - margin:
                    ui_handler.rect.bottom = limits.bottom - margin
                    self.velocity_y = 0 # Reseta velocidade ao tocar no chão
                    self.jumped = False # Permite pular novamente
                if ui_handler.rect.left <= limits.left + margin:
                    ui_handler.rect.left = limits.left + margin
                if ui_handler.rect.right >= limits.right - margin:
                    ui_handler.rect.right = limits.right - margin
                
                ui_handler.pos = ui_handler.rect.topleft


    def __repr__(self):
        return "<MovementHandler>"



@dataclass(slots=True, eq=False)
class UIHandler:
    changed:  bool   = True
    tdrag:    bool   = False

    border:   int    = 0
    layer:    int    = 0 # class-layer
    bsize:    int    = 0 # border-size
    tsize:    int    = 0 # topbar-size

    align:    str    = "absolute"
    _type:    str    = "<UIHandler>"

    children: list   = field(default_factory=list)

    rect:     object = None # main-rect
    arect:    object = None # anchor-rect
    trect:    object = None # topbar-rect
    anchor:   object = None # main-anchor
    movement: object = field(default_factory=MovementHandler)

    pos:      tuple  = (0, 0)
    startpos: tuple  = (0, 0)
    endpos:   tuple  = (100, 100)
    adjust:   tuple  = (0, 0)
    size:     tuple  = (100, 100)
    msize:    tuple  = (None, None) # max-size
    
    stadjust: tuple = (0, 0)
    eadjust:  tuple = (0, 0)

    extras:   dict   = field(default_factory=dict)


    def collide(self, other: pygame.Rect):
        return self.rect.colliderect(other)


    def collidepoint(self, pos: tuple):
        return self.rect.collidepoint(pos)


    def set_speed(self, speed=200, step=0):
        if step <= 0 or speed == self.speed:
            self.speed = speed
        else:
            if speed > self.speed:
                self.speed = min(self.speed + step, speed)
            else:
                self.speed = max(self.speed - step, speed)


    def get_half(self, times=(1, 1), adjust=(0, 0)):
        if isinstance(times, (int, float)):
            times = (times, times)
        if isinstance(adjust, (int, float)):
            adjust = (adjust, adjust)

        if times[0] != 0 and times[1] != 0:
            w = int((self.size[0] + adjust[0]) / times[0])
            h = int((self.size[1] + adjust[1]) / times[1])
            return (w, h)
        log("UIHandler", "GET", "can't divide by zero!")
        return self.size


    def get_rect(self, surface=None, no_return=False):
        rect = pygame.Rect((*self.pos, *self.size))
        if surface is not None:
            rect = surface.get_rect(topleft=self.pos)
            w, h = calculate_bounded_size(self.size, self.msize)
            self.size = (w, h)
            rect.size = self.size
        if no_return:
            self.rect = rect
        else:
            return rect


    def __repr__(self):
        return "<UIHandler>"


    def __setattr__(self, key, value):
        if hasattr(self, key):
            if getattr(self, key) != value:
                object.__setattr__(self, "changed", True)
        object.__setattr__(self, key, value)



@dataclass(slots=True, eq=False)
class UXHandler:
    changed:   bool   = True
    show:      bool   = True  # main-show
    hshow:     bool   = True  # hover-show
    tshow:     bool   = False # topbar-show
    bshow:     bool   = False # border-show
    fitalic:   bool   = False # font-italic
    fbold:     bool   = True  # font-bold
    fsmooth:   bool   = True
    rescaled:  bool   = False

    alpha:     int    = 255
    fsize:     int    = 15 # font-size
    hstep:     int    = 5  # hover-step-animation

    _type:     str    = "<UXHandler>"
    content:   str    = "???"
    fname:     str    = "Courier New"
    path:      str    = ""
    root:      str    = ""
    animation: str    = None

    font:      object = None
    render:    object = None # font-render
    surface:   object = None # main-surface

    color:     tuple  = (50, 50, 50)     # main-color
    bcolor:    tuple  = (100, 100, 100)  # border-color
    tcolor:    tuple  = (150, 150, 150)  # topbar-color
    hcolor:    tuple  = (175, 175, 175)  # hover-color
    fcolor:    tuple  = (255, 255, 255)  # font-color
    fdata:     tuple  = None             # font-data

    extras:    dict   = field(default_factory=dict)


    def set_content(self, text, rewrite=True):
        if rewrite:
            self.content = text
        else:
            self.content += text


    def toggle_show(self):
        self.show = not self.show


    def rescale(self, rect, smooth=True):
        if self.rescaled or not self.path:
            return self.surface
        if self.root is not None:
            x = os.path.join(self.root, self.path)
        else:
            x = self.path
        if not os.path.exists(x):
            return self.surface
        img = pygame.image.load(x).convert_alpha()
        img_w, img_h = img.get_size()
        rect_w, rect_h = rect.width, rect.height
        if img_w == 0 or img_h == 0 or rect_w == 0 or rect_h == 0:
            return img
        ratio = min(rect_w / img_w, rect_h / img_h)
        new_size = (max(1, int(img_w * ratio)), max(1, int(img_h * ratio)))
        if smooth:
            img_res = pygame.transform.smoothscale(img, new_size)
        else:
            img_res = pygame.transform.scale(img, new_size)
        self.surface = img_res
        self.rescaled = True
        return img_res


    def load(self, rect=None):
        if not self.path:
            log("UXHandler", "ERROR", "couldn't read any path to load!")
            return None
        x = self.path
        if self.root and self.path:
            x = os.path.join(self.root, self.path)
        if not os.path.exists(x):
            log("UXHandler", "ERROR", f"couldn't load anything from path: {x}")
            return None
        log("UXHandler", "LOAD", f"image loaded from path {x}")
        self.surface = pygame.image.load(x).convert_alpha()
        self.rescaled = False
        if rect is not None:
            self.surface = self.rescale(rect)
        self.surface.set_alpha(self.alpha)


    def __repr__(self):
        return "<UXHandler>"


    def __setattr__(self, key, value):
        if hasattr(self, key) and getattr(self, key) != value:
            object.__setattr__(self, "changed", True)
        object.__setattr__(self, key, value)



@dataclass(slots=True, eq=False)
class RenderHandler:
    _type:  str  = "<RenderHandler>"
    query:  list = field(default_factory=list)


    def __repr__(self):
        return "<RenderHandler>"


    def update(self, screen, obj=None):
        if obj is None or not obj.ui.changed:
            return
        if not obj.ui.rect:
            if obj.ux.render is not None:
                obj.ui.rect = obj.ux.render.get_rect(topleft=obj.ui.pos)
            elif obj.ux.surface is not None:
                obj.ui.rect = obj.ux.surface.get_rect(topleft=obj.ui.pos)
            else:
                obj.ui.rect = pygame.Rect(*obj.ui.pos, *obj.ui.size)


    def draw(self, screen, obj=None):
        if obj is None:
            return
        surface = obj.ux.render or obj.ux.surface
        if surface is not None:
            screen.blit(surface, obj.ui.rect)
        else:
            pygame.draw.rect(screen, obj.ux.color, obj.ui.rect, width=obj.ui.border)
            if obj.ux.bshow and obj.ui.bsize > 0:
                pygame.draw.rect(screen, obj.ux.bcolor, obj.ui.rect, width=obj.ui.bsize)



@dataclass(slots=True, eq=False)
class Node:
    enabled: bool   = True
    debug:   bool   = True
    changed: bool   = True

    uid:     str    = ""
    _type:   str    = "<Node>"

    ui:      object = field(default_factory=UIHandler)
    ux:      object = field(default_factory=UXHandler)


    def __setattr__(self, key, value):
        if hasattr(self, key):
            if getattr(self, key) != value:
                object.__setattr__(self, "changed", True)
        object.__setattr__(self, key, value)


    def __repr__(self):
        return f"<Node as {self.uid}>"



@dataclass(slots=True, eq=False)
class Text:
    debug:     bool    = True
    enabled:   bool    = True
    changed:   bool    = True

    uid:       str     = None
    _type:     str     = "<Text>"

    ux:        object  = field(default_factory=UXHandler)
    ui:        object  = field(default_factory=UIHandler)

    _lines:    list    = field(default_factory=list)


    def wrap_text(self):
        content = self.ux.content if self.ux.content is not None else ""
        raw_paragraphs = content.split("\n")
        lines = []
        
        for paragraph in raw_paragraphs:
            if not paragraph:
                lines.append("")
                continue
            if not self.ui.msize[0]:
                lines.append(paragraph)
            else:
                words = paragraph.split(" ")
                current_line = []
                for word in words:
                    test_line = " ".join(current_line + [word]) if current_line else word
                    if self.ux.font.size(test_line)[0] <= self.ui.msize[0]:
                        current_line.append(word)
                    else:
                        if current_line:
                            lines.append(" ".join(current_line))
                            current_line = [word]
                        else:
                            lines.append(word)
                            current_line = []
                if current_line:
                    lines.append(" ".join(current_line))
        return lines if lines else [""]


    def __post_init__(self):
        self.ux.fdata = (self.ux.fname, self.ux.fsize, self.ux.fbold, self.ux.fitalic)


    def __setattr__(self, key, value):
        if hasattr(self, key):
            if getattr(self, key) != value:
                object.__setattr__(self, "changed", True)
        object.__setattr__(self, key, value)


    def __repr__(self):
        return f"<Text as {self.uid}>"



@dataclass(slots=True, eq=False)
class Rect:
    debug:   bool   = True
    enabled: bool   = True
    changed: bool   = True


    _type:   str    = "<Rect>"
    uid:     str    = None

    ui:      object = field(default_factory=UIHandler)
    ux:      object = field(default_factory=UXHandler)


    def set_size(self, width: int, height: int):
        self.ui.size = (width, height)
        if self.ui.rect is not None:
            self.ui.rect.size = self.ui.size
        else:
            self.ui.rect = pygame.Rect((*self.ui.pos, *self.ui.size))


    def __setattr__(self, key, value):
        if hasattr(self, key):
            if getattr(self, key) != value:
                object.__setattr__(self, "changed", True)
        object.__setattr__(self, key, value)


    def __repr__(self):
        return f"<Rect as {self.uid}>"



@dataclass(slots=True, eq=False)
class Image:
    enabled: bool   = True
    changed: bool   = True
    debug:   bool   = True

    _type:   str    = "<Image>"
    uid:     str    = ""

    ui:      object = field(default_factory=UIHandler)
    ux:      object = field(default_factory=UXHandler)


    def __setattr__(self, key, value):
        if hasattr(self, key):
            if getattr(self, key) != value:
                object.__setattr__(self, "changed", True)
        object.__setattr__(self, key, value)


    def __repr__(self):
        return f"<Image as {self.uid}>"



@dataclass(slots=True, eq=False)
class Modal:
    enabled:  bool   = True
    changed:  bool   = True
    debug:    bool   = True

    _type:    str    = "<Modal>"
    uid:      str    = ""

    _offset:  tuple  = field(default_factory=tuple)

    ui:       object = field(default_factory=UIHandler)
    ux:       object = field(default_factory=UXHandler)


    def __post_init__(self):
        if self.ui.children is None:
            self.ui.children = []


    def add_child(self, obj: object, adjust: tuple=None):
        if obj is None:
            log("Modal", "ERROR", "child must be an object!")
        elif obj.ui.anchor == self and obj in self.ui.children:
            log("Modal", "WARN", f"child {obj.uid} already in children!")
        else:
            self.ui.children.append(obj)
            obj.ui.anchor   = self
            obj.ui.arect    = self.ui.rect
            obj.ui.layer    = self.ui.layer + 1
            obj.ui.align    = "relative.topleft"
            obj.ui.adjust   = adjust if adjust is not None else (2, 2)
            log("Modal", "ADD", f"child {obj.uid} has been added to {self.uid} children")


    def rem_child(self, obj: object):
        if obj in self.ui.children:
            self.ui.children.remove(obj)
            log("Modal", "DEL" f"{obj.uid} has been removed from {self.uid} children")


    def __setattr__(self, key, value):
        if hasattr(self, key):
            if getattr(self, key) != value:
                object.__setattr__(self, "changed", True)
        object.__setattr__(self, key, value)


    def __repr__(self):
        return f"<Modal as {self.uid}>"



@dataclass(slots=True, eq=False)
class Button:
    enabled:  bool     = True
    changed:  bool     = True
    debug:    bool     = True
    clicked:  bool     = False
    hover:    bool     = False

    uid:      str      = ""
    _type:    str      = "<Button>"

    _icons:   list     = field(default_factory=list) # small images

    ux:       object   = field(default_factory=UXHandler)
    ui:       object   = field(default_factory=UIHandler)

    on_click: callable = None


    def _calculate(self, current, target, step=5):
        if target > current:
            current += step
            if current > target:
                current = target
        elif target < current:
            current -= step
            if current < target:
                current = target
        return current


    def update_animation(self, _uuid="_RGBANIMATIONEASE-IN-OUT_"):
        if self.ux.extras.get(_uuid, None) is None:
            base = self.ux.color
            hover = self.ux.hcolor
            clicked = (
                max(0, hover[0] - 80),
                max(0, hover[1] - 80),
                max(0, hover[2] - 80)
            )
            self.ux.extras[_uuid] = {
                "base": base,
                "hover": hover,
                "click": clicked
            }
        data = self.ux.extras[_uuid]
        if self.clicked:
            target = data["click"]
        else:
            target = data["hover"] if self.hover else data["base"]
        if self.ux.animation is None:
            if self.ux.color != target:
                self.ux.color = target
                self.ux.changed = True
                self.changed = True
            return
        if self.ux.animation == "ease-in-out":
            current = self.ux.color
            if current == target:
                return
            r, g, b = current
            _r = self._calculate(r, target[0])
            _g = self._calculate(g, target[1])
            _b = self._calculate(b, target[2])
            self.ux.color = (_r, _g, _b)
            self.ux.changed = True
            self.changed = True


    def __repr__(self):
        return f"<Button as {self.uid}>"



@dataclass(slots=True, eq=False)
class Bind:
    uid:      str      = ""
    _type:    str      = "<Bind>"
    event:    object   = None
    key:      object   = None
    callback: callable = None


    def call(self):
        try:
            if callable(self.callback):
                self.callback()
                log("Bind", "CALL", f"{self.uid} - WORKING")
                return True
            else:
                log("Bind", "ERROR", f"{self.uid} isn't a callable!")
                return False
        except Exception as e:
            log("Bind", "EXCEPTION", f"{self.uid} couldn't be called! - {type(e).__name__} in {e}")
            return False


    def __repr__(self):
        return f"<Bind as {self.uid}>"



@dataclass(slots=True, eq=False)
class Line:
    enabled: bool   = True
    changed: bool   = True
    debug:   bool   = True

    uid:     str    = ""
    _type:   str    = "<Line>"

    ui:      object = field(default_factory=UIHandler)
    ux:      object = field(default_factory=UXHandler)



@dataclass(slots=True, eq=False)
class MouseManager:
    enabled:  bool   = True

    detected: object = None

    pos:      tuple  = (0, 0)
    rel:      tuple  = (0, 0)
    pressed:  tuple  = (False, False, False)

    cursors: dict   = field(default_factory=dict)


    def __post_init__(self):
        self.cursors = {
            "hand":  pygame.SYSTEM_CURSOR_HAND,
            "wait":  pygame.SYSTEM_CURSOR_WAIT,
            "arrow": pygame.SYSTEM_CURSOR_ARROW,
            "move":  pygame.SYSTEM_CURSOR_SIZEALL
        }


    def click(self, button: int, query: list=None):
        if not self.pressed[button]:
            return None
        for obj in query:
            if getattr(obj.ux, "show", True) and getattr(obj, "debug", True):
                if obj.ui.rect and obj.ui.collidepoint(self.pos):
                    return obj
        return None


    def hover(self, obj: object=None):
        if obj is not None:
            if obj.ui.rect is not None:
                return obj.ui.collidepoint(self.pos)



@dataclass(slots=True, eq=False)
class AudioManager:
    data: dict = field(default_factory=dict)
    channels: dict = field(default_factory=lambda: {0: pygame.mixer.Channel(0)})
    master: float = 0.5
    muted: bool = False
    bgm: bool = False


    def mute(self) -> bool:
        self.muted = not self.muted
        if self.muted:
            self.vl_master(0.0)
        else:
            try:
                for sound in self.data:
                    self.data[sound]["ref"].set_volume(self.data[sound]["volume"])
            except Exception:
                return False
        return True


    def vl_master(self, volume: float) -> bool:
        if not isinstance(volume, float) or not (0.0 <= volume <= 1.0):
            raise ValueError("key: volume must be a float in range 0.0 to 1.0!")
        self.master = volume
        try:
            for sound in self.data:
                self.data[sound]["ref"].set_volume(self.master)
        except Exception:
            return False
        return True


    def vl_channel(self, volume: float, channel: int = 0) -> bool:
        if not isinstance(volume, float) or not (0.0 <= volume <= 1.0):
            raise ValueError("key: volume must be a float in range 0.0 to 1.0!")
        if not isinstance(channel, int):
            raise  ValueError(f"item: {channel} must be an int, like: 1, 2 or 3!")

        if channel not in self.channels:
            raise KeyError(f"item: {channel} doesn't exists!")
        else:
            if not self.muted:
                self.channels[channel].set_volume(volume)
                return True
        return False


    def vl_fx(self, volume: float, sound_id: str) -> bool:
        if not isinstance(volume, float) or not (0.0 <= volume <= 1.0):
            raise ValueError("key: volume must be a float in range 0.0 to 1.0!")
        if not isinstance(sound_id, str):
            raise ValueError(f"item: {sound_id} must be a string!")
        if sound_id not in self.data:
            raise KeyError(f"item: {sound_id} doesn't exists!")
        else:
            self.data[sound_id]["volume"] = volume
            if not self.muted:
                self.data[sound_id]["ref"].set_volume(volume)
            return True


    def vl_bg(self, volume: float) -> bool:
        if not isinstance(volume, float) or not (0.0 <= volume <= 1.0):
            raise ValueError("key: volume must be a float in range 0.0 to 1.0!")
        if not self.muted:
            pygame.mixer.music.set_volume(volume)
            return True
        return False


    def fx_add(self, sound_id: str, sound_local: str, channel: int = 0, volume=None) -> bool:
        if volume is not None and (not isinstance(volume, float) or not (0.0 <= volume <= 1.0)):
            raise ValueError("key: volume must be a float in range 0.0 to 1.0!")
        if not all(isinstance(i, str) for i in [sound_id, sound_local]):
            raise ValueError("key: id & local must be a string!")
        if not isinstance(channel, int):
            raise ValueError(f"item: {channel} must be an int, like: 1, 2 or 3!")
        if channel not in self.channels:
            log("Channel", "WARN", f"item: {channel} doesn't exists!")
            return False
        if volume is None:
            volume = self.master
        if sound_id not in self.data:
            self.data[sound_id] = {
                "ref": pygame.mixer.Sound(sound_local), 
                "local": sound_local, 
                "channel": channel, 
                "volume": volume
            }
            self.data[sound_id]["ref"].set_volume(volume)
            log("Sound", "ADD", f"item: {sound_id} has been added to data successfully!")
            return True
        log("Sound", "WARN", f"item: {sound_id} already exists!")
        return False


    def fx_play(self, sound_id: str) -> bool:
        if not isinstance(sound_id, str):
            raise ValueError("key: id must be a string!")
        if sound_id not in self.data:
            log("Sound", "WARN", f"item: {sound_id} doesn't exists!")
            return False
        channel_id = self.data[sound_id]["channel"]
        if channel_id in self.channels:
            if not self.muted:
                self.data[sound_id]["ref"].set_volume(self.data[sound_id]["volume"])
            self.channels[channel_id].play(self.data[sound_id]["ref"])
            return True
        log("Channel", "WARN", f"item: {channel_id} doesn't exists!")
        return False


    def fx_stop(self, sound_id=None):
        if sound_id is None:
            for i in self.data:
                channel_id = self.data[i]["channel"]
                if channel_id in self.channels:
                    self.channels[channel_id].stop()
                    log("Channel", "STOP", f"item: {channel_id} sounds has been stopped!")
        else:
            if sound_id in self.data:
                channel_id = self.data[sound_id]["channel"]
                if channel_id in self.channels:
                    self.channels[channel_id].stop()
                    log("Channel", "STOP", f"item: {channel_id} sounds has been stopped!")


    def new_channel(self, channel_id: int, volume=None) -> bool:
        if not isinstance(channel_id, int):
            raise  ValueError(f"item: {channel_id} must be an int, like: 1, 2 or 3!")
        if volume is not None and (not isinstance(volume, float) or not (0.0 <= volume <= 1.0)):
            raise ValueError("key: volume must be a float in range 0.0 to 1.0!")
        if volume is None:
            volume = self.master
        if channel_id not in self.channels:
            self.channels[channel_id] = pygame.mixer.Channel(channel_id)
            self.channels[channel_id].set_volume(volume)
            log("Channel", "ADDED", f"item: {channel_id} has been created successfully!")
            return True
        log("Channel", "WARN", f"item: {channel_id} already exists!")
        return False


    def bg_play(self, sound_local: str, loop=True, volume=None) -> bool:
        if volume is not None and (not isinstance(volume, float) or not (0.0 <= volume <= 1.0)):
            raise ValueError("key: volume must be a float in range 0.0 to 1.0!")
        if not isinstance(sound_local, str):
            raise ValueError("key: local must be a string!")
        if not isinstance(loop, bool):
            raise ValueError("key: loop must be a boolean!")
        if volume is None:
            volume = self.master
        if not self.bgm:
            self.bgm = True
            pygame.mixer.music.load(sound_local)
            if not self.muted:
                pygame.mixer.music.set_volume(volume)
            if loop:
                pygame.mixer.music.play(-1)
            else:
                pygame.mixer.music.play()
            log("Audio", "PLAY", "item: bgm is now playing!")
            return True
        return False


    def bg_stop(self) -> bool:
        if self.bgm:
            self.bgm = False
            pygame.mixer.music.stop()
            log("Audio", "STOP", "item: bgm has been stopped!")
            return True
        log("Audio", "WARN", "There's no music playing!")
        return False


    def __repr__(self):
        return "<AudioManager>"



class ContextManager:
    def __init__(self, root, init_mixer=False):
        self.uid        = "ContextManager"
        self.root       = root
        self.index      = 0  # unique, incremental
        self.bind_index = 0  # unique, incremental, only binds
        self.query      = {} # index: obj
        self._native    = (int, float, str, bool, type(None), list, dict, tuple, set)
        self._binds     = {}
        self.sort_dirty = True
        self.paused     = False
        self.models     = {}
        self.mouse      = MouseManager()
        self.render     = RenderHandler()
        self.audio      = AudioManager() if init_mixer else None
        self.new_model(
            node=Node,
            text=Text,
            rect=Rect,
            image=Image,
            modal=Modal,
            button=Button,
            line=Line
        )


    def serialize(self, obj, get_all=False, dump=False):
        y = {}
        if not get_all:
            y = self.debug_item(obj)
        else:
            for k, v in self.query.items():
                y[k] = self.debug_item(v)
        if dump:
            y = str(json.dumps(y, indent=4, ensure_ascii=False, default=str))
        return y


    # folders/filename only, root implicit
    def save_item(self, obj: object, path=None):
        if obj is None or obj not in self.query.values():
            log("System", "ERROR", "item: obj must be a valid object!")
            return False
        if path is None:
            log("System", "WARN", "key: path must be a string!")
            return False
        x = os.path.join(self.root, path)
        if not os.path.exists(os.path.dirname(x)):
            log("System", "ERROR", "key: path doesn't exists!")
            return False
        try:
            with open(x, "w", encoding="utf-8") as f:
                json.dump(self.serialize(obj), f, indent=4, ensure_ascii=False, default=str)
            log("System", "SAVE", f"{obj.uid} data has been saved in {x}")
            return True
        except Exception as e:
            log("System", "EXCEPTION", f"can't save {obj.uid} data in path: {path} - {e}")
            return False


    def new_model(self, **models):
        for k, v in models.items():
            if k in self.models:
                log("Model", "WARN", f"model: {k} already exists!")
                continue
            self.models[k] = v
            log("Model", "ADD", f"model: {k} created successfully!")


    def add_bind(self, event, key, callback=None, uid=None, temp=False):
        if uid is None:
            uid = f"bind-{self.bind_index}-{key}"
        if not temp:
            if uid in self._binds:
                log(f"Bind", "CALL",  f"{uid} - WORKING")
                return self._binds[uid]
        if key is None: log("Bind", "WARN", "key is None!")
        x          = Bind()
        x.uid      = uid
        x.key      = getattr(pygame, f"K_{key}", None) if isinstance(key, str) else key
        x.event    = getattr(pygame, event, None) if isinstance(event, str) else event
        x.callback = callback
        log("Bind", "ADD", f"item: {uid} has been added to binds!")
        if not temp:
            self._binds[uid] = x
            self.bind_index += 1
        return x


    def rem_bind(self, uid):
        if uid not in self._binds:
            log("Bind", "WARN", f"item: {uid} doens't exists!")
            return False
        del self._binds[uid]
        return True


    def debug_item(self, obj: object) -> dict:
        x = {}
        attributes = obj.__slots__ if hasattr(obj, "__slots__") else obj.__dict__.keys()
        ui_attr    = obj.ui.__slots__
        ux_attr    = obj.ux.__slots__
        for i in attributes:
            z = getattr(obj, i, "Error")
            if i in ["ux", "ui"]: continue
            if hasattr(z, "_type") or isinstance(z, (Text, Image, Rect, Modal, Bind)):
                x[i] = z
            elif callable(z) or not isinstance(z, self._native):
                x[i] = str(z)
            else:
                x[i] = z
        x["ui"] = {}
        for i in ui_attr:
            z = getattr(obj.ui, i, "Error")
            if callable(z) or not isinstance(z, self._native):
                x["ui"][i] = str(z)
            else:
                x["ui"][i] = z
        x["ux"] = {}
        for i in ux_attr:
            z = getattr(obj.ux, i, "Error")
            if callable(z) or not isinstance(z, self._native):
                x["ux"][i] = str(z)
            else:
                x["ux"][i] = z
        return x


    def add_item(self, obj: object, custom_uid: str = None):
        idx = self.index if custom_uid is None else custom_uid
        if idx not in self.query:
            self.query[idx] = obj
            self.render.query.append(obj)
            self.sort_dirty = True
            log(f"Item", "ADD", f"item: {idx} - ({self.index:0>3}) has been added to query!")
            self.index += 1
            return True
        else:
            log("Item", "WARN", f"item: {idx} already exists!")
            return False


    def rem_item(self, uid: str=None):
        if uid is None:
            log("Item", "ERROR", "item uid must be a string!")
            return False
        if uid in self.query:
            obj = self.query.pop(uid)
            if obj in self.render.query:
                self.render.query.remove(obj)
                log("Item", "DEL", f"item: {uid} has been removed successfully!")
            self.sort_dirty = True
            return True
        return False


    def item_update(self, obj, movset=False):
        if obj.ui.anchor is not None:
            if isinstance(obj.ui.anchor, pygame.Rect):
                obj.ui.arect = obj.ui.anchor
            elif hasattr(obj.ui.anchor, "rect") and obj.ui.anchor.rect is not None:
                obj.ui.arect = obj.ui.anchor.rect
            elif hasattr(obj.ui.anchor, "ui") and hasattr(obj.ui.anchor.ui, "rect") and obj.ui.anchor.ui.rect is not None:
                obj.ui.arect = obj.ui.anchor.ui.rect

        if not obj.ui.align or not obj.ui.rect:
            return

        i = obj.ui.align.split('.')
        m = i[0]
        p = i[1] if len(i) > 1 else "topleft"
        d = i[2] if len(i) > 2 else None

        match m:
            case "absolute":
                x, y = obj.ui.pos
                match p:
                    case "topleft":
                        obj.ui.rect.topleft = (x, y)
                    case "topright":
                        obj.ui.rect.topright = (x, y)
                    case "bottomleft":
                        obj.ui.rect.bottomleft = (x, y)
                    case "bottomright":
                        obj.ui.rect.bottomright = (x, y)
                    case _:
                        obj.ui.rect.x, obj.ui.rect.y = (x, y)
            case "relative":
                if obj.ui.anchor is None or obj.ui.arect is None:
                    return
                if obj._type == "<Line>":
                    if p == "mid" and d == "top":
                        startpos = obj.ui.arect.midtop
                        endpos   = obj.ui.arect.midbottom
                        obj.ui.startpos = (startpos[0] + obj.ui.stadjust[0], startpos[1] + obj.ui.stadjust[1])
                        obj.ui.endpos   = (endpos[0] + obj.ui.eadjust[0], endpos[1] + obj.ui.eadjust[1])
                    else:
                        obj.ui.startpos = (obj.ui.arect.left + obj.ui.adjust[0], obj.ui.arect.top + obj.ui.adjust[1])
                        obj.ui.endpos = (obj.ui.arect.left + obj.ui.adjust[0], obj.ui.arect.bottom + obj.ui.adjust[1])
                    return
                match p:
                    case "topleft":
                        obj.ui.rect.topleft = obj.ui.arect.topleft
                    case "topright":
                        obj.ui.rect.topright = obj.ui.arect.topright
                    case "bottomleft":
                        obj.ui.rect.bottomleft = obj.ui.arect.bottomleft
                    case "bottomright":
                        obj.ui.rect.bottomright = obj.ui.arect.bottomright
                    case "mid":
                        if d is None:
                            return
                        match d:
                            case "top":
                                obj.ui.rect.midtop = obj.ui.arect.midtop
                            case "bottom":
                                obj.ui.rect.midbottom = obj.ui.arect.midbottom
                            case "left":
                                obj.ui.rect.midleft = obj.ui.arect.midleft
                            case "right":
                                obj.ui.rect.midright = obj.ui.arect.midright
                            case "above":
                                obj.ui.rect.midbottom = obj.ui.arect.midtop
                            case "sidel":
                                obj.ui.rect.left = obj.ui.arect.right
                            case "sider":
                                obj.ui.rect.right = obj.ui.arect.left
                            case "bellow":
                                obj.ui.rect.midtop = obj.ui.arect.midbottom
                            case "center":
                                obj.ui.rect.center = obj.ui.arect.center
                            case _:
                                obj.ui.rect.topleft = obj.ui.arect.topleft
                    case _:
                        obj.ui.rect.topleft = obj.ui.arect.topleft
            case _:
                pass
        obj.ui.rect.x += obj.ui.adjust[0]
        obj.ui.rect.y += obj.ui.adjust[1]
        obj.ui.pos = (obj.ui.rect.x, obj.ui.rect.y)


    def create(self, model: str, uid: str, **kwargs):
        try:
            m = self.models.get(model, None)
            if not m:
                log(f"Model", "WARN", f"model: {model} doens't exists!")
                return None
            temp = m()
            temp.uid = uid
            x = None
            x = temp.__slots__ if hasattr(temp, "__slots__") else temp.__dict__
            for k, v in kwargs.items():
                if hasattr(temp.ui, k):
                    setattr(temp.ui, k, v)
                    continue
                elif hasattr(temp.ux, k):
                    setattr(temp.ux, k, v)
                    continue
                else:
                    setattr(temp, k, v)

                if k not in x:
                    log("Item", "WARN", f"key: {k} isn't in {uid} slots!")
                    continue
                elif k == "uid":
                    log("Item", "WARN", "key: uid already is a required args")
                    continue


            if temp.ui.rect is None:
                temp.ui.rect = temp.ui.get_rect(temp.ux.render or temp.ux.surface)

            if temp._type == "<Text>":
                temp.ux.font = get_cached_sysfont(*temp.ux.fdata)
                temp.ux.render = temp.ux.font.render(temp.ux.content, temp.ux.fsmooth, temp.ux.color)
            elif temp._type == "<Image>":
                if not temp.ux.root:
                    temp.ux.root = self.root
                temp.ux.load(temp.ui.rect)
            if temp.ui.rect is None:
                temp.ui.rect = temp.ui.get_rect(temp.ux.render or temp.ux.surface)
            if self.add_item(temp, uid):
                return temp
            return None
        except Exception as e:
            log("Item", "EXCEPTION", f"index: {self.index:0>3} - system couldn't create {model}\n{e}")
            return Node()


    def create_text(self, uid, **kwargs):
        return self.create("text", uid, **kwargs)


    def create_rect(self, uid, **kwargs):
        return self.create("rect", uid, **kwargs)


    def create_image(self, uid, **kwargs):
        return self.create("image", uid, **kwargs)


    def create_modal(self, uid, **kwargs):
        return self.create("modal", uid, **kwargs)


    def create_button(self, uid, **kwargs):
        return self.create("button", uid, **kwargs)


    def create_line(self, uid, **kwargs):
        return self.create("line", uid, **kwargs)


    def create_node(self, uid, **kwargs):
        return self.create("node", uid, **kwargs)


    def destroy(self, obj: object|str=None):
        if obj is None:
            log("Destroy","WARN", "key: obj is None!")
            return None
        x = None
        if isinstance(obj, str):
            x = obj
        else: 
            if hasattr(obj, "uid"):
                x = obj.uid
        if x is not None:
            temp = self.rem_item(x)
            if temp:
                log(f"Destroy: {x} has been destroyed successfully")
        return None


    def action(self, obj=None, key=None, val=None, function=None):
        status = False
        result = None
        
        if obj is None:
            if isinstance(key, str):
                log("Action", "ERROR", "key: obj is required to use a key or val!")
        else:
            if key is None:
                obj = val() if callable(val) else val
                result = obj
                status = True
            elif isinstance(key, str):
                target = obj
                if hasattr(obj, "ui") and hasattr(obj, "ux"):
                    if hasattr(obj.ui, key):
                        target = obj.ui
                    elif hasattr(obj.ux, key):
                        target = obj.ux
                    elif hasattr(obj, key):
                        target = obj
                    else:
                        target = None
                elif not hasattr(obj, key):
                    target = None
                if target is not None:
                    resolved_val = val() if callable(val) else val
                    setattr(target, key, resolved_val)
                    result = getattr(target, key, None)
                    status = True
                else:
                    uid_str = getattr(obj, "uid", type(obj).__name__)
                    log("Action", "WARN", f"item: {uid_str} haven't any attribute as {key}")
        if function is not None and callable(function):
            function()
        if status:
            return result


    def _render(self, screen, dt, limits=None):
        if self.sort_dirty:
            self.render.query.sort(key=lambda item: item.ui.layer)
            self.sort_dirty = False
        for obj in self.render.query:
            if obj.ui.anchor is not None and not isinstance(obj.ui.anchor, pygame.Rect):
                if not obj.ui.anchor.ux.show or not obj.ui.anchor.enabled:
                    obj.enabled = False
                else:
                    obj.enabled = True

            if not obj.ux.show or not obj.enabled:
                continue

            self.item_update(obj)

            if obj.ui.changed or obj.ux.changed:
                obj.changed = True

            if obj.ui.movement.movset and not self.paused:
                obj.ui.movement.update(obj.ui, dt, limits)

            if obj.changed:
                # Resolução de âncora
                if obj.ui.anchor is not None:
                    if isinstance(obj.ui.anchor, pygame.Rect):
                        obj.ui.arect = obj.ui.anchor
                    elif hasattr(obj.ui.anchor, "rect") and obj.ui.anchor.rect is not None:
                        obj.ui.arect = obj.ui.anchor.rect
                    elif hasattr(obj.ui.anchor, "ui") and hasattr(obj.ui.anchor.ui, "rect") and obj.ui.anchor.ui.rect is not None:
                        obj.ui.arect = obj.ui.anchor.ui.rect
                    if obj.ui.arect is not None:
                        w, h = obj.ui.msize
                        arect_w, arect_h = obj.ui.arect.size
                        obj.ui.msize = (arect_w if w is None else w, arect_h if h is None else h)
                else:
                    obj.ui.msize = (None, None)

                # Gestão de Surface e Cores básicas
                if obj.ux.surface is None and obj._type not in ("<Rect>", "<Text>"):
                    obj.ux.surface = pygame.Surface(obj.ui.size, pygame.SRCALPHA)
                    if obj.ux.color:
                        obj.ux.surface.fill(obj.ux.color)
                    obj.ux.surface.set_alpha(obj.ux.alpha)

                # Gestão de Rect principal
                if obj.ui.rect is not None:
                    if obj.ui.rect.size != obj.ui.size:
                        obj.ui.rect.size = obj.ui.size
                else:
                    if obj.ux.surface is not None:
                        obj.ui.rect = obj.ux.surface.get_rect(topleft=obj.ui.pos)
                    else:
                        obj.ui.rect = pygame.Rect((*obj.ui.pos, *obj.ui.size))

                # Gestão de Filhos (Children)
                if hasattr(obj.ui, "children") and obj.ui.children:
                    for i in obj.ui.children:
                        x, y = i.ui.adjust
                        if x <= obj.ui.bsize: x += obj.ui.bsize
                        if y <= obj.ui.bsize: y += obj.ui.bsize
                        i.ui.adjust = (x, y)
                        if i.ui.anchor is None or i.ui.anchor is not obj:
                            i.ui.anchor = obj
                            i.ui.arect = obj.ui.rect
                        if not i.ui.align:
                            i.ui.align = "relative.topleft"
                        if i.ui.layer <= obj.ui.layer:
                            i.ui.layer = obj.ui.layer + 1
                            self.sort_dirty = True

                if obj._type == "<Text>":
                    new_fdata = (obj.ux.fname, obj.ux.fsize, obj.ux.fbold, obj.ux.fitalic)
                    if obj.ux.font is None or obj.ux.fdata != new_fdata:
                        obj.ux.fdata = new_fdata
                        obj.ux.font = get_cached_sysfont(*obj.ux.fdata)
                    raw_lines = obj.wrap_text()
                    obj._lines = [obj.ux.font.render(lt, obj.ux.fsmooth, obj.ux.color) for lt in raw_lines]
                    current_pos = (obj.ui.rect.x, obj.ui.rect.y) if obj.ui.rect else obj.ui.pos
                    if obj._lines:
                        obj.ui.rect = obj._lines[0].get_rect(topleft=current_pos)
                elif obj._type == "<Image>" and obj.ui.rect is None:
                    if obj.ux.surface is None:
                        obj.ux.rescaled = False
                        obj.ux.load(obj.ui.rect)
                    else:
                        obj.ui.rect = obj.ux.surface.get_rect(topleft=obj.ui.pos)
                elif obj._type == "<Modal>" and obj.ux.tshow and obj.ui.trect is None and obj.ui.rect is not None:
                    obj.ui.trect = pygame.Rect(*obj.ui.rect.topleft, obj.ui.rect.width, obj.ui.tsize)
                    obj.ui.trect.bottomleft = obj.ui.rect.topleft
                obj.changed = False
                obj.ui.changed = False
                obj.ux.changed = False

            # Fase de Desenho (Blit / Draw)
            if obj._type == "<Line>":
                pygame.draw.line(screen, obj.ux.color, obj.ui.startpos, obj.ui.endpos, width=obj.ui.border)
            elif obj._type == "<Text>":
                if obj._lines and obj.ui.rect:
                    line_rect = obj._lines[0].get_rect(topleft=obj.ui.rect.topleft)
                    screen.blit(obj._lines[0], line_rect)
                    for surf in obj._lines[1:]:
                        line_rect = surf.get_rect(topleft=(line_rect.left, line_rect.bottom + 2))
                        screen.blit(surf, line_rect)
            elif obj._type == "<Image>":
                if obj.ux.surface and obj.ui.rect:
                    screen.blit(obj.ux.surface, obj.ui.rect)
            elif obj._type == "<Rect>":
                pygame.draw.rect(screen, obj.ux.color, obj.ui.rect, width=obj.ui.border)
            elif obj._type == "<Modal>":
                if obj.ux.surface and obj.ui.rect:
                    screen.blit(obj.ux.surface, obj.ui.rect.topleft)
                    pygame.draw.rect(screen, obj.ux.bcolor, obj.ui.rect, width=obj.ui.bsize)
                    if obj.ux.tshow and obj.ui.trect:
                        obj.ui.trect.bottomleft = obj.ui.rect.topleft
                        obj.ui.trect.height = obj.ui.tsize
                        pygame.draw.rect(screen, obj.ux.tcolor, obj.ui.trect)
            elif obj._type in ("<Button>", "<CheckButton>"):
                if obj.ui.rect:
                    is_hovered = obj.ui.collidepoint(self.mouse.pos)
                    obj.hover = is_hovered
                    obj.update_animation()
                    current_color = obj.ux.color
                    pygame.draw.rect(screen, current_color, obj.ui.rect, width=obj.ui.border)
                    if obj.ux.bshow and obj.ui.bsize > 0:
                        pygame.draw.rect(screen, obj.ux.bcolor, obj.ui.rect, width=obj.ui.bsize)
            if obj.ui.rect is not None and obj.ui.bsize > 0:
                pygame.draw.rect(screen, obj.ux.bcolor, obj.ui.rect, width=obj.ui.bsize)


    def event_handler(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                modals = [obj for obj in self.render.query if obj._type == "<Modal>" and obj.ux.show]
                for modal in modals:
                    if modal.ui.trect and modal.ui.trect.collidepoint(self.mouse.pos):
                        self.mouse.detected = modal
                        modal.ui.tdrag = True
                        modal.ui.movement.flying = True
                        modal._offset = (self.mouse.pos[0] - modal.ui.rect.x, self.mouse.pos[1] - modal.ui.rect.y)
                        pygame.mouse.set_cursor(self.mouse.cursors["move"])
                        break
                buttons = [obj for obj in self.render.query if obj._type == "<Button>" and obj.ux.show and obj.enabled]
                for btn in buttons:
                    if btn.ui.rect and btn.ui.collidepoint(self.mouse.pos):
                        btn.clicked = True
                        if btn.on_click is not None and callable(btn.on_click):
                            log("Button", "CALL", f"item: {btn.uid} clicked")
                            print(f" {'-'*33}")
                            btn.on_click()
                            print(f" {'-'*33}")
        elif event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                for obj in self.render.query:
                    if obj._type == "<Button>":
                        obj.clicked = False
                if self.mouse.detected:
                    if hasattr(self.mouse.detected.ui, "tdrag"):
                        self.mouse.detected.ui.tdrag = False
                        self.mouse.detected.ui.movement.flying = False
                    self.mouse.detected = None
                hovering_any = False
                modals = [obj for obj in self.render.query if obj._type == "<Modal>" and obj.ux.show]
                for modal in modals:
                    if modal.ui.trect and modal.ui.trect.collidepoint(self.mouse.pos):
                        hovering_any = True
                        break
                if hovering_any:
                    pygame.mouse.set_cursor(self.mouse.cursors["hand"])
                else:
                    pygame.mouse.set_cursor(self.mouse.cursors["arrow"])
        elif event.type == pygame.MOUSEMOTION:
            if self.mouse.detected and getattr(self.mouse.detected.ui, "tdrag", False):
                modal = self.mouse.detected
                dx, dy = modal._offset
                new_x = self.mouse.pos[0] - dx
                new_y = self.mouse.pos[1] - dy
                modal.ui.rect.topleft = (new_x, new_y)
                modal.ui.pos = (new_x, new_y)
                if modal.ui.trect:
                    modal.ui.trect.topleft = (new_x, new_y)
            else:
                hovering_any = False
                modals = [obj for obj in self.render.query if obj._type == "<Modal>" and obj.ux.show]
                for modal in modals:
                    if modal.ui.trect and modal.ui.trect.collidepoint(self.mouse.pos):
                        hovering_any = True
                        break
                if hovering_any:
                    pygame.mouse.set_cursor(self.mouse.cursors["hand"])
                else:
                    pygame.mouse.set_cursor(self.mouse.cursors["arrow"])


    def update_binds(self, event):
        if self.mouse.enabled:
            if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
                self.mouse.pos = pygame.mouse.get_pos()
                self.mouse.rel = pygame.mouse.get_rel()
                if hasattr(event, "button"):
                    self.mouse.pressed = pygame.mouse.get_pressed()
        self.event_handler(event)
        for i in self._binds.values():
            if event.type == i.event:
                ev_val = getattr(event, 'key', None) if event.type in (pygame.KEYDOWN, pygame.KEYUP) else getattr(event, 'button', None)
                if ev_val is not None and ev_val == i.key:
                    i.call()



class Game:
    def __init__(self, root=None, init_mixer=False, init_joystick=False):
        pygame.display.init()
        pygame.font.init()
        if init_mixer:
            pygame.mixer.init()
            log("System", "INIT", "item: mixer has been initiated")
        if init_joystick:
            pygame.joystick.init()
            log("System", "INIT", "item: joystick has been initiated")
        x = load_config(root)
        self.uid = "Game"
        self.root = root if root is not None else os.path.dirname(os.path.abspath(__file__))
        self.w, self.h = x.get("size", (900, 600))
        self.m = x.get("margin", 5)
        self.fps = x.get("fps", 30)
        self.colors = x.get("colors", {})
        self.screen = pygame.display.set_mode((self.w, self.h))
        self.font = pygame.font.SysFont(*tuple(x.get("font", ("Courier New", 15, True))))
        self.clock = pygame.time.Clock()
        self.rect = self.screen.get_rect()
        self.running = True
        self.paused = False
        self.debug = True
        self.fullscreen = False
        self.data = {"update": {}, "draw": {}}
        self.context = ContextManager(root, init_mixer)
        self.context.add_bind("KEYDOWN", "F11", lambda: self.toggle_fullscreen())


    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            self.screen = pygame.display.set_mode((self.w, self.h), pygame.SCALED | pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.w, self.h))
        self.rect = self.screen.get_rect(topleft=(0, 0))


    def add_event(self, uid, where="update", obj=None, key=None, val=None, function=None):
        if where in self.data and uid not in self.data[where]:
            self.data[where][uid] = lambda: self.context.action(obj, key, val, function)


    def update(self, dt):
        for i in self.data["update"].values():
            i()


    def draw(self, dt):
        for i in self.data["draw"].values():
            i()
        self.context._render(self.screen, dt, self.rect)


    def run(self, name=None):
        pygame.display.set_caption(name or "CONTEXT WINDOW")
        while self.running:
            dt = self.clock.tick(self.fps) / 1000
            self.screen.fill(self.colors.get("background", (0, 0, 0)))
            for event in pygame.event.get():
                self.context.update_binds(event)
                if event.type == pygame.QUIT:
                    self.running = False
                    break

            self.update(dt)
            self.draw(dt)
            pygame.display.flip()
        pygame.quit()


log("System", "RUNNING", "ContextAPI loaded successfully!")
# batata
