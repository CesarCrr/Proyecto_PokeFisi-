# main.py — Punto de entrada PokeFisi (Pygame)
# Ventana redimensionable con soporte de pantalla completa (F11 o doble clic en barra)

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pygame
from ui.menu_inicio_pg         import PokemonMenu
from ui.interfaz_pg            import PokemonGUI
from ui.audio_manager          import play_menu, play_battle, stop
from ui.interfaz_simulacion_pg import PokemonSimulationGUI
from ui.pygame_utils           import preload_all_resources


BASE_W = 900
BASE_H = 660
FPS    = 60
TITLE  = "PokeFisi"


class PokemonApp:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)

        # RESIZABLE permite redimensionar y muestra botones nativos de la ventana
        # (minimizar, maximizar, cerrar) en todos los sistemas operativos.
        self.screen = pygame.display.set_mode(
            (BASE_W, BASE_H),
            pygame.RESIZABLE
        )
        self.clock       = pygame.time.Clock()
        self._fullscreen = False
        
        print("Iniciando PokeFisi...")
        preload_all_resources() 
        print("Recursos precargados!")

        # Icono
        base = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base, "images", "Logo_Pokefisi.png")
        if os.path.exists(icon_path):
            try:
                from PIL import Image
                img  = Image.open(icon_path).convert("RGBA").resize((32, 32))
                raw  = img.tobytes()
                icon = pygame.image.fromstring(raw, (32, 32), "RGBA")
                pygame.display.set_icon(icon)
            except Exception:
                pass

        self.current_scene = None
        self._show_menu()

    # ── Escenas ───────────────────────────────────────────────────────────
    def _show_menu(self):
        play_menu()
        self.current_scene = PokemonMenu(self.screen, self._start_battle)

    def _start_battle(self, mode, ai_level, ai2_level, battle_type):
        play_battle(ai_level, ai2_level if mode == 'simulation' else None)
        if mode == "simulation":
            self.current_scene = PokemonSimulationGUI(
                self.screen,
                ai_level=ai_level,
                ai2_level=ai2_level,
                battle_type=battle_type,
                on_exit_callback=self._show_menu,
            )
        else:
            self.current_scene = PokemonGUI(
                self.screen,
                ai_level=ai_level,
                battle_type=battle_type,
                on_exit_callback=self._show_menu,
            )

    # ── Pantalla completa ─────────────────────────────────────────────────
    def _toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        if self._fullscreen:
            self.screen = pygame.display.set_mode(
                (0, 0), pygame.FULLSCREEN | pygame.RESIZABLE)
        else:
            self.screen = pygame.display.set_mode(
                (BASE_W, BASE_H), pygame.RESIZABLE)
        pygame.display.flip()  # forzar que pygame actualice el tamaño real
        W, H = self.screen.get_size()  # leer tamaño real DESPUÉS del flip
        if self.current_scene:
            self.current_scene.screen = self.screen
            self.current_scene.W = W
            self.current_scene.H = H
            if hasattr(self.current_scene, '_recalc_layout'):
                self.current_scene._recalc_layout()
            if hasattr(self.current_scene, '_rebuild_current_step'):
                self.current_scene._rebuild_current_step()
            if hasattr(self.current_scene, '_load_assets'):
                self.current_scene._load_assets()
            if hasattr(self.current_scene, '_compute_layout'):
                self.current_scene._compute_layout()
                if hasattr(self.current_scene, '_refresh_ui'):
                    self.current_scene._refresh_ui()

    # ── Loop principal ────────────────────────────────────────────────────
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                # F11 → pantalla completa / ventana
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                    self._toggle_fullscreen()
                    continue

                # Redimensión de ventana (usuario arrastra bordes o maximiza)
                if event.type == pygame.VIDEORESIZE:
                    # En modo ventana normal actualizamos el tamaño
                    if not self._fullscreen:
                        self.screen = pygame.display.set_mode(
                            (event.w, event.h), pygame.RESIZABLE)
                    # Notificar a la escena
                    if self.current_scene:
                        self.current_scene.screen = self.screen
                        self.current_scene.W = event.w
                        self.current_scene.H = event.h
                        if hasattr(self.current_scene, '_recalc_layout'):
                            self.current_scene._recalc_layout()
                        if hasattr(self.current_scene, '_rebuild_current_step'):
                            self.current_scene._rebuild_current_step()
                        if hasattr(self.current_scene, '_compute_layout'):
                            self.current_scene._compute_layout()
                            if hasattr(self.current_scene, '_refresh_ui'):
                                self.current_scene._refresh_ui()
                    continue

                if self.current_scene:
                    self.current_scene.handle_event(event)

            if self.current_scene:
                if hasattr(self.current_scene, 'update'):
                    self.current_scene.update()
                self.current_scene.draw()

            pygame.display.flip()
            self.clock.tick(FPS)


def main():
    app = PokemonApp()
    app.run()


if __name__ == "__main__":
    main()