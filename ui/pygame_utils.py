import pygame
import os
import pickle
import hashlib

_BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FONT_PATH = os.path.join(_BASE_DIR, "fuente_letra", "Pokemon_Classic.ttf")

# Carpeta para caché de GIFs
_CACHE_DIR = os.path.join(_BASE_DIR, "cache")
os.makedirs(_CACHE_DIR, exist_ok=True)

_global_img_cache = {}
_global_gif_cache = {}
_global_preloaded = False
_global_preloaded_gifs = {}

BG       = (26,  26,  46)
BG2      = (22,  33,  62)
BG3      = (15,  52,  96)
ACCENT   = (233, 69,  96)
GOLD     = (245, 166, 35)
TEXTCOL  = (226, 232, 240)
TEXT2    = (148, 163, 184)
GREEN    = (74,  222, 128)
RED_COL  = (248, 113, 113)
BLUE_C   = (96,  165, 250)
WHITE    = (255, 255, 255)
BLACK    = (0,   0,   0)
DARK     = (10,  10,  20)
PANEL_BG = (42,  42,  62)

PKM_BLACK  = (40,  40,  40)
PKM_RED    = (200, 40,  40)
PKM_BLUE   = (30,  60,  200)
PKM_GREEN  = (20,  140, 40)
PKM_GOLD   = (180, 120, 0)
PKM_GRAY   = (100, 100, 100)
PKM_WHITE  = (250, 250, 250)

TYPE_COLORS = {
    "Dragon":    ((111, 53,  252), WHITE),
    "Fantasma":  ((115, 87,  151), WHITE),
    "Tierra":    ((226, 191, 101), PKM_BLACK),
    "Fuego":     ((255, 156, 84),  PKM_BLACK),
    "Agua":      ((99,  144, 240), WHITE),
    "Planta":    ((122, 199, 76),  PKM_BLACK),
    "Electrico": ((247, 208, 44),  PKM_BLACK),
    "Hielo":     ((150, 217, 214), PKM_BLACK),
    "Psiquico":  ((249, 85,  135), WHITE),
    "Lucha":     ((194, 46,  40),  WHITE),
    "Acero":     ((183, 183, 206), PKM_BLACK),
    "Volador":   ((169, 143, 243), WHITE),
    "Hada":      ((214, 133, 173), WHITE),
    "Bicho":     ((166, 185, 26),  PKM_BLACK),
    "Veneno":    ((163, 62,  161), WHITE),
    "Siniestro": ((112, 87,  70),  WHITE),
    "Normal":    ((168, 167, 122), PKM_BLACK),
    "Roca":      ((182, 161, 54),  PKM_BLACK),
}

STATUS_COLORS = {
    "burn":      (255, 112, 67),
    "poison":    (156, 39,  176),
    "toxic":     (106, 13,  173),
    "paralyze":  (255, 193, 7),
    "sleep":     (96,  125, 139),
    "freeze":    (128, 222, 234),
    "infectado": (76,  175, 80),
}

STATUS_LABELS = {
    "burn":      "QMD",
    "poison":    "VNO",
    "toxic":     "VNG",
    "paralyze":  "PAR",
    "sleep":     "DRM",
    "freeze":    "CON",
    "infectado": "INF",
}

HP_GREEN = (74,  222, 128)
HP_GOLD  = (245, 166, 35)
HP_RED   = (248, 113, 113)

HP_GREEN_PKM = (50,  180, 50)
HP_GOLD_PKM  = (220, 160, 0)
HP_RED_PKM   = (220, 40,  40)

_font_cache: dict = {}

def get_font(size: int, bold: bool = False, classic: bool = False) -> pygame.font.Font:
    key = (size, bold, classic)
    if key not in _font_cache:
        if classic and os.path.exists(_FONT_PATH):
            try:
                f = pygame.font.Font(_FONT_PATH, size)
                if bold:
                    f.set_bold(True)
                _font_cache[key] = f
                return f
            except Exception:
                pass
        name = pygame.font.match_font("couriernew,courier,freemono,dejavusansmono,monospace")
        try:
            f = pygame.font.Font(name, size) if name else pygame.font.SysFont("monospace", size, bold=bold)
            if bold:
                f.set_bold(True)
            _font_cache[key] = f
        except Exception:
            _font_cache[key] = pygame.font.SysFont("monospace", size, bold=bold)
    return _font_cache[key]

def pkm_font(size: int) -> pygame.font.Font:
    return get_font(size, classic=True)

def draw_rect_alpha(surface: pygame.Surface, color: tuple,
                    rect: pygame.Rect, alpha: int = 180, radius: int = 0):
    s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(s, (*color[:3], alpha), s.get_rect(), border_radius=radius)
    surface.blit(s, rect.topleft)

def draw_text(surface: pygame.Surface, text: str, x: int, y: int,
              font: pygame.font.Font, color=TEXTCOL,
              center=False, right=False) -> pygame.Rect:
    rendered = font.render(text, True, color)
    rect = rendered.get_rect()
    if center:
        rect.centerx = x
        rect.y = y
    elif right:
        rect.right = x
        rect.y = y
    else:
        rect.x = x
        rect.y = y
    surface.blit(rendered, rect)
    return rect

def draw_hp_bar(surface: pygame.Surface, rect: pygame.Rect,
                pct: float, dark_bg: bool = True):
    bg_col = (50, 50, 50) if dark_bg else (180, 180, 180)
    pygame.draw.rect(surface, bg_col, rect, border_radius=3)
    if pct > 0:
        if dark_bg:
            color = HP_GREEN if pct > 0.5 else (HP_GOLD if pct > 0.2 else HP_RED)
        else:
            color = HP_GREEN_PKM if pct > 0.5 else (HP_GOLD_PKM if pct > 0.2 else HP_RED_PKM)
        filled = pygame.Rect(rect.x, rect.y, max(2, int(rect.width * pct)), rect.height)
        pygame.draw.rect(surface, color, filled, border_radius=3)
    pygame.draw.rect(surface, PKM_BLACK, rect, 2, border_radius=3)

def load_image_pil(path: str, size: tuple, keep_alpha: bool = True) -> pygame.Surface | None:
    key = (path, size)
    if key in _global_img_cache:
        return _global_img_cache[key]
    try:
        from PIL import Image
        mode = "RGBA" if keep_alpha else "RGB"
        img = Image.open(path).convert(mode)
        img = img.resize(size, Image.LANCZOS)
        raw  = img.tobytes()
        fmt  = "RGBA" if keep_alpha else "RGB"
        surf = pygame.image.fromstring(raw, size, fmt)
        _global_img_cache[key] = surf
        return surf
    except Exception:
        return None

def load_bg_image(path: str, size: tuple) -> pygame.Surface | None:
    return load_image_pil(path, size, keep_alpha=False)

def _process_gif_frames(path: str, size: tuple) -> list:
    try:
        from PIL import Image
        
        gif = Image.open(path)
        frames = []
        target_w, target_h = size
        
        total_frames = gif.n_frames
        print(f"  Procesando {path}: {total_frames} frames")
        
        for i in range(total_frames):
            gif.seek(i)
            duration = gif.info.get("duration", 100)  
            if duration < 30: 
                duration = 100
            
            frame = gif.convert("RGBA")
            
            original_w, original_h = frame.size
            scale = min(target_w / original_w, target_h / original_h)
            new_w = max(1, int(original_w * scale))
            new_h = max(1, int(original_h * scale))
            
            frame_resized = frame.resize((new_w, new_h), Image.LANCZOS)
            
            final = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
            paste_x = (target_w - new_w) // 2
            paste_y = (target_h - new_h) // 2
            final.paste(frame_resized, (paste_x, paste_y))
            
            raw = final.tobytes()
            surf = pygame.image.fromstring(raw, (target_w, target_h), "RGBA")
            frames.append((surf, duration))
            
            if i % 10 == 0:
                pygame.event.pump()
        
        if not frames and total_frames > 0:
            gif.seek(0)
            frame = gif.convert("RGBA").resize((target_w, target_h), Image.LANCZOS)
            raw = frame.tobytes()
            surf = pygame.image.fromstring(raw, (target_w, target_h), "RGBA")
            frames = [(surf, 1000)]
        
        print(f"  GIF cargado: {len(frames)} frames")
        return frames
    except Exception as e:
        print(f"Error procesando GIF {path}: {e}")
        return []
    
def load_gif_frames_with_cache(path: str, size: tuple) -> list:
    cache_key = hashlib.md5(f"{path}_{size[0]}_{size[1]}".encode()).hexdigest()
    cache_file = os.path.join(_CACHE_DIR, f"gif_{cache_key}.pickle")

    # Las Surfaces de pygame no son picklables: se guardan como bytes RGBA
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'rb') as f:
                raw_frames = pickle.load(f)
            if raw_frames:  # caché vacía = procesamiento fallido: reintentar
                return [(pygame.image.fromstring(raw, fsize, "RGBA"), dur)
                        for raw, fsize, dur in raw_frames]
        except Exception:
            pass  # caché corrupta o de formato viejo: reprocesar

    frames = _process_gif_frames(path, size)

    if frames:
        try:
            raw_frames = [(pygame.image.tostring(surf, "RGBA"), surf.get_size(), dur)
                          for surf, dur in frames]
            with open(cache_file, 'wb') as f:
                pickle.dump(raw_frames, f)
        except Exception:
            pass

    return frames

class GifSprite:
    def __init__(self, path: str, size: tuple):
        self.frames    = load_gif_frames_with_cache(path, size)
        self._idx      = 0
        self._t_next   = 0
        self._size     = size
        self._fallback = None
        self._current  = None

    def is_valid(self) -> bool:
        return len(self.frames) > 0

    def get_frame(self) -> "pygame.Surface | None":
        if not self.frames:
            return self._fallback
        now = pygame.time.get_ticks()
        if now >= self._t_next:
            surf, duration = self.frames[self._idx]
            self._idx    = (self._idx + 1) % len(self.frames)
            self._t_next = now + duration
            self._current = surf
        if not hasattr(self, "_current") or self._current is None:
            self._current = self.frames[0][0]
        return self._current

    def reset(self):
        self._idx    = 0
        self._t_next = pygame.time.get_ticks()
        if hasattr(self, "_current"):
            del self._current

    def set_fallback(self, surf):
        self._fallback = surf


def load_pokemon_gif(path: str, size: tuple) -> "GifSprite":
    return GifSprite(path, size)

def preload_all_resources():
    global _global_preloaded
    
    if _global_preloaded:
        return
    
    print("Precargando recursos esenciales...")
    
    img_dirs = [
        ("images", "Logo_Pokefisi.png"),
        ("images", "Fondo_Menu.png"),
        ("images", "Fondos", "Fondo_Batalla.jfif"),
        ("images", "Cuadro_Texto", "Fondo_Vida.png"),
        ("images", "Cuadro_Texto", "Cuadro_stats.png"),
        ("images", "Vivo_Poke.png"),
        ("images", "Muerto_Poke.png"),
    ]
    
    for parts in img_dirs:
        path = os.path.join(_BASE_DIR, *parts)
        if os.path.exists(path):
            load_image_pil(path, (100, 100), keep_alpha=True)
    
    print("Precarga esencial completada!")
    _global_preloaded = True


def get_preloaded_gif(name: str, target_size: tuple = None) -> 'GifSprite':
    name_lower = name.lower()
    
    if target_size is None:
        target_size = (180, 180)
    
    cache_key = f"{name_lower}_{target_size[0]}x{target_size[1]}"
    
    if cache_key in _global_preloaded_gifs:
        return _global_preloaded_gifs[cache_key]

    # Mega Pikachu vive en su propia carpeta, fuera de Gif_Pokemon
    if name_lower in ("mega_pikachu", "mega pikachu"):
        mega_path = os.path.join(_BASE_DIR, "images", "Mega_Pikachu", "Mega_Pikachu.gif")
        if os.path.exists(mega_path):
            gif = load_pokemon_gif(mega_path, target_size)
            _global_preloaded_gifs[cache_key] = gif
            return gif
        return None

    gif_dir = os.path.join(_BASE_DIR, "images", "Gif_Pokemon")
    if not os.path.exists(gif_dir):
        return None
    
    for f in os.listdir(gif_dir):
        if f.lower().endswith('.gif'):
            file_name = f[3:].rsplit('.', 1)[0].lower()
            if file_name == name_lower:
                full = os.path.join(gif_dir, f)
                gif = load_pokemon_gif(full, target_size)
                _global_preloaded_gifs[cache_key] = gif
                return gif
    
    return None


def limpiar_cache_gifs():
    import shutil
    if os.path.exists(_CACHE_DIR):
        shutil.rmtree(_CACHE_DIR)
        os.makedirs(_CACHE_DIR)
        print("Caché de GIFs limpiada")

class Button:
    def __init__(self, rect: pygame.Rect, text: str, font: pygame.font.Font,
                 bg=None, fg=PKM_BLACK, hover_bg=None, disabled=False,
                 radius=0, tag=None, border_col=PKM_BLACK, border_w=0,
                 text_align="center"):
        self.rect      = rect
        self.text      = text
        self.font      = font
        self.bg        = bg
        self.fg        = fg
        self.hover_bg  = hover_bg or ((min(255,bg[0]+30), min(255,bg[1]+30), min(255,bg[2]+30)) if bg else None)
        self.disabled  = disabled
        self.radius    = radius
        self.tag       = tag
        self.border_col = border_col
        self.border_w  = border_w
        self.text_align = text_align
        self._hovered  = False

    def handle_event(self, event) -> bool:
        if self.disabled:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return self.rect.collidepoint(event.pos)
        return False

    def update_hover(self, mouse_pos):
        self._hovered = self.rect.collidepoint(mouse_pos) and not self.disabled

    def draw(self, surface: pygame.Surface):
        if self.bg is not None:
            bg = (max(0,self.bg[0]-30), max(0,self.bg[1]-30), max(0,self.bg[2]-30)) if self.disabled \
                 else (self.hover_bg if self._hovered else self.bg)
            pygame.draw.rect(surface, bg, self.rect, border_radius=self.radius)
        if self.border_w > 0:
            border_c = (120,120,120) if self.disabled else self.border_col
            pygame.draw.rect(surface, border_c, self.rect, self.border_w, border_radius=self.radius)
        fg = PKM_GRAY if self.disabled else self.fg
        display_text = self.text
        rendered = self.font.render(display_text, True, fg)
        r = rendered.get_rect()
        if self.text_align == "center":
            r.center = self.rect.center
        elif self.text_align == "left":
            r.midleft = (self.rect.x + 8, self.rect.centery)
        surface.blit(rendered, r)

    @property
    def hovered(self):
        return self._hovered

class TextLog:
    MAX_LINES = 120

    def __init__(self, rect: pygame.Rect, font: pygame.font.Font,
                 bg=None, fg=PKM_BLACK, line_height: int = 0):
        self.rect        = rect
        self.font        = font
        self.bg          = bg
        self.fg          = fg
        self.line_h      = line_height or (font.get_height() + 4)
        self.lines: list = []
        self.scroll      = 0

    def add(self, text: str, color=None):
        color = color or self.fg
        max_w = self.rect.width - 20
        words = text.split(' ')
        current = ''
        wrapped = []
        for word in words:
            test = current + (' ' if current else '') + word
            if self.font.size(test)[0] <= max_w:
                current = test
            else:
                if current:
                    wrapped.append(current)
                current = word
        if current:
            wrapped.append(current)
        for line in wrapped:
            self.lines.append((line, color))
        if len(self.lines) > self.MAX_LINES:
            self.lines = self.lines[-self.MAX_LINES:]
        visible = max(1, (self.rect.height - 16) // self.line_h)
        self.scroll = max(0, len(self.lines) - visible)

    def handle_scroll(self, event):
        if event.type == pygame.MOUSEWHEEL:
            if self.rect.collidepoint(pygame.mouse.get_pos()):
                self.scroll = max(0, self.scroll - event.y)

    def draw(self, surface: pygame.Surface):
        if self.bg:
            pygame.draw.rect(surface, self.bg, self.rect)
        clip = surface.get_clip()
        inner = self.rect.inflate(-8, -8)
        surface.set_clip(inner)
        visible = max(1, (self.rect.height - 16) // self.line_h)
        start   = self.scroll
        end     = min(start + visible + 1, len(self.lines))
        y = self.rect.y + 10
        for i in range(start, end):
            text, color = self.lines[i]
            rendered = self.font.render(text, True, color)
            surface.blit(rendered, (self.rect.x + 10, y))
            y += self.line_h
        surface.set_clip(clip)


def draw_pokemon_dots(surface, team, active_idx, x, y, size=10, gap=3):
    for i, p in enumerate(team):
        cx = x + i * (size + gap) + size // 2
        cy = y + size // 2
        color = (68, 68, 68) if p.fainted else HP_GREEN_PKM
        border = (180, 120, 0) if i == active_idx else PKM_BLACK
        pygame.draw.circle(surface, color, (cx, cy), size // 2)
        pygame.draw.circle(surface, border, (cx, cy), size // 2, 2)