import pygame
import random
import os

from ui.pygame_utils import (
    BG, BG2, BG3, ACCENT, GOLD, TEXTCOL, TEXT2, GREEN, WHITE, BLACK,
    BLUE_C, RED_COL, PKM_BLACK, PKM_RED, PKM_BLUE, PKM_GREEN, PKM_GOLD,
    HP_GREEN_PKM, HP_GOLD_PKM, HP_RED_PKM,
    TYPE_COLORS, STATUS_COLORS, STATUS_LABELS,
    get_font, pkm_font, draw_rect_alpha, draw_text, draw_hp_bar,
    draw_pokemon_dots, Button, TextLog,
    load_image_pil, load_bg_image,
    GifSprite, load_pokemon_gif, get_preloaded_gif, preload_all_resources,
)
from datos.datos_pokemon import POKEMON_DB
from models.clase_batalla import BattlePokemon
from batalla.logica_batalla import resolve_turn, calculate_damage, get_priority
from batalla.peligros import apply_hazards_on_switch
from batalla.efectos import apply_move_effects
from utiles.funciones_auxiliares import rand, clamp
from ia.ia_levels import RandomAI, HeuristicAI, MinimaxAI
from utiles.estadisticas import registrar_resultado_pve

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_IMGS     = os.path.join(_BASE_DIR, "images")

SEL_COL  = (30, 80, 200)   
NORM_COL = PKM_BLACK       

VIDA_RATIO   = 2573/905   
CUADRO_RATIO = 2843/2135   
VIDA_SCALE   = 0.40        
SPRITE_H_MIN = 180         
CUADRO_H_PCT = 0.42       
CUADRO_H_MIN = 260         
LOG_DELAY_MS = 1100       

VIDA_H   = 100   
SPRITE_H = 240   
CUADRO_H = 290   

class PokemonGUI:
    STATE_MOVE_SEL_INIT = "move_sel_init"
    STATE_MOVE_SELECT   = "move_select"
    STATE_CONTINUE      = "continue"
    STATE_SWITCH_SELECT = "switch_select"
    STATE_WAITING       = "waiting"
    STATE_GAME_OVER     = "game_over"

    def __init__(self, screen, ai_level=1, battle_type=4, on_exit_callback=None):
        self.screen   = screen
        self.W, self.H = screen.get_size()
        self.ai_level = ai_level
        self.battle_type = battle_type
        self.on_exit_callback = on_exit_callback

        self.player_team     = []
        self.ai_team         = []
        self.player_active_idx = 0
        self.ai_active_idx   = 0
        self.turn            = 1
        self.ia              = None
        self.player_hazards  = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        self.ai_hazards      = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}

        self.buttons_locked     = False
        self.pending_switch     = False
        self.pending_switch_idx = None
        self.switch_source      = None
        self.pending_move_idx   = None
        self._auto_enfado_active = False
        self._game_over_active  = False
        self._procesando_derrotado = False
        self._pokemon_ia_pendiente = None
        self._ventana_cambio_abierta = False
        self._player_move_idx  = None
        self._ai_move_idx      = None
        self._player_force_idx = None
        self._log_lines_temp   = []
        self._continue_callback = None

        self._pending_log_lines = []
        self._log_delay_ms      = LOG_DELAY_MS
        self._last_log_time     = 0
        self._log_callback      = None

        self.pokemon_data_list     = []
        self.seleccion_movimientos = {}
        self.pokemon_actual        = 0
        self._move_vars            = []

        self._hp_anim = {
            "player": {"cur": 1.0, "tgt": 1.0, "animating": False, "speed": 0.025},
            "ai":     {"cur": 1.0, "tgt": 1.0, "animating": False, "speed": 0.025},
        }
        self._hp_event_queue = []

        self._dialog = None
        self.active_tab = "moves"
        self.state      = self.STATE_WAITING

        self._load_assets()
        self._compute_layout()
        self._start_new_game()

    def _load_assets(self):
        W, H = self.W, self.H

        bg_path = os.path.join(_IMGS, "Fondos", "Fondo_Batalla.jfif")
        self.bg_surf = load_bg_image(bg_path, (W, H))

        vida_w = int(W * 0.44)
        vida_h = int(vida_w / VIDA_RATIO)
        self.vida_w = vida_w
        self.vida_h = vida_h
        vida_path = os.path.join(_IMGS, "Cuadro_Texto", "Fondo_Vida.png")
        self.vida_surf = load_image_pil(vida_path, (vida_w, vida_h), keep_alpha=True)

        cuadro_w = W - 10
        cuadro_h = int(cuadro_w / CUADRO_RATIO)
        self.cuadro_w = cuadro_w
        self.cuadro_h = cuadro_h
        cuadro_path = os.path.join(_IMGS, "Cuadro_Texto", "Cuadro_stats.png")
        self.cuadro_surf = load_image_pil(cuadro_path, (cuadro_w, cuadro_h), keep_alpha=True)

        vivo_path   = os.path.join(_IMGS, "Vivo_Poke.png")
        muerto_path = os.path.join(_IMGS, "Muerto_Poke.png")
        self.icon_vivo   = load_image_pil(vivo_path,   (12, 12), keep_alpha=True)
        self.icon_muerto = load_image_pil(muerto_path, (12, 12), keep_alpha=True)

        self._poke_gifs = {}

    def _get_poke_gif(self, nombre, size=None):
        """Obtiene un GIF precargado, redimensionado si es necesario."""
        if size is None:
            size = (self.sprite_h, self.sprite_h)
        
        cache_key = f"{nombre}_{size[0]}x{size[1]}"
        if cache_key in self._poke_gifs:
            return self._poke_gifs[cache_key]
        
        gif = get_preloaded_gif(nombre, size)
        if gif:
            self._poke_gifs[cache_key] = gif
            return gif
        return None

    def _compute_layout(self):
        W, H = self.W, self.H
        margin = 5

        vida_w = int(W * 0.44)
        vida_h = int(vida_w / VIDA_RATIO)
        self.vida_w = vida_w
        self.vida_h = vida_h
        vida_path = os.path.join(_IMGS, "Cuadro_Texto", "Fondo_Vida.png")
        self.vida_surf = load_image_pil(vida_path, (vida_w, vida_h), keep_alpha=True)

        vida_y = margin
        self.rect_vida_player = pygame.Rect(margin, vida_y, vida_w, vida_h)
        self.rect_vida_ai     = pygame.Rect(W - vida_w - margin, vida_y, vida_w, vida_h)
        vida_bottom = vida_y + vida_h + 4

        cuadro_w = W - 10
        cuadro_h = max(CUADRO_H_MIN, int(H * 0.42))
        cuadro_top = H - cuadro_h - margin
        cuadro_path = os.path.join(_IMGS, "Cuadro_Texto", "Cuadro_stats.png")
        self.cuadro_surf = load_image_pil(cuadro_path, (cuadro_w, cuadro_h), keep_alpha=True)
        self.cuadro_w = cuadro_w
        self.cuadro_h = cuadro_h
        self.cuadro_y = cuadro_top
        self.rect_cuadro = pygame.Rect(margin, cuadro_top, cuadro_w, cuadro_h)

        sprite_zone_h = cuadro_top - vida_bottom - 4
        self.sprite_h = max(SPRITE_H_MIN, sprite_zone_h)
        self.rect_sprite_zone = pygame.Rect(0, vida_bottom, W, sprite_zone_h)
        sp_size = min(sprite_zone_h - 8, (W // 2) - 16)
        self.rect_sprite_player = pygame.Rect(
            W//4 - sp_size//2,
            vida_bottom + (sprite_zone_h - sp_size)//2,
            sp_size, sp_size)
        self.rect_sprite_ai = pygame.Rect(
            W*3//4 - sp_size//2,
            vida_bottom + (sprite_zone_h - sp_size)//2,
            sp_size, sp_size)

        borde   = max(10, int(self.cuadro_w * 0.036))
        borde_v = max(12, int(self.cuadro_h * 0.045))
        self.cuadro_inner = pygame.Rect(
            self.rect_cuadro.x + borde,
            self.rect_cuadro.y + borde_v,
            self.cuadro_w - borde*2,
            self.cuadro_h - borde_v*2
        )

        def vida_inner(rect):
            xi = rect.x + int(rect.width  * 0.12)
            yi = rect.y + int(rect.height * 0.10)
            wi = int(rect.width  * 0.86)
            hi = int(rect.height * 0.82)
            return pygame.Rect(xi, yi, wi, hi)
        self.vida_inner_player = vida_inner(self.rect_vida_player)
        self.vida_inner_ai     = vida_inner(self.rect_vida_ai)

        ci = self.cuadro_inner
        tab_h = 36
        tab_w = ci.width // 2 - 4
        self.rect_tab_moves  = pygame.Rect(ci.x,              ci.y,       tab_w, tab_h)
        self.rect_tab_switch = pygame.Rect(ci.x + tab_w + 8,  ci.y,       tab_w, tab_h)

        act_y = ci.y + tab_h + 6
        act_h = ci.height - tab_h - 10
        self.rect_action = pygame.Rect(ci.x, act_y, ci.width, act_h)

        bw = ci.width // 2 - 4
        bh = max(44, (act_h - 6) // 2)
        self.move_buttons = []
        self.switch_buttons = []
        for i in range(4):
            rx = self.rect_action.x + (i%2) * (bw + 8)
            ry = self.rect_action.y + (i//2) * (bh + 6)
            r  = pygame.Rect(rx, ry, bw, bh)
            self.move_buttons.append(
                Button(r, "", pkm_font(8), tag=i, text_align="left"))
            self.switch_buttons.append(
                Button(r, "", pkm_font(8), tag=i, text_align="left"))

        self.log = TextLog(self.rect_action, pkm_font(12), fg=PKM_BLACK)
        self.log.line_h = pkm_font(12).get_height() + 7

    def _start_new_game(self):
        pool = POKEMON_DB[:]
        random.shuffle(pool)
        num = self.battle_type
        self.pokemon_data_list = [pool[i] for i in range(num)]
        self.ai_team = []
        for i in range(num):
            data = pool[i + num] if len(pool) >= num * 2 else pool[i % len(pool)]
            avail = data["movimientos"][:]
            random.shuffle(avail)
            movs = []
            for m in avail[:4]:
                mv = m.copy(); mv["pp"] = mv["ppMax"]; mv["pp_max"] = mv["ppMax"]
                movs.append(mv)
            self.ai_team.append(BattlePokemon(data, preassigned_moves=movs, level=55))
        self._start_move_selection()

    def _start_move_selection(self):
        self.state = self.STATE_MOVE_SEL_INIT
        self.seleccion_movimientos = {}
        self.pokemon_actual = 0
        self._load_move_sel_screen(0)

    def _load_move_sel_screen(self, idx):
        self.pokemon_actual = idx
        prev = self.seleccion_movimientos.get(idx, [])
        self._move_vars = [i in prev for i in range(len(self.pokemon_data_list[idx]["movimientos"]))]
        self._build_move_sel_buttons(idx)

    def _build_move_sel_buttons_inner(self, idx, ci):
        """Construye botones de selección usando un inner rect dado."""
        pokemon = self.pokemon_data_list[idx]
        f   = pkm_font(12)
        bh  = 30
        gap = 5
        y0  = ci.y + 36
        self._move_sel_btns = []
        for i, move in enumerate(pokemon["movimientos"]):
            r = pygame.Rect(ci.x + 4, y0 + i*(bh+gap), ci.width - 8, bh)
            lbl = f"{move['nombre']}  {move['tipo']}  P:{move['poder'] or '-'}  PP:{move['ppMax']}"
            self._move_sel_btns.append(
                Button(r, lbl, f, tag=("toggle", i), text_align="left"))
        bot_y = ci.y + ci.height - 38
        bw3   = (ci.width - 16) // 3
        self._move_sel_btns.append(Button(
            pygame.Rect(ci.x+4, bot_y, bw3, 32), "Anterior", f, tag="anterior",
            disabled=(idx==0), text_align="left"))
        self._move_sel_btns.append(Button(
            pygame.Rect(ci.x+4+bw3+4, bot_y, bw3, 32), "Aleatorio", f, tag="aleatorio",
            text_align="left"))
        last = (idx == len(self.pokemon_data_list)-1)
        self._move_sel_btns.append(Button(
            pygame.Rect(ci.x+4+2*(bw3+4), bot_y, bw3, 32),
            "Iniciar" if last else "Siguiente", f, tag="siguiente",
            text_align="left"))

    def _build_move_sel_buttons(self, idx):
        pokemon = self.pokemon_data_list[idx]
        ci  = self.cuadro_inner
        f   = pkm_font(11)
        bh  = 30
        gap = 5
        y0  = ci.y + 34  # espacio para título
        self._move_sel_btns = []
        for i, move in enumerate(pokemon["movimientos"]):
            r = pygame.Rect(ci.x + 4, y0 + i*(bh+gap), ci.width - 8, bh)
            lbl = f"{move['nombre']}  {move['tipo']}  P:{move['poder'] or '-'}"
            self._move_sel_btns.append(
                Button(r, lbl, f, tag=("toggle", i), text_align="left"))

        # Botones nav
        bot_y = ci.y + ci.height - 38
        bw3   = (ci.width - 16) // 3
        self._move_sel_btns.append(Button(
            pygame.Rect(ci.x+4, bot_y, bw3, 32), "Anterior", f, tag="anterior",
            disabled=(idx==0), text_align="left"))
        self._move_sel_btns.append(Button(
            pygame.Rect(ci.x+4+bw3+4, bot_y, bw3, 24), "Aleatorio", f, tag="aleatorio",
            text_align="left"))
        last = (idx == len(self.pokemon_data_list)-1)
        self._move_sel_btns.append(Button(
            pygame.Rect(ci.x+4+2*(bw3+4), bot_y, bw3, 24),
            "Iniciar" if last else "Siguiente", f, tag="siguiente",
            text_align="left"))

    def handle_event(self, event):
        # Redimensión de ventana
        if event.type == pygame.VIDEORESIZE:
            self.W, self.H = event.w, event.h
            self._load_assets()
            self._compute_layout()
            if self.state != self.STATE_MOVE_SEL_INIT and self.player_team:
                self._refresh_ui()
            elif self.state == self.STATE_MOVE_SEL_INIT and self.pokemon_data_list:
                self._build_move_sel_buttons(self.pokemon_actual)
            return

        self.log.handle_scroll(event)

        if self.state == self.STATE_CONTINUE:
            if (event.type == pygame.MOUSEBUTTONDOWN or
                    (event.type == pygame.KEYDOWN and
                     event.key in (pygame.K_RETURN, pygame.K_SPACE))):
                cb = self._continue_callback
                self._continue_callback = None
                self.state = self.STATE_WAITING
                if cb: cb()
            return

        mouse = pygame.mouse.get_pos()

        if self.state == self.STATE_MOVE_SEL_INIT:
            for btn in self._move_sel_btns:
                btn.update_hover(mouse)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in self._move_sel_btns:
                    if btn.handle_event(event):
                        t = btn.tag
                        if isinstance(t, tuple) and t[0]=="toggle":
                            self._toggle_move(t[1])
                        elif t == "anterior":
                            self._save_and_go(self.pokemon_actual - 1)
                        elif t == "aleatorio":
                            self._randomize()
                        elif t == "siguiente":
                            self._save_and_go(self.pokemon_actual + 1)
            return

        if self._dialog:
            self._handle_dialog_event(event)
            return

        if self.state == self.STATE_GAME_OVER:
            for btn in getattr(self,"_go_btns",[]):
                btn.update_hover(mouse)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in getattr(self,"_go_btns",[]):
                    if btn.handle_event(event):
                        self._on_go_click(btn.tag)
            return

        # Tabs
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect_tab_moves.collidepoint(event.pos):
                self.active_tab = "moves"
            elif self.rect_tab_switch.collidepoint(event.pos):
                self.active_tab = "switch"

        if self.state in (self.STATE_MOVE_SELECT, self.STATE_SWITCH_SELECT):
            btns = self.move_buttons if self.active_tab=="moves" else self.switch_buttons
            for btn in btns: btn.update_hover(mouse)
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for btn in btns:
                    if btn.handle_event(event):
                        if self.active_tab=="moves":
                            self._on_move(btn.tag)
                        else:
                            self._on_switch(btn.tag)

    def _handle_dialog_event(self, event):
        mouse = pygame.mouse.get_pos()
        for btn in self._dialog.get("buttons",[]):
            btn.update_hover(mouse)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in self._dialog.get("buttons",[]):
                if btn.handle_event(event):
                    self._dialog["callback"](btn.tag)

    def _toggle_move(self, i):
        sel = [j for j,v in enumerate(self._move_vars) if v]
        if self._move_vars[i]:
            self._move_vars[i] = False
        elif len(sel) < 4:
            self._move_vars[i] = True

    def _randomize(self):
        ids = list(range(len(self._move_vars)))
        random.shuffle(ids)
        self._move_vars = [False]*len(self._move_vars)
        for i in ids[:4]: self._move_vars[i] = True

    def _save_and_go(self, next_idx):
        sel = [i for i,v in enumerate(self._move_vars) if v]
        if next_idx > self.pokemon_actual and len(sel) != 4:
            return  # necesita exactamente 4
        self.seleccion_movimientos[self.pokemon_actual] = sel
        if next_idx >= len(self.pokemon_data_list):
            self._crear_equipo_jugador()
        elif next_idx >= 0:
            self._load_move_sel_screen(next_idx)

    def _crear_equipo_jugador(self):
        self.player_team = []
        for idx, data in enumerate(self.pokemon_data_list):
            sel = self.seleccion_movimientos.get(idx, [])
            movs = []
            for mi in sel:
                mv = data["movimientos"][mi].copy()
                mv["pp"] = mv["ppMax"]; mv["pp_max"] = mv["ppMax"]
                movs.append(mv)
            p = BattlePokemon(data, preassigned_moves=movs, level=55)
            self.player_team.append(p)
        self._iniciar_batalla()

    def _iniciar_batalla(self):
        self.player_active_idx = 0
        self.ai_active_idx     = 0
        self.turn              = 1
        self.player_hazards = {"stealth_rock":False,"spikes":0,"toxic_spikes":0}
        self.ai_hazards     = {"stealth_rock":False,"spikes":0,"toxic_spikes":0}
        if self.ai_level == 1:
            self.ia = RandomAI(self.ai_team, self.player_team[0])
        elif self.ai_level == 2:
            self.ia = HeuristicAI(self.ai_team, self.player_team[0])
        elif self.ai_level == 3:
            self.ia = MinimaxAI(self.ai_team, self.player_team[0],
                               enemy_team=self.player_team)
        self.buttons_locked = False
        self.pending_switch = False
        self._game_over_active = False
        self._hp_anim = {
            "player": {"cur":1.0,"tgt":1.0,"animating":False,"speed":0.025},
            "ai":     {"cur":1.0,"tgt":1.0,"animating":False,"speed":0.025},
        }
        self._hp_event_queue = []
        self.log.lines = []
        self._log_msg("Equipos listos!", PKM_BLACK)
        self._log_msg(f"Tu equipo: {', '.join(p.nombre for p in self.player_team)}", PKM_BLUE)
        self._log_msg(f"Rival: {', '.join(p.nombre for p in self.ai_team)}", PKM_RED)
        self.state = self.STATE_MOVE_SELECT
        self._refresh_ui()

    def _log_msg(self, msg, color=None):
        color = color or PKM_BLACK
        self.log.add(msg, color)

    def _log_lines_delayed(self, lines, callback=None):
        self._pending_log_lines = list(lines)
        self._log_callback      = callback
        self._last_log_time     = pygame.time.get_ticks()
        self.buttons_locked     = True

    def _tick_log_lines(self):
        if self._dialog or self._ventana_cambio_abierta:
            return
        if self.state == self.STATE_CONTINUE:
            return

        for a in self._hp_anim.values():
            if a["animating"]:
                return

        if not self._pending_log_lines:
            if self._log_callback:
                cb = self._log_callback
                self._log_callback = None
                cb()
            return

        now = pygame.time.get_ticks()
        if now - self._last_log_time >= self._log_delay_ms:
            line = self._pending_log_lines.pop(0)
            col = PKM_BLACK
            if "🔵" in line or "[JUGADOR]" in line: col = PKM_BLUE
            elif "🔴" in line or "[IA]" in line: col = PKM_RED
            elif any(x in line for x in ["[DERROTA]","[DANO]","💀","💢"]) or "baja" in line: col = PKM_RED
            elif any(x in line for x in ["[CURACION]","[CRITICO]","💚","💥"]): col = PKM_GREEN
            elif any(x in line for x in ["[CAMBIO]","[IMPACTO]","[EFECTO]","🔄"]): col = (100,50,160)
            elif "muy efectivo" in line or "💫" in line: col = PKM_GOLD
            elif any(x in line for x in ["😴","❄️","⚡","😵","🔥","☠️"]): col = (140,0,180)
            self._log_msg(line, col)
            self._last_log_time = now

            if ("[IMPACTO]" in line or "[DANO]" in line or
                    "[CURACION]" in line or "baja" in line):
                self._trigger_hp_anim_from_state()
            if "[CAMBIO]" in line:
                self._sync_hp_on_switch()

    def _sync_hp_on_switch(self):
        """Al cambiar de Pokémon, salta la barra directamente al HP real del nuevo."""
        if not self.player_team or not self.ai_team:
            return
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]
        p_pct = max(0.0, pp.current_hp / pp.max_hp)
        a_pct = max(0.0, ap.current_hp / ap.max_hp)
        for key, pct in (("player", p_pct), ("ai", a_pct)):
            a = self._hp_anim[key]
            a["cur"]       = pct  # salta directo
            a["tgt"]       = pct
            a["animating"] = False

    def _trigger_hp_anim_from_state(self):
        """Lee el HP real de los pokémon activos y lanza animación suave."""
        if not self.player_team or not self.ai_team:
            return
        pp  = self.player_team[self.player_active_idx]
        ap  = self.ai_team[self.ai_active_idx]
        p_pct = max(0.0, pp.current_hp / pp.max_hp)
        a_pct = max(0.0, ap.current_hp / ap.max_hp)

        for key, pct in (("player", p_pct), ("ai", a_pct)):
            a = self._hp_anim[key]
            if abs(pct - a["cur"]) > 0.005:
                a["tgt"]       = pct
                a["animating"] = True  # bloquea el log hasta terminar

    def _show_dialog_in_cuadro(self, title, options):
        """
        Muestra un diálogo de selección dentro del cuadro inferior.
        options = [(label, tag), ...]  con scroll si hay muchas.
        """
        ci  = self.cuadro_inner
        f   = pkm_font(9)
        f_t = pkm_font(10)
        bh  = 24
        gap = 4
        y0  = ci.y + 28
        btns = []
        for i, (label, tag) in enumerate(options):
            r = pygame.Rect(ci.x+4, y0+i*(bh+gap), ci.width-8, bh)
            btns.append(Button(r, label, f, tag=tag, text_align="left"))
        self._dialog = {"title": title, "buttons": btns, "callback": None}
        return btns

    def _show_switch_before_attack(self, pokemon, move_idx, move_name):
        available = [(i, p) for i,p in enumerate(self.player_team)
                     if not p.fainted and i != self.player_active_idx]
        opts = [(f"{p.nombre}  HP:{p.current_hp}/{p.max_hp}", ("sw_after", i))
                for i, p in available]
        opts.append(("Cancelar (solo atacar)", "cancel_sw"))

        def cb(tag):
            self._dialog = None
            self.buttons_locked = False
            if isinstance(tag, tuple) and tag[0]=="sw_after":
                self.pending_switch_idx = tag[1]
                self._execute_turn(("move", move_idx))
            elif tag == "cancel_sw":
                self.pending_switch = False
                self.pending_switch_idx = None
                self.switch_source = None
                self._execute_turn(("move", move_idx))

        btns = self._show_dialog_in_cuadro(f"{pokemon.nombre} usara {move_name}!", opts)
        self._dialog["callback"] = cb

    def _show_force_switch(self, title, available_indices, callback):
        opts = []
        for idx in available_indices:
            p = self.player_team[idx]
            opts.append((f"{p.nombre}  HP:{p.current_hp}/{p.max_hp}", idx))
        btns = self._show_dialog_in_cuadro(title, opts)
        self._dialog["callback"] = callback

    def _show_question(self, text, yes_lbl, no_lbl, callback):
        btns = self._show_dialog_in_cuadro(text,
                [(yes_lbl, "yes"), (no_lbl, "no")])
        self._dialog["callback"] = callback

    def _on_move(self, move_idx):
        if self.buttons_locked or self.pending_switch: return
        pp = self.player_team[self.player_active_idx]
        if pp.outrage_locked or (hasattr(pp,'flying_active') and pp.flying_active): return
        move = pp.movimientos[move_idx]
        if move["pp"] <= 0:
            self._log_msg(f"{move['nombre']}: sin PP!", PKM_RED); return
        if move["nombre"] in ["Ida y Vuelta","Voltio Cambio"]:
            avail = [i for i,p in enumerate(self.player_team)
                     if not p.fainted and i!=self.player_active_idx]
            if avail:
                self.pending_move_idx = move_idx
                self.pending_switch   = True
                self.switch_source    = pp
                self._show_switch_before_attack(pp, move_idx, move["nombre"])
                return
        self._execute_turn(("move", move_idx))

    def _on_switch(self, target_idx):
        if self.buttons_locked or self.pending_switch: return
        if target_idx >= len(self.player_team): return
        if target_idx == self.player_active_idx: return
        if self.player_team[target_idx].fainted: return
        pp = self.player_team[self.player_active_idx]
        if pp.outrage_locked or (hasattr(pp,'flying_active') and pp.flying_active): return
        self._execute_turn(("switch", target_idx))
        self.active_tab = "moves"

    def _execute_turn(self, player_action):
        self.ia.active_idx = self.ai_active_idx
        self.ia.enemy = self.player_team[self.player_active_idx]
        if hasattr(self.ia, "enemy_team"):
            self.ia.enemy_team = self.player_team
        if hasattr(self.ia, "enemy_active_idx"):
            self.ia.enemy_active_idx = self.player_active_idx
        ai_action = self.ia.get_action()
        self.buttons_locked = True
        self.state = self.STATE_WAITING
        log_lines  = []

        player_switch = (player_action[0]=="switch")
        ai_switch     = (ai_action[0]=="switch")

        if player_switch:
            nuevo_idx = player_action[1]
            entrante  = self.player_team[nuevo_idx]
            self.player_active_idx = nuevo_idx
            entrante.mods = {"atk":0,"def":0,"spe":0,"evasion":0}
            entrante.protect_success=True; entrante.protect_fail_count=0
            log_lines.append(f"[CAMBIO] 🔄 ¡Cambiaste a {entrante.nombre}!")
            log_lines += apply_hazards_on_switch(entrante, self.player_hazards, True)
            if entrante.fainted:
                log_lines.append(f"💀 ¡{entrante.nombre} fue derrotado por las trampas al entrar!")
                self._log_lines_delayed(log_lines, self._refresh_ui); return
            ai_flying_carga = (getattr(self.ai_team[self.ai_active_idx], 'flying_active', False) and
                               getattr(self.ai_team[self.ai_active_idx], 'flying_turns', 0) == 2)
            if ai_action[0]=="move" and ai_action[1] is not None and not ai_flying_carga:
                def do_ai():
                    self._ejecutar_ataque_seq(self.ai_team[self.ai_active_idx], entrante,
                                              ai_action[1], None, False, [],
                                              lambda: self._finalizar_turno([]))
                self._log_lines_delayed(log_lines, do_ai)
            else:
                self._log_lines_delayed(log_lines, lambda: self._finalizar_turno([]))
            return

        if ai_switch:
            nuevo_idx = ai_action[1]
            entrante  = self.ai_team[nuevo_idx]
            self.ai_active_idx = nuevo_idx; self.ia.active_idx = nuevo_idx
            entrante.mods={"atk":0,"def":0,"spe":0,"evasion":0}
            entrante.protect_success=True; entrante.protect_fail_count=0
            log_lines += apply_hazards_on_switch(entrante, self.ai_hazards, False)
            log_lines.append(f"[CAMBIO] 🔄 IA cambió a {entrante.nombre}!")
            if player_action[0]=="move" and player_action[1] is not None:
                def do_pl():
                    self._ejecutar_ataque_seq(self.player_team[self.player_active_idx], entrante,
                                              player_action[1], None, True, [],
                                              lambda: self._finalizar_turno([]))
                self._log_lines_delayed(log_lines, do_pl)
            else:
                self.pending_switch=False; self.pending_switch_idx=None
                self._log_lines_delayed(log_lines, lambda: self._finalizar_turno([]))
            return

        pmv = player_action[1] if (player_action[0]=="move" and player_action[1] != -1) else None
        amv = ai_action[1]     if ai_action[0]=="move"     else None
        pfi = self.pending_switch_idx

        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]
        pprio = get_priority(pmv,pp) if pmv is not None else 0
        aprio = get_priority(amv,ap) if amv is not None else 0
        pspd  = pp.get_effective_stat("spe")
        aspd  = ap.get_effective_stat("spe")
        orden = ["player","ai"] if (pprio>aprio or (pprio==aprio and pspd>=aspd)) else ["ai","player"]

        self._player_move_idx  = pmv
        self._ai_move_idx      = amv
        self._player_force_idx = pfi
        self._log_lines_temp   = log_lines[:]
        self._procesar_accion_siguiente(orden, 0)

    def _procesar_accion_siguiente(self, orden, index):
        if index >= len(orden):
            self.turn += 1
            self._log_lines_delayed(self._log_lines_temp,
                                    self._aplicar_efectos_fin_turno_y_verificar)
            return
        if index == 0:
            pp = self.player_team[self.player_active_idx]
            ap = self.ai_team[self.ai_active_idx]
            if getattr(pp, 'flying_active', False) and getattr(pp, 'flying_turns', 0) > 0:
                pp.flying_turns -= 1
                if pp.flying_turns == 1:
                    self._log_lines_temp.append(f"🕊️ ¡{pp.nombre} va a aterrizar!")
            if getattr(ap, 'flying_active', False) and getattr(ap, 'flying_turns', 0) > 0:
                ap.flying_turns -= 1
                if ap.flying_turns == 1:
                    self._log_lines_temp.append(f"🕊️ ¡{ap.nombre} va a aterrizar!")
        quien = orden[index]
        nxt   = lambda: self._procesar_accion_siguiente(orden, index+1)
        if quien == "player":
            p = self.player_team[self.player_active_idx]
            if p.fainted or p.current_hp <= 0: nxt(); return
            pmv = getattr(self, '_player_move_idx', None)
            # Forzar Enfado si está enfurecido
            if getattr(p, 'outrage_locked', False):
                for i, m in enumerate(p.movimientos):
                    if m["nombre"] == "Enfado":
                        pmv = i; break
            # Forzar Vuelo/Bote turno 2 automáticamente
            if getattr(p, 'flying_active', False) and getattr(p, 'flying_turns', 0) == 1:
                flying_mv = getattr(p, 'flying_move', None)
                if flying_mv:
                    for i, m in enumerate(p.movimientos):
                        if m["nombre"] == flying_mv:
                            pmv = i; break
            if getattr(p, 'flying_active', False) and getattr(p, 'flying_turns', 0) == 2:
                pmv = None
            if pmv is not None:
                self._ejecutar_ataque_seq(p, self.ai_team[self.ai_active_idx],
                                          pmv, self._player_force_idx,
                                          True, self._log_lines_temp, nxt)
            else: nxt()
        else:
            p = self.ai_team[self.ai_active_idx]
            if p.fainted or p.current_hp <= 0: nxt(); return
            amv = getattr(self, '_ai_move_idx', None)
            # Forzar Enfado si está enfurecida
            if getattr(p, 'outrage_locked', False):
                for i, m in enumerate(p.movimientos):
                    if m["nombre"] == "Enfado":
                        amv = i; break
            # Forzar Vuelo/Bote turno 2 automáticamente
            if getattr(p, 'flying_active', False) and getattr(p, 'flying_turns', 0) == 1:
                flying_mv = getattr(p, 'flying_move', None)
                if flying_mv:
                    for i, m in enumerate(p.movimientos):
                        if m["nombre"] == flying_mv:
                            amv = i; break
            if getattr(p, 'flying_active', False) and getattr(p, 'flying_turns', 0) == 2:
                amv = None
            if amv is not None:
                self._ejecutar_ataque_seq(p, self.player_team[self.player_active_idx],
                                          amv, None,
                                          False, self._log_lines_temp, nxt)
            else: nxt()

    def _ejecutar_ataque_seq(self, atacante, defensor, move_idx, force_idx,
                              es_jugador, log_lines, callback):
        if atacante.fainted or atacante.current_hp <= 0:
            if es_jugador and self.pending_switch:
                self.pending_switch = False
                self.pending_switch_idx = None
                self.switch_source = None
            callback(); return
        if defensor.fainted or defensor.current_hp <= 0: callback(); return

        if atacante.status == "sleep":
            atacante.status_turns -= 1
            if atacante.status_turns <= 0:
                atacante.status = None
                log_lines.append(f"😴 ¡{atacante.nombre} se despertó!")
            else:
                log_lines.append(f"😴 {atacante.nombre} no puede atacar porque está dormido!")
                self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return

        if atacante.status == "freeze":
            if hasattr(atacante, 'freeze_turns'):
                atacante.freeze_turns -= 1
                if atacante.freeze_turns <= 0:
                    atacante.status = None
                    log_lines.append(f"❄️ ¡{atacante.nombre} se descongeló!")
                else:
                    log_lines.append(f"❄️ {atacante.nombre} no puede atacar porque está congelado!")
                    self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return
            elif rand(0.2):
                atacante.status = None
                log_lines.append(f"❄️ ¡{atacante.nombre} se descongeló!")
            else:
                log_lines.append(f"❄️ {atacante.nombre} no puede atacar porque está congelado!")
                self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return

        if atacante.status == "paralyze":
            if rand(0.25):
                log_lines.append(f"⚡ {atacante.nombre} está paralizado y no puede moverse!")
                self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return

        if getattr(atacante, 'confused', False):
            atacante.confused_turns -= 1
            if atacante.confused_turns <= 0:
                atacante.confused = False
                log_lines.append(f"😵 {atacante.nombre} ya no está confundido.")
            elif rand(0.5):
                conf_dmg = max(1, int((atacante.get_effective_stat("atk") / atacante.get_effective_stat("def")) * 40))
                log_lines.append(f"😵 ¡{atacante.nombre} está confundido y se golpeó a sí mismo! ({conf_dmg} HP)")
                atacante.apply_damage(conf_dmg, True)
                if atacante.current_hp <= 0:
                    atacante.fainted = True
                    log_lines.append(f"💀 ¡{atacante.nombre} se derrotó a sí mismo!")
                self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return

        move = atacante.movimientos[move_idx]
        prefijo = "🔵" if es_jugador else "🔴"
        log_lines.append(f"{prefijo} {atacante.nombre} usó {move['nombre']}!")
        if move["pp"] <= 0:
            log_lines.append("¡Sin PP! El movimiento falló.")
            self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return
        MOVES_HIT_FLYING = {"Trueno", "Onda Trueno", "Vendaval", "Tormenta"}
        if (getattr(defensor, 'flying_active', False) and
                getattr(defensor, 'flying_turns', 0) == 1 and
                move["nombre"] not in MOVES_HIT_FLYING):
            log_lines.append(f"🕊️ ¡No afecta a {defensor.nombre}! (está volando)")
            self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return
        if move["nombre"] not in ["Vuelo","Bote"]: move["pp"] -= 1
        SKIP_ACC = {"Proteccion","Vuelo","Bote","Ida y Vuelta","Voltio Cambio","Onda Trueno",
                    "Fuego Fatuo","Deseo","Danza Espada","Malicioso","Mofa","Doble Equipo",
                    "Defensa Ferréa","Foco Energía","Agilidad","Impulso","Danza Aleteo",
                    "Paz Mental","Calma Mental","Amnesia","Campana Cura","Descanso","Bostezo",
                    "Síntesis","Polvo Veneno","Despejar","Trampa Rocas","Puas","Puas Toxicas","Destello"}
        if move["nombre"] not in SKIP_ACC:
            evasion_mod = defensor.get_effective_stat("evasion") if hasattr(defensor, 'get_effective_stat') else 1.0
            acc = move["precision"] * (1.0 / evasion_mod) if evasion_mod > 0 else move["precision"]
            if not rand(acc):
                log_lines.append(f"¡{atacante.nombre} falló el ataque!")
                self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return
        effect_msgs = []
        if move["poder"] > 0:
            if hasattr(defensor,'is_protected') and defensor.is_protected:
                log_lines.append(f"[DEFENSA] {defensor.nombre} se protecio!")
                defensor.is_protected = False
                self._log_lines_delayed(log_lines[:], callback); log_lines.clear(); return
            damage, type_mult = calculate_damage(atacante, defensor, move)
            if rand(0.0625):
                damage = int(damage*1.5); log_lines.append("[CRITICO] Golpe critico!")
            defensor.current_hp = max(0, defensor.current_hp - damage)
            murio = (defensor.current_hp <= 0)
            if type_mult >= 2:   log_lines.append(f"Es muy efectivo! (x{type_mult})")
            elif type_mult == 0: log_lines.append(f"No afecta a {defensor.nombre}!"); defensor.current_hp=min(defensor.max_hp,defensor.current_hp+damage); murio=False
            elif type_mult < 1:  log_lines.append(f"No es muy efectivo... (x{type_mult})")
            log_lines.append(f"{defensor.nombre} baja {damage} de vida.")
            if move["nombre"] in ["Gigadrenado","Puno Drenaje"]:
                d=int(damage*0.5); atacante.heal(d); log_lines.append(f"[CURACION] {atacante.nombre} absorbe {d} HP!")
            if move["nombre"]=="Pajaro Osado":
                r=int(damage/3); atacante.apply_damage(r,True); log_lines.append(f"[DANO] {atacante.nombre} recibe {r} de retroceso.")
            if murio:
                defensor.fainted = True
                log_lines.append(f"[DERROTA] {defensor.nombre} fue derrotado!")
            apply_move_effects(atacante,defensor,move,effect_msgs,es_jugador,self.player_hazards,self.ai_hazards)
            log_lines += effect_msgs
            if force_idx is not None and es_jugador:
                new_p = self.player_team[force_idx]
                old_name = atacante.nombre
                self.player_active_idx = force_idx
                new_p.mods={"atk":0,"def":0,"spe":0,"evasion":0}
                new_p.protect_success=True; new_p.protect_fail_count=0
                h = apply_hazards_on_switch(new_p, self.player_hazards, True)
                log_lines.append(f"🔄 ¡{old_name} regresó! ¡{new_p.nombre} salió al campo!")
                log_lines += h
                if new_p.fainted:
                    log_lines.append(f"💀 ¡{new_p.nombre} fue derrotado por las trampas!")
                self.pending_switch_idx=None; self.pending_switch=False
                self.switch_source=None; self.pending_move_idx=None
        else:
            apply_move_effects(atacante,defensor,move,effect_msgs,es_jugador,self.player_hazards,self.ai_hazards)
            log_lines+=effect_msgs
        self._log_lines_delayed(log_lines[:], callback); log_lines.clear()

    def _finalizar_turno(self, log_lines):
        self.turn += 1
        def go():
            self.pending_switch=False; self.pending_switch_idx=None; self.switch_source=None
            pp = self.player_team[self.player_active_idx]
            ap = self.ai_team[self.ai_active_idx]
            pmv = getattr(self, '_player_move_idx', None)
            amv = getattr(self, '_ai_move_idx', None)
            def _used_protect(pokemon, move_idx):
                if move_idx is None: return False
                try:
                    return pokemon.movimientos[move_idx]["nombre"] == "Proteccion"
                except: return False
            if not _used_protect(pp, pmv):
                pp.protect_fail_count = 0
                pp.protect_success = True
            if not _used_protect(ap, amv):
                ap.protect_fail_count = 0
                ap.protect_success = True
            self._aplicar_efectos_fin_turno_y_verificar()
        self._log_lines_delayed(log_lines, go)

    def _aplicar_efectos_fin_turno_y_verificar(self):
        if not self.player_team or not self.ai_team: return
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]
        # Decrementar Enfado al final del turno
        for pokemon in [pp, ap]:
            if not getattr(pokemon, 'outrage_active', False):
                continue
            pokemon.outrage_turns -= 1
            if pokemon.outrage_turns <= 0:
                pokemon.outrage_active = False
                pokemon.outrage_locked = False
                pokemon.confused = True
                pokemon.confused_turns = random.randint(2, 5)
                self._log_msg(f"😵 ¡{pokemon.nombre} ya no está enfurecido! ¡{pokemon.nombre} está confundido!", (140,0,180))
        for pokemon in [pp, ap]:
            if pokemon.fainted: continue
            if pokemon.status=="burn":
                d=max(1,int(pokemon.max_hp/16)); pokemon.apply_damage(d,True)
                self._log_msg(f"{pokemon.nombre} baja {d} de vida (quemadura).", PKM_RED)
            elif pokemon.status=="poison":
                d=max(1,int(pokemon.max_hp/16)); pokemon.apply_damage(d,True)
                self._log_msg(f"{pokemon.nombre} baja {d} de vida (veneno).", (140,0,180))
            elif pokemon.status=="toxic":
                d=max(1,int(pokemon.max_hp/16*pokemon.poison_counter))
                pokemon.poison_counter+=1; pokemon.apply_damage(d,True)
                self._log_msg(f"{pokemon.nombre} baja {d} de vida (veneno grave).", (100,0,150))
            elif pokemon.status=="infectado":
                d=max(1,int(pokemon.max_hp/8)); pokemon.apply_damage(d,True)
                self._log_msg(f"{pokemon.nombre} baja {d} de vida (drenadoras).", PKM_GREEN)
            if pokemon.current_hp<=0 and not pokemon.fainted:
                pokemon.fainted=True
                self._log_msg(f"[DERROTA] {pokemon.nombre} derrotado!", PKM_RED)
        for p,wh in [(pp,getattr(pp,'wish_heal',0)),(ap,getattr(ap,'wish_heal',0))]:
            if wh and not p.fainted:
                p.heal(wh); self._log_msg(f"[CURACION] {p.nombre} Deseo +{wh}HP.", PKM_GREEN)
                p.wish_heal=0
        if hasattr(pp,'is_protected'): pp.is_protected=False
        if hasattr(ap,'is_protected'): ap.is_protected=False
        self._refresh_ui()
        self._trigger_hp_anim_from_state()
        self._verificar_derrotados()

    def _verificar_derrotados(self):
        if self._procesando_derrotado: return
        self._procesando_derrotado = True
        for p in self.player_team:
            if p.current_hp<=0 and not p.fainted: p.fainted=True
        for p in self.ai_team:
            if p.current_hp<=0 and not p.fainted: p.fainted=True
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]
        pa = [i for i,p in enumerate(self.player_team) if not p.fainted]
        aa = [i for i,p in enumerate(self.ai_team)     if not p.fainted]
        if not pa: self._procesando_derrotado=False; self._game_over("ai"); return
        if not aa: self._procesando_derrotado=False; self._game_over("player"); return
        if pp.fainted and pa:
            self._procesando_derrotado=False
            if not self._ventana_cambio_abierta: self._force_switch_player()
            return
        if ap.fainted and aa:
            nuevo_idx = random.choice(aa)
            self._pokemon_ia_pendiente = (nuevo_idx, self.ai_team[nuevo_idx])
            self._procesando_derrotado=False
            pp_outrage = getattr(pp, 'outrage_locked', False)
            pp_flying  = getattr(pp, 'flying_active', False)
            if not pp.fainted and not self._ventana_cambio_abierta and not pp_outrage and not pp_flying:
                self._ask_player_switch(self.ai_team[nuevo_idx], nuevo_idx)
            else:
                self._enviar_ia_pendiente()
            return
        self._procesando_derrotado=False
        self._iniciar_siguiente_turno()

    def _iniciar_siguiente_turno(self):
        """Decide si el siguiente turno es automático (Enfado/Vuelo) o espera al jugador."""
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]
        outrage = getattr(pp, 'outrage_locked', False)
        flying  = getattr(pp, 'flying_active', False) and getattr(pp, 'flying_turns', 0) > 0

        if outrage or flying:
            # Turno automático: mostrar "Continuar" antes de ejecutar
            label = "😤 sigue enfurecido" if outrage else "🕊️ sigue volando"
            self._show_continue(
                f"{pp.nombre} {label}... (Presiona Continuar)",
                lambda: self._execute_turn(("move", -1))  # -1 = forzado por outrage/vuelo
            )
        else:
            # Turno normal: mostrar botón Continuar y luego dar control al jugador
            self._show_continue(
                "Presiona Continuar para el siguiente turno.",
                self._unlock_player
            )

    def _unlock_player(self):
        self.buttons_locked = False
        self.state = self.STATE_MOVE_SELECT
        self._refresh_ui()

    def _show_continue(self, mensaje, callback):
        self._log_msg(f"── {mensaje} ──", (100, 100, 100))
        self._continue_callback = callback
        self.buttons_locked = True
        self.state = self.STATE_CONTINUE
        self._refresh_ui()

    def _force_switch_player(self):
        if self._ventana_cambio_abierta: return
        self._ventana_cambio_abierta=True
        self._pending_log_lines = []
        self._log_callback = None
        avail = [i for i,p in enumerate(self.player_team) if not p.fainted]
        def cb(idx):
            self._dialog=None; self._ventana_cambio_abierta=False
            p=self.player_team[idx]
            msgs=apply_hazards_on_switch(p,self.player_hazards,True)
            for m in msgs: self._log_msg(m, PKM_RED)
            if p.fainted:
                alive=[i for i,pk in enumerate(self.player_team) if not pk.fainted]
                if not alive: self._game_over("ai"); return
                self._force_switch_player(); return
            self.player_active_idx=idx
            p.mods={"atk":0,"def":0,"spe":0,"evasion":0}
            p.protect_success=True; p.protect_fail_count=0
            self._log_msg(f"[CAMBIO] 🔄 {p.nombre} al campo!", PKM_BLUE)
            self._pending_log_lines = []
            self._log_callback = None
            self.buttons_locked = False
            self.state = self.STATE_MOVE_SELECT
            self._refresh_ui()
        self._show_force_switch("Tu Pokemon fue derrotado! Elige:", avail, cb)

    def _ask_player_switch(self, nuevo_pokemon, nuevo_idx):
        if self._ventana_cambio_abierta: return
        self._ventana_cambio_abierta=True
        # Limpiar callbacks pendientes del turno anterior
        self._pending_log_lines = []
        self._log_callback = None
        def cb(tag):
            self._dialog=None; self._ventana_cambio_abierta=False
            if tag=="yes":
                avail=[i for i,p in enumerate(self.player_team)
                       if not p.fainted and i!=self.player_active_idx]
                if avail:
                    def cb2(idx):
                        self._dialog=None; self._ventana_cambio_abierta=False
                        self.player_active_idx=idx
                        new_p=self.player_team[idx]
                        new_p.mods={"atk":0,"def":0,"spe":0,"evasion":0}
                        new_p.protect_success=True; new_p.protect_fail_count=0
                        msgs=apply_hazards_on_switch(new_p,self.player_hazards,True)
                        for m in msgs: self._log_msg(m,PKM_RED)
                        self._log_msg(f"[CAMBIO] Cambiaste a {new_p.nombre}!", PKM_BLUE)
                        self._enviar_ia_pendiente()
                    self._show_force_switch("Elige tu Pokemon:", avail, cb2)
                else: self._enviar_ia_pendiente()
            else: self._enviar_ia_pendiente()
        self._show_question(
            f"Rival envia a {nuevo_pokemon.nombre}. Cambiar?",
            "Si, cambiar", "No, seguir", cb)

    def _enviar_ia_pendiente(self):
        nuevo_idx,nuevo_pokemon=self._pokemon_ia_pendiente
        self.ai_active_idx=nuevo_idx
        new_ap=self.ai_team[nuevo_idx]
        new_ap.mods={"atk":0,"def":0,"spe":0,"evasion":0}
        new_ap.protect_success=True; new_ap.protect_fail_count=0
        msgs=apply_hazards_on_switch(new_ap,self.ai_hazards,False)
        for m in msgs: self._log_msg(m,PKM_RED)
        self._log_msg(f"[CAMBIO] 🔄 IA envió a {new_ap.nombre}!",PKM_RED)
        # Sincronizar índices de la IA
        if hasattr(self.ia, "enemy_active_idx"):
            self.ia.enemy_active_idx = self.player_active_idx
        # Limpiar callbacks pendientes del turno anterior
        self._pending_log_lines = []
        self._log_callback = None
        self._procesando_derrotado=False
        self._iniciar_siguiente_turno()

    def _game_over(self, winner):
        if self._game_over_active: return
        self._game_over_active=True
        registrar_resultado_pve(winner, self.ai_level)
        self.buttons_locked=True; self.state=self.STATE_GAME_OVER
        msg = "VICTORIA! Derrotaste al rival!" if winner=="player" else "DERROTA... Todos tus Pokemon han caido."
        col = PKM_GREEN if winner=="player" else PKM_RED
        self._go_msg=msg; self._go_col=col
        ci  = self.cuadro_inner
        f   = pkm_font(12)
        bh  = 30; bw=(ci.width-16)//2
        y   = ci.y+ci.height-32
        self._go_btns=[
            Button(pygame.Rect(ci.x+4, y, bw, bh), "Jugar de nuevo", f, tag="restart", text_align="left"),
            Button(pygame.Rect(ci.x+4+bw+8, y, bw, bh), "Menu Principal", f, tag="menu", text_align="left"),
        ]

    def _on_go_click(self, tag):
        if tag=="restart": self._restart()
        elif tag=="menu":
            if self.on_exit_callback: self.on_exit_callback()

    def _restart(self):
        self.player_team=[]; self.ai_team=[]; self.pokemon_data_list=[]
        self.turn=1; self._game_over_active=False; self.buttons_locked=False
        self.pending_switch=False; self.pending_switch_idx=None
        self._procesando_derrotado=False; self._pokemon_ia_pendiente=None
        self._ventana_cambio_abierta=False; self._dialog=None
        self.log.lines=[]; self._pending_log_lines=[]; self._log_callback=None
        self.player_hazards={"stealth_rock":False,"spikes":0,"toxic_spikes":0}
        self.ai_hazards    ={"stealth_rock":False,"spikes":0,"toxic_spikes":0}
        self._start_new_game()

    def _refresh_ui(self):
        if not self.player_team or not self.ai_team: return
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]
        p_pct = max(0.0, pp.current_hp / pp.max_hp)
        a_pct = max(0.0, ap.current_hp / ap.max_hp)
        for key, pct in (("player", p_pct), ("ai", a_pct)):
            a = self._hp_anim[key]
            if not a["animating"] and abs(pct - a["tgt"]) < 0.001:
                a["cur"] = pct
                a["tgt"] = pct
        self._update_move_buttons(pp, ap)
        self._update_switch_buttons()

    def _update_move_buttons(self, pp, ap):
        for i, btn in enumerate(self.move_buttons):
            if i>=len(pp.movimientos): btn.text="---"; btn.disabled=True; continue
            m=pp.movimientos[i]
            warn=" (!)" if m["pp"]<=max(1,m["pp_max"]//4) else ""
            dis=m["pp"]<=0 or self.buttons_locked or self.pending_switch
            btn.text=f"{m['nombre']}  PP:{m['pp']}/{m['pp_max']}{warn}"
            btn.disabled=dis

    def _update_switch_buttons(self):
        if not self.player_team: return
        for i,btn in enumerate(self.switch_buttons):
            if i>=len(self.player_team): btn.text="---"; btn.disabled=True; continue
            p=self.player_team[i]
            is_active=(i==self.player_active_idx)
            dis=p.fainted or is_active or self.buttons_locked or self.pending_switch
            pct=int(p.current_hp/p.max_hp*100) if not p.fainted else 0
            star="* " if is_active else "  "
            faint="[DERROTADO]" if p.fainted else f"HP:{p.current_hp}/{p.max_hp}"
            btn.text=f"{star}{p.nombre}  {faint}"
            btn.disabled=dis

    def update(self):
        self._tick_log_lines()
        for key in ("player","ai"):
            a = self._hp_anim[key]
            if a["animating"]:
                diff = a["tgt"] - a["cur"]
                if abs(diff) > 0.003:
                    a["cur"] += diff * a["speed"]  # suave e interpolado
                else:
                    a["cur"]       = a["tgt"]
                    a["animating"] = False  # desbloquear log

    def draw(self):
        # 1. Fondo
        if self.bg_surf:
            self.screen.blit(self.bg_surf,(0,0))
        else:
            self.screen.fill(BG)

        if self.state==self.STATE_MOVE_SEL_INIT:
            self._draw_move_selection_full()
            return

        self._draw_vida_panels()

        self._draw_sprites()

        # 4. Cuadro inferior
        self._draw_cuadro_base()

        if self._dialog:
            self._draw_dialog_in_cuadro()
        elif self.state==self.STATE_GAME_OVER:
            self._draw_game_over_in_cuadro()
        else:
            self._draw_action_or_log()

    def _draw_move_selection_full(self):
        """Dibuja la selección de movimientos con un cuadro alto (casi toda la pantalla)."""
        W, H = self.W, self.H
        margin = 5
        sel_w = W - 10
        sel_h = H - margin * 2 - 10
        sel_x = margin
        sel_y = margin + 5
        sel_rect = pygame.Rect(sel_x, sel_y, sel_w, sel_h)
        sel_surf = load_image_pil(
            os.path.join(_IMGS, "Cuadro_Texto", "Cuadro_stats.png"),
            (sel_w, sel_h), keep_alpha=True)
        if sel_surf:
            self.screen.blit(sel_surf, sel_rect.topleft)
        else:
            pygame.draw.rect(self.screen, (255,255,255), sel_rect)
            pygame.draw.rect(self.screen, PKM_BLACK, sel_rect, 3)
        # Inner del cuadro de selección
        borde   = max(10, int(sel_w * 0.036))
        borde_v = max(12, int(sel_h * 0.045))
        self._sel_inner = pygame.Rect(
            sel_rect.x + borde, sel_rect.y + borde_v,
            sel_w - borde*2, sel_h - borde_v*2)
        # Reconstruir botones con el inner grande
        self._build_move_sel_buttons_inner(self.pokemon_actual, self._sel_inner)
        self._draw_move_selection(inner_override=self._sel_inner)

    def _draw_cuadro_base(self):
        if self.cuadro_surf:
            self.screen.blit(self.cuadro_surf, self.rect_cuadro.topleft)
        else:
            pygame.draw.rect(self.screen, WHITE, self.rect_cuadro)
            pygame.draw.rect(self.screen, PKM_BLACK, self.rect_cuadro, 3)

    def _draw_vida_panels(self):
        if not self.player_team or not self.ai_team: return
        pp=self.player_team[self.player_active_idx]
        ap=self.ai_team[self.ai_active_idx]
        self._draw_one_vida(self.rect_vida_player, self.vida_inner_player,
                            pp, self.player_team, self.player_active_idx,
                            "Jugador", self._hp_anim["player"]["cur"])
        self._draw_one_vida(self.rect_vida_ai, self.vida_inner_ai,
                            ap, self.ai_team, self.ai_active_idx,
                            f"IA Nivel {self.ai_level}" + (" (MM)" if self.ai_level in (3,4) else ""), self._hp_anim["ai"]["cur"])

    def _draw_one_vida(self, rect, inner, poke, team, active_idx, label, hp_cur):
        # Imagen Fondo_Vida
        if self.vida_surf:
            self.screen.blit(self.vida_surf, rect.topleft)
        else:
            pygame.draw.rect(self.screen, (255,255,255), rect)
            pygame.draw.rect(self.screen, PKM_BLACK, rect, 2)

        # Escalar fuentes al tamaño del panel
        panel_w  = rect.width
        f_owner  = pkm_font(max(6, int(panel_w * 0.022)))  # "Jugador" / "IA NvX"
        f_name   = pkm_font(max(7, int(panel_w * 0.026)))  # nombre Pokémon
        f_hp     = pkm_font(max(6, int(panel_w * 0.022)))  # "HP:xxx/xxx"
        f_status = pkm_font(max(5, int(panel_w * 0.019)))  # tag estado

        x  = inner.x + 4
        y  = inner.y + 2

        draw_text(self.screen, label, x, y, f_owner, SEL_COL)
        y += f_owner.get_height() + 0

        # 2. Nombre del Pokémon + Nivel
        draw_text(self.screen, f"{poke.nombre} N{poke.level}", x, y, f_name, PKM_BLACK)
        y += f_name.get_height() + 1

        x_hp = x
        if poke.status:
            sc  = STATUS_COLORS.get(poke.status, (136,136,136))
            sl  = STATUS_LABELS.get(poke.status, poke.status[:3].upper())
            ss  = f_status.render(sl, True, (255,255,255))
            sr  = pygame.Rect(x, y, ss.get_width()+6, f_status.get_height()+2)
            pygame.draw.rect(self.screen, sc, sr, border_radius=2)
            self.screen.blit(ss, (x+3, y+1))
            x_hp = sr.right + 4

        hp_display = int(round(hp_cur * poke.max_hp))
        hp_display = max(0, min(hp_display, poke.max_hp))
        draw_text(self.screen, f"HP:{hp_display}/{poke.max_hp}", x_hp, y, f_hp, PKM_BLACK)
        y += max(f_hp.get_height(), f_status.get_height() if poke.status else 0) + 3

        # 4. Barra de HP
        bar_w = inner.width - 8
        bar_h = max(6, int(inner.height * 0.12))
        draw_hp_bar(self.screen, pygame.Rect(x, y, bar_w, bar_h), hp_cur, dark_bg=False)
        y += bar_h + 3

        # 5. Iconos del equipo
        dot_size = max(8, int(panel_w * 0.019))
        for i, p in enumerate(team):
            cx = x + i*(dot_size+3) + dot_size//2
            cy = y + dot_size//2
            icon = self.icon_muerto if p.fainted else self.icon_vivo
            if icon:
                scaled_icon = pygame.transform.scale(icon, (dot_size, dot_size))
                self.screen.blit(scaled_icon, (cx - dot_size//2, cy - dot_size//2))
            else:
                color  = (68,68,68) if p.fainted else HP_GREEN_PKM
                border = (180,120,0) if i == active_idx else PKM_BLACK
                pygame.draw.circle(self.screen, color,  (cx, cy), dot_size//2)
                pygame.draw.circle(self.screen, border, (cx, cy), dot_size//2, 2)

    def _draw_sprites(self):
        if not self.player_team or not self.ai_team: return
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]

        for poke, rect in [(pp, self.rect_sprite_player), (ap, self.rect_sprite_ai)]:
            gif = self._get_poke_gif(poke.nombre)
            img = gif.get_frame() if gif and gif.is_valid() else None
            if img:
                iw, ih = img.get_size()
                scale = min(rect.width / iw, rect.height / ih)
                nw, nh = int(iw * scale), int(ih * scale)
                scaled = pygame.transform.smoothscale(img, (nw, nh))
                ix = rect.x + (rect.width - nw) // 2
                iy = rect.y + (rect.height - nh) // 2
                
                if poke.fainted:
                    grey = pygame.Surface((nw, nh), pygame.SRCALPHA)
                    grey.fill((100, 100, 100, 180))
                    scaled.blit(grey, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                self.screen.blit(scaled, (ix, iy))
        
        f_turn = pkm_font(12)
        draw_text(self.screen, f"Turno {self.turn}",
                self.W//2, self.rect_sprite_zone.y+4, f_turn, WHITE, center=True)
        
    def _draw_action_or_log(self):
        """Dibuja tabs + botones de acción O el log del turno."""
        ci = self.cuadro_inner
        f_tab = pkm_font(11)

        # Tabs
        tab_col_m  = PKM_BLACK if self.active_tab=="moves"  else (120,120,120)
        tab_col_s  = PKM_BLACK if self.active_tab=="switch" else (120,120,120)
        draw_text(self.screen, "Ataques", self.rect_tab_moves.centerx,
                  self.rect_tab_moves.y+3, f_tab, tab_col_m, center=True)
        draw_text(self.screen, "Cambiar", self.rect_tab_switch.centerx,
                  self.rect_tab_switch.y+3, f_tab, tab_col_s, center=True)
        # Subrayado del tab activo
        if self.active_tab=="moves":
            pygame.draw.line(self.screen, PKM_BLACK,
                             (self.rect_tab_moves.x, self.rect_tab_moves.bottom-1),
                             (self.rect_tab_moves.right, self.rect_tab_moves.bottom-1), 2)
        else:
            pygame.draw.line(self.screen, PKM_BLACK,
                             (self.rect_tab_switch.x, self.rect_tab_switch.bottom-1),
                             (self.rect_tab_switch.right, self.rect_tab_switch.bottom-1), 2)

        if self.state in (self.STATE_WAITING, self.STATE_CONTINUE):
            self.log.draw(self.screen)
            if self.state == self.STATE_CONTINUE:
                f_cont = pkm_font(14)
                txt = f_cont.render("[ Clic / Enter / Espacio para continuar ]", True, (60,60,180))
                r = txt.get_rect(midbottom=(self.W//2, self.H - 8))
                pygame.draw.rect(self.screen, (220,220,240), r.inflate(12,6), border_radius=4)
                pygame.draw.rect(self.screen, (60,60,180), r.inflate(12,6), 2, border_radius=4)
                self.screen.blit(txt, r)
        else:
            # Dibujar botones de acción
            btns = self.move_buttons if self.active_tab=="moves" else self.switch_buttons
            f_btn = pkm_font(12)
            for btn in btns:
                col    = (150,150,150) if btn.disabled else (SEL_COL if btn.hovered else NORM_COL)
                cursor = "> " if btn.hovered and not btn.disabled else "  "
                text   = cursor + btn.text
                rendered = f_btn.render(text, True, col)
                r = rendered.get_rect(midleft=(btn.rect.x+4, btn.rect.centery))
                self.screen.blit(rendered, r)
                pygame.draw.line(self.screen, (200,200,200),
                                 (btn.rect.x, btn.rect.bottom),
                                 (btn.rect.right, btn.rect.bottom), 1)
            # Log debajo si hay líneas
            if self.log.lines:
                pass

    def _draw_dialog_in_cuadro(self):
        d  = self._dialog
        ci = self.cuadro_inner
        f_title = pkm_font(12)
        f_opt   = pkm_font(11)

        # Título
        draw_text(self.screen, d["title"], ci.x+6, ci.y+4, f_title, PKM_BLACK)

        # Opciones con cursor '>'
        for btn in d["buttons"]:
            mouse = pygame.mouse.get_pos()
            btn.update_hover(mouse)
            col  = PKM_RED if "cancel" in str(btn.tag).lower() or btn.tag=="no"                    else (SEL_COL if btn.hovered else NORM_COL)
            cursor = "> " if btn.hovered else "  "
            text   = cursor + btn.text
            rendered = f_opt.render(text, True, col)
            r = rendered.get_rect(midleft=(btn.rect.x+4, btn.rect.centery))
            self.screen.blit(rendered, r)
            pygame.draw.line(self.screen, (200,200,200),
                             (btn.rect.x, btn.rect.bottom),(btn.rect.right,btn.rect.bottom),1)

    def _draw_game_over_in_cuadro(self):
        ci = self.cuadro_inner
        f  = pkm_font(10)
        f2 = pkm_font(8)
        draw_text(self.screen, self._go_msg, ci.centerx, ci.y+10,
                  f, self._go_col, center=True)
        for btn in self._go_btns:
            mouse = pygame.mouse.get_pos()
            btn.update_hover(mouse)
            col2 = SEL_COL if btn.hovered else NORM_COL
            cursor = "> " if btn.hovered else "  "
            rendered = f2.render(cursor+btn.text, True, col2)
            r = rendered.get_rect(midleft=(btn.rect.x+4, btn.rect.centery))
            self.screen.blit(rendered, r)

    def _draw_move_selection(self, inner_override=None):
        """Pantalla de selección inicial de movimientos dentro del cuadro."""
        ci = inner_override if inner_override is not None else self.cuadro_inner
        f_title = pkm_font(13)
        f_opt   = pkm_font(11)
        pokemon = self.pokemon_data_list[self.pokemon_actual]
        sel_count = sum(1 for v in self._move_vars if v)

        f_title_big = pkm_font(14)
        draw_text(self.screen, f"Pokemon {self.pokemon_actual+1}/{len(self.pokemon_data_list)}",
                  ci.x+4, ci.y+4, f_title_big, PKM_BLACK)
        draw_text(self.screen, f"{pokemon['nombre']}  Sel:{sel_count}/4",
                  ci.centerx, ci.y+4, f_title_big, SEL_COL, center=True)

        mouse = pygame.mouse.get_pos()
        for i, btn in enumerate(self._move_sel_btns[:-3]):
            btn.update_hover(mouse)
            sel = self._move_vars[i]
            col = SEL_COL if sel or btn.hovered else NORM_COL
            cursor = "> " if sel or btn.hovered else "  "
            move   = pokemon["movimientos"][i]
            tipo   = move["tipo"]
            tc,_   = TYPE_COLORS.get(tipo,((100,100,100),WHITE))
            # Fondo de tipo
            draw_rect_alpha(self.screen, tc, btn.rect, alpha=80, radius=2)
            rendered = f_opt.render(cursor+btn.text, True, col)
            r = rendered.get_rect(midleft=(btn.rect.x+4, btn.rect.centery))
            self.screen.blit(rendered, r)
            pygame.draw.line(self.screen,(200,200,200),
                             (btn.rect.x,btn.rect.bottom),(btn.rect.right,btn.rect.bottom),1)

        # Botones de navegación
        for btn in self._move_sel_btns[-3:]:
            btn.update_hover(mouse)
            col = (120,120,120) if btn.disabled else PKM_BLACK
            cursor = "> " if btn.hovered and not btn.disabled else "  "
            rendered = f_opt.render(cursor+btn.text, True, col)
            r = rendered.get_rect(midleft=(btn.rect.x+4, btn.rect.centery))
            self.screen.blit(rendered, r)