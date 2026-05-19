import pygame
import os

from ui.pygame_utils import (
    PKM_BLACK, PKM_RED, PKM_BLUE, PKM_GREEN, PKM_GOLD, PKM_WHITE,
    get_font, pkm_font, draw_rect_alpha, draw_text, Button,
    load_image_pil, load_bg_image,
)
from utiles.estadisticas import obtener_estadisticas, resetear_estadisticas

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_IMGS     = os.path.join(_BASE_DIR, "images")

SEL_COL  = (30, 80, 200)  
NORM_COL = PKM_BLACK
GRAY_COL = (130, 130, 130)


class PokemonMenu:
    STEP_MODE   = 1
    STEP_CONFIG = 2
    STEP_STATS  = 3

    def __init__(self, screen: pygame.Surface, on_start_callback):
        self.screen   = screen
        self.callback = on_start_callback
        self.W, self.H = screen.get_size()

        self.step        = self.STEP_MODE
        self.modo        = "pve"
        self.ai_level    = 1
        self.ai2_level   = 1
        self.battle_type = 4
        self._confirm_reset = False

        self._load_assets()
        self._recalc_layout()
        self._build_step_mode()

    # ── Assets ────────────────────────────────────────────────────────────
    def _load_assets(self):
        W, H = self.W, self.H

        # Fondo
        bg_path = os.path.join(_IMGS, "Fondo_Menu.png")
        if not os.path.exists(bg_path):
            bg_path = os.path.join(_IMGS, "Fondos", "Fondo_Menu.jpg")
        self.bg_surf = load_bg_image(bg_path, (W, H))

        # Logo: alto fijo 150px, ancho proporcional (ratio 3953:3508 ≈ 1.127)
        logo_h = min(int(H * 0.33), 220)
        logo_w = int(logo_h * (3953 / 3508))
        logo_path = os.path.join(_IMGS, "Logo_Pokefisi.png")
        self.logo_surf = load_image_pil(logo_path, (logo_w, logo_h), keep_alpha=True)

        # Cuadro_stats — se recarga al cambiar tamaño de ventana
        self._load_cuadro()

    def _load_cuadro(self):
        """Carga/recarga el Cuadro_stats al tamaño correcto para la ventana actual."""
        W, H = self.W, self.H
        logo_h   = self.logo_surf.get_height() if self.logo_surf else 150
        logo_bot = 12 + logo_h + 6        # donde termina el logo

        # Cuadro ocupa 58% del ancho, altura hasta casi el fondo
        panel_w = int(W * 0.58)
        panel_h = H - logo_bot - 8        # 8px margen inferior
        # Mínimo viable
        panel_h = max(panel_h, 200)
        panel_w = max(panel_w, 300)

        self.panel_w  = panel_w
        self.panel_h  = panel_h
        self.logo_bot = logo_bot

        cuadro_path = os.path.join(_IMGS, "Cuadro_Texto", "Cuadro_stats.png")
        self.cuadro_surf = load_image_pil(
            cuadro_path, (panel_w, panel_h), keep_alpha=True)

    def _recalc_layout(self):
        """Recalcula todos los rectángulos de layout al tamaño actual."""
        W, H = self.W, self.H
        self._load_cuadro()

    # ── Rectángulos calculados ────────────────────────────────────────────
    def _get_cuadro_rect(self) -> pygame.Rect:
        cx = self.W // 2
        return pygame.Rect(cx - self.panel_w // 2,
                           self.logo_bot,
                           self.panel_w,
                           self.panel_h)

    def _get_inner(self) -> pygame.Rect:
        cr     = self._get_cuadro_rect()
        borde  = int(self.panel_w * 0.04)
        borde_v = max(14, int(self.panel_h * 0.048))
        return pygame.Rect(cr.x + borde,
                           cr.y + borde_v,
                           cr.width  - borde * 2,
                           cr.height - borde_v * 2)

    # ── Builders de pasos ────────────────────────────────────────────────
    def _build_step_mode(self):
        self.step = self.STEP_MODE
        self.buttons = []
        self._confirm_reset = False
        inner  = self._get_inner()
        f      = pkm_font(13)
        line_h = max(36, int(inner.height * 0.13))
        gap    = max(10, int(inner.height * 0.04))
        lx     = inner.x + 16
        # Opciones empiezan al 30% del inner
        y0     = inner.y + int(inner.height * 0.28)

        for tag, label in [("mode_pve","Jugador vs IA"),
                            ("mode_sim","IA vs IA"),
                            ("stats",  "Ver Estadisticas")]:
            r = pygame.Rect(lx, y0, inner.width - 32, line_h)
            self.buttons.append(Button(r, label, f, tag=tag, text_align="left"))
            y0 += line_h + gap

        # Botón "Siguiente" al fondo del inner
        y_next = inner.y + inner.height - line_h - 10
        self.buttons.append(Button(
            pygame.Rect(lx, y_next, inner.width - 32, line_h),
            "Siguiente", f, tag="next", text_align="left"))

    def _build_step_config(self):
        self.step = self.STEP_CONFIG
        self.buttons = []
        inner  = self._get_inner()
        f      = pkm_font(13)
        line_h = max(34, int(inner.height * 0.11))
        gap    = max(8,  int(inner.height * 0.035))
        lx     = inner.x + 16
        is_sim = (self.modo == "simulation")
        y      = inner.y + int(inner.height * 0.20)
        half   = (inner.width - 32) // 2

        # IA 1
        quarter = (inner.width - 32) // 4
        for k, (tag, label) in enumerate([("ai1_1","Nivel 1"), ("ai1_2","Nivel 2"),
                                          ("ai1_3","Nivel 3")]):
            xi = lx + k * (quarter + 2)
            self.buttons.append(Button(pygame.Rect(xi, y, quarter - 2, line_h),
                                       label, f, tag=tag, text_align="left"))
        y += line_h + gap * 2

        if is_sim:
            quarter = (inner.width - 32) // 4
            for k, (tag, label) in enumerate([("ai2_1","Nivel 1"), ("ai2_2","Nivel 2"),
                                              ("ai2_3","Nivel 3"), ("ai2_4","Nivel 4")]):
                xi = lx + k * (quarter + 2)
                self.buttons.append(Button(pygame.Rect(xi, y, quarter - 2, line_h),
                                           label, f, tag=tag, text_align="left"))
            y += line_h + gap * 2

        # Tipo de combate
        for tag, label in [("bt_4","4 vs 4"), ("bt_3","3 vs 3")]:
            xi = lx if tag == "bt_4" else lx + half + 8
            self.buttons.append(Button(pygame.Rect(xi, y, half - 4, line_h),
                                       label, f, tag=tag, text_align="left"))
        y += line_h + gap * 3

        # Volver / Empezar
        bw = (inner.width - 32) // 2
        lbl = "Observar" if is_sim else "Empezar"
        self.buttons.append(Button(pygame.Rect(lx,        y, bw, line_h),
                                   "Volver", f, tag="back", text_align="left"))
        self.buttons.append(Button(pygame.Rect(lx+bw+8,   y, bw, line_h),
                                   lbl,      f, tag="start", text_align="left"))

    def _build_step_stats(self):
        self.step = self.STEP_STATS
        self.buttons = []
        self._confirm_reset = False
        inner  = self._get_inner()
        f      = pkm_font(13)
        line_h = max(34, int(inner.height * 0.11))
        lx     = inner.x + 16
        bw     = (inner.width - 32) // 2
        y      = inner.y + inner.height - line_h - 10

        self.buttons.append(Button(pygame.Rect(lx,       y, bw, line_h),
                                   "Reiniciar", f, tag="reset_stats", text_align="left"))
        self.buttons.append(Button(pygame.Rect(lx+bw+8,  y, bw, line_h),
                                   "Cerrar", f, tag="close_stats", text_align="left"))

    # ── Event handling ───────────────────────────────────────────────────
    def handle_event(self, event):
        # Redimensión de ventana
        if event.type == pygame.VIDEORESIZE:
            self.W, self.H = event.w, event.h
            self._recalc_layout()
            self._rebuild_current_step()
            return

        mouse = pygame.mouse.get_pos()
        for btn in self.buttons:
            btn.update_hover(mouse)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self.buttons:
                if btn.handle_event(event):
                    self._on_click(btn.tag)
                    return

    def _rebuild_current_step(self):
        if   self.step == self.STEP_MODE:   self._build_step_mode()
        elif self.step == self.STEP_CONFIG: self._build_step_config()
        elif self.step == self.STEP_STATS:  self._build_step_stats()

    def _on_click(self, tag):
        if   tag == "mode_pve":  self.modo = "pve";        self._build_step_mode()
        elif tag == "mode_sim":  self.modo = "simulation"; self._build_step_mode()
        elif tag == "stats":     self._build_step_stats()
        elif tag == "next":      self._build_step_config()
        elif tag == "back":      self._build_step_mode()
        elif tag == "start":     self.callback(self.modo, self.ai_level, self.ai2_level, self.battle_type)
        elif tag == "ai1_1":     self.ai_level = 1;    self._build_step_config()
        elif tag == "ai1_2":     self.ai_level = 2;    self._build_step_config()
        elif tag == "ai1_3":     self.ai_level = 3;    self._build_step_config()
        elif tag == "ai1_4":     self.ai_level = 4;    self._build_step_config()
        elif tag == "ai2_1":     self.ai2_level = 1;   self._build_step_config()
        elif tag == "ai2_2":     self.ai2_level = 2;   self._build_step_config()
        elif tag == "ai2_3":     self.ai2_level = 3;   self._build_step_config()
        elif tag == "ai2_4":     self.ai2_level = 4;   self._build_step_config()
        elif tag == "bt_4":      self.battle_type = 4; self._build_step_config()
        elif tag == "bt_3":      self.battle_type = 3; self._build_step_config()
        elif tag == "close_stats": self._build_step_mode()
        elif tag == "reset_stats":
            self._confirm_reset = True
            self._add_confirm_buttons()
        elif tag == "confirm_yes":
            resetear_estadisticas(); self._build_step_stats()
        elif tag == "confirm_no":
            self._confirm_reset = False; self._build_step_stats()

    def _add_confirm_buttons(self):
        inner  = self._get_inner()
        f      = pkm_font(13)
        line_h = max(34, int(inner.height * 0.11))
        lx     = inner.x + 16
        bw     = (inner.width - 32) // 2
        y      = inner.y + inner.height - line_h * 2 - 18
        self.buttons = [b for b in self.buttons
                        if b.tag not in ("reset_stats","close_stats","confirm_yes","confirm_no")]
        self.buttons.append(Button(pygame.Rect(lx,       y, bw, line_h),
                                   "Si, borrar", f, tag="confirm_yes", text_align="left"))
        self.buttons.append(Button(pygame.Rect(lx+bw+8,  y, bw, line_h),
                                   "Cancelar",   f, tag="confirm_no",  text_align="left"))

    # ── Dibujo ───────────────────────────────────────────────────────────
    def draw(self):
        W, H = self.screen.get_size()
        # Detectar si la ventana cambió de tamaño
        if (W, H) != (self.W, self.H):
            self.W, self.H = W, H
            self._recalc_layout()
            self._rebuild_current_step()

        # 1. Fondo
        bg = load_bg_image(
            os.path.join(_IMGS, "Fondo_Menu.png"), (W, H)) or self.bg_surf
        if bg:
            self.screen.blit(bg, (0, 0))
        else:
            self.screen.fill((26, 26, 46))

        # 2. Logo centrado arriba
        if self.logo_surf:
            lx = W // 2 - self.logo_surf.get_width() // 2
            self.screen.blit(self.logo_surf, (lx, 12))

        # 3. Cuadro de stats
        cr = self._get_cuadro_rect()
        if self.cuadro_surf:
            self.screen.blit(self.cuadro_surf, cr.topleft)

        # 4. Contenido del paso
        if   self.step == self.STEP_MODE:   self._draw_mode()
        elif self.step == self.STEP_CONFIG: self._draw_config()
        elif self.step == self.STEP_STATS:  self._draw_stats()

        # 5. Opciones con cursor
        self._draw_options()

    # ── Dibujado de opciones ─────────────────────────────────────────────
    def _draw_options(self):
        """Dibuja cada opción con '>' en azul si está seleccionada."""
        f = pkm_font(13)
        for btn in self.buttons:
            sel    = self._is_selected(btn.tag)
            hover  = btn.hovered
            active = sel or hover
            col    = SEL_COL if active else NORM_COL
            cursor = "> " if active else "  "
            text   = cursor + btn.text
            rendered = f.render(text, True, col)
            r = rendered.get_rect(midleft=(btn.rect.x, btn.rect.centery))
            # Asegurar que no se salga de la pantalla
            if r.right > self.W - 4:
                r.right = self.W - 4
            if r.bottom > self.H - 4:
                r.bottom = self.H - 4
            self.screen.blit(rendered, r)

    def _is_selected(self, tag) -> bool:
        return (
            (tag == "mode_pve" and self.modo == "pve") or
            (tag == "mode_sim" and self.modo == "simulation") or
            (tag == "ai1_1"   and self.ai_level    == 1) or
            (tag == "ai1_2"   and self.ai_level    == 2) or
            (tag == "ai1_3"   and self.ai_level    == 3) or
            (tag == "ai1_4"   and self.ai_level    == 4) or
            (tag == "ai2_1"   and self.ai2_level   == 1) or
            (tag == "ai2_2"   and self.ai2_level   == 2) or
            (tag == "ai2_3"   and self.ai2_level   == 3) or
            (tag == "ai2_4"   and self.ai2_level   == 4) or
            (tag == "bt_4"    and self.battle_type == 4) or
            (tag == "bt_3"    and self.battle_type == 3)
        )

    # ── Contenido por paso ───────────────────────────────────────────────
    def _draw_mode(self):
        inner   = self._get_inner()
        f_title = pkm_font(15)
        draw_text(self.screen, "Seleccione el modo de juego",
                  inner.centerx, inner.y + 10, f_title, PKM_BLACK, center=True)

    def _draw_config(self):
        inner   = self._get_inner()
        f_title = pkm_font(15)
        f_label = pkm_font(8)
        is_sim  = (self.modo == "simulation")
        btag    = {b.tag: b for b in self.buttons}

        draw_text(self.screen, "Configure la batalla",
                  inner.centerx, inner.y + 8, f_title, PKM_BLACK, center=True)

        _nv_map = {1:"Nivel 1",2:"Nivel 2",3:"Nivel 3 (MM)",4:"Nivel 4 (MM x10)"}
        lbl_ia1 = (f"IA 1: {_nv_map.get(self.ai_level,'')}"
                   if is_sim else
                   f"Nivel de IA: {_nv_map.get(self.ai_level,'')}")
        if "ai1_1" in btag:
            draw_text(self.screen, lbl_ia1,
                      inner.x + 16, btag["ai1_1"].rect.y - 16, f_label, PKM_BLACK)
        if is_sim and "ai2_1" in btag:
            draw_text(self.screen, "IA 2:",
                      inner.x + 16, btag["ai2_1"].rect.y - 16, f_label, PKM_BLACK)
        if "bt_4" in btag:
            draw_text(self.screen, "Tipo de Combate:",
                      inner.x + 16, btag["bt_4"].rect.y - 16, f_label, PKM_BLACK)

    def _draw_stats(self):
        inner   = self._get_inner()
        f_title = pkm_font(12)
        f_label = pkm_font(9)
        f_val   = pkm_font(8)
        stats   = obtener_estadisticas()

        draw_text(self.screen, "Estadisticas de IAs",
                  inner.centerx, inner.y + 6, f_title, PKM_BLACK, center=True)

        # Layout 2x2: dos IAs por fila para maximizar espacio
        pairs = [("ia1","IA Nv1"),("ia2","IA Nv2"),("ia3","IA Nv3 (MM)"),("ia4","IA Nv4 (MMx10)")]
        col_w = (inner.width - 8) // 2
        row_h = max(80, (inner.height - 30) // 2)
        for i, (clave, titulo) in enumerate(pairs):
            d     = stats.get(clave, {"victorias":0,"derrotas":0})
            v     = d.get("victorias", 0)
            de    = d.get("derrotas",  0)
            total = v + de
            pct   = f"{v/total*100:.0f}%" if total > 0 else "---"
            col   = i % 2
            row   = i // 2
            x     = inner.x + 8 + col * col_w
            y     = inner.y + 28 + row * row_h
            draw_text(self.screen, titulo,           x, y,    f_label, PKM_BLACK)
            draw_text(self.screen, f"Vic: {v}",       x, y+17, f_val,   PKM_GREEN)
            draw_text(self.screen, f"Der: {de}",      x, y+31, f_val,   PKM_RED)
            draw_text(self.screen, f"Win: {pct}",     x, y+45, f_val,   PKM_GOLD)

        if self._confirm_reset:
            f_conf = pkm_font(10)
            draw_text(self.screen, "Confirmar reinicio de estadisticas?",
                      inner.centerx,
                      inner.y + inner.height - max(28,int(inner.height*0.10))*2 - 30,
                      f_conf, PKM_RED, center=True)

