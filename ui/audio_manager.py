import pygame
import os

_current_track = None

def _music_path(filename):
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "sonidos", filename)

def play(filename, loops=-1):
    global _current_track
    if _current_track == filename:
        return
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        path = _music_path(filename)
        if not os.path.exists(path):
            return
        pygame.mixer.music.load(path)
        pygame.mixer.music.set_volume(0.6)
        pygame.mixer.music.play(loops)
        _current_track = filename
    except Exception:
        pass

def stop():
    global _current_track
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
    _current_track = None

def play_menu():
    play("Main_Theme.ogg")

def play_battle(ai_level, ai2_level=None):
    max_level = max(ai_level, ai2_level or 0)
    if max_level >= 4:
        play("Batalla_Legend.ogg")
    elif max_level >= 3:
        play("Batalla_Final.ogg")
    else:
        play("Batalla_Normal.ogg")