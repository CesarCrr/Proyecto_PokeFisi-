import pygame
import random

def rand(prob):
    return random.random() < prob

def clamp(value, min_val, max_val):
    return max(min_val, min(max_val, value))

def get_stat_stage_mod(stage):
    stages = [0.25,0.28,0.33,0.4,0.5,0.66,1,1.5,2,2.5,3,3.5,4]
    return stages[max(0, min(12, stage + 6))]

def get_evasion_mod(stage):
    stages = [0.33,0.38,0.43,0.5,0.6,0.75,1,1.33,1.66,2,2.5,3,3.5]
    return stages[max(0, min(12, stage + 6))]
import os

from datos.datos_pokemon import POKEMON_DB
from ui.pygame_utils import (
    BG, PKM_BLACK, PKM_RED, PKM_BLUE, PKM_GREEN, PKM_GOLD, PKM_WHITE,
    HP_GREEN_PKM, HP_GOLD_PKM, HP_RED_PKM,
    TYPE_COLORS, STATUS_COLORS, STATUS_LABELS,
    get_font, pkm_font, draw_rect_alpha, draw_text, draw_hp_bar,
    Button, TextLog,
    load_image_pil, load_bg_image,
    GifSprite, load_pokemon_gif, get_preloaded_gif,
)
from models.clase_batalla import BattlePokemon
from batalla.logica_batalla import calculate_damage, get_priority
from batalla.peligros import apply_hazards_on_switch
from batalla.efectos import apply_move_effects
from ia.ia_levels import RandomAI, HeuristicAI, MinimaxAI
from utiles.estadisticas import registrar_resultado_simulation

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_IMGS     = os.path.join(_BASE_DIR, "images")

SEL_COL  = (30, 80, 200)
NORM_COL = PKM_BLACK

class PokemonSimulationGUI:
    STATE_RUNNING   = "running"
    STATE_GAME_OVER = "game_over"

    def __init__(self, screen, ai_level=1, ai2_level=1,
                 battle_type=4, on_exit_callback=None):
        self.screen   = screen
        self.W, self.H = screen.get_size()
        self.ai_level  = ai_level
        self.ai2_level = ai2_level
        self.battle_type = battle_type
        self.on_exit_callback = on_exit_callback

        self.blue_team       = []
        self.red_team        = []
        self.blue_active_idx = 0
        self.red_active_idx  = 0
        self.turn            = 1
        self.blue_ia         = None
        self.red_ia          = None
        self.blue_hazards    = {"stealth_rock":False,"spikes":0,"toxic_spikes":0}
        self.red_hazards     = {"stealth_rock":False,"spikes":0,"toxic_spikes":0}
        self._game_over_active = False

        self._pending_log_lines = []
        self._log_delay_ms      = 1000
        self._last_log_time     = 0
        self._log_callback      = None
        self._turn_pending      = False
        self._turn_delay_ms     = 1600
        self._last_turn_time    = 0

        self._sim_orden         = []
        self._sim_index         = 0
        self._sim_blue_move_idx = None
        self._sim_red_move_idx  = None
        self._log_lines_temp    = []

        self._hp_anim = {
            "blue": {"cur":1.0, "tgt":1.0, "animating": False, "speed": 0.025},
            "red":  {"cur":1.0, "tgt":1.0, "animating": False, "speed": 0.025},
        }
        self.state = self.STATE_RUNNING

        self._load_assets()
        self._compute_layout()
        self._start_new_game()

    def _load_assets(self):
        W, H = self.W, self.H

        bg_path = os.path.join(_IMGS, "Fondos", "Fondo_Batalla.jfif")
        self.bg_surf = load_bg_image(bg_path, (W, H))

        VIDA_RATIO = 2573/905
        vida_w = int(W * 0.34)
        vida_h = int(vida_w / VIDA_RATIO * 0.65)
        self.vida_w = vida_w
        self.vida_h = vida_h
        vida_path = os.path.join(_IMGS, "Cuadro_Texto", "Fondo_Vida.png")
        self.vida_surf = load_image_pil(vida_path, (vida_w, vida_h), keep_alpha=True)

        f_ref    = pkm_font(12)
        line_h   = f_ref.get_height() + 7
        borde_v  = max(10, int(H * 0.018))
        cuadro_w = W - 10
        cuadro_h = line_h * 3 + borde_v * 2 + 40
        cuadro_h = max(120, min(cuadro_h, int(H * 0.26)))
        self.cuadro_w = cuadro_w
        self.cuadro_h = cuadro_h
        cuadro_path = os.path.join(_IMGS, "Cuadro_Texto", "Cuadro_stats.png")
        self.cuadro_surf = load_image_pil(cuadro_path, (cuadro_w, cuadro_h), keep_alpha=True)

        icon_sz = max(10, int(W * 0.013))
        vivo_path   = os.path.join(_IMGS, "Vivo_Poke.png")
        muerto_path = os.path.join(_IMGS, "Muerto_Poke.png")
        self.icon_vivo   = load_image_pil(vivo_path,   (icon_sz, icon_sz), keep_alpha=True)
        self.icon_muerto = load_image_pil(muerto_path, (icon_sz, icon_sz), keep_alpha=True)
        self._icon_sz    = icon_sz

        self._poke_gifs = {}

    def _get_poke_gif(self, nombre, size=None):
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

        vida_w = self.vida_w
        vida_h = self.vida_h
        vida_y = margin
        self.rect_vida_blue = pygame.Rect(margin, vida_y, vida_w, vida_h)
        self.rect_vida_red  = pygame.Rect(W - vida_w - margin, vida_y, vida_w, vida_h)
        dot_gap     = max(10, int(vida_w * 0.055)) + 6
        vida_bottom = vida_y + vida_h + dot_gap + 4

        cuadro_w  = self.cuadro_w
        cuadro_h  = self.cuadro_h
        cuadro_top = H - cuadro_h - margin
        self.cuadro_y   = cuadro_top
        self.rect_cuadro = pygame.Rect(margin, cuadro_top, cuadro_w, cuadro_h)

        sprite_zone_h = max(80, cuadro_top - vida_bottom - 2)
        self.sprite_h = sprite_zone_h
        self.rect_sprite_zone = pygame.Rect(0, vida_bottom, W, sprite_zone_h)
        sp_size = min(sprite_zone_h - 4, W // 2 - 12)
        self.rect_sprite_blue = pygame.Rect(W//4 - sp_size//2, vida_bottom+(sprite_zone_h-sp_size)//2, sp_size, sp_size)
        self.rect_sprite_red  = pygame.Rect(W*3//4 - sp_size//2, vida_bottom+(sprite_zone_h-sp_size)//2, sp_size, sp_size)

        borde   = max(8, int(cuadro_w * 0.025))
        borde_v = max(8, int(cuadro_h * 0.06))
        self.cuadro_inner = pygame.Rect(
            self.rect_cuadro.x + borde,
            self.rect_cuadro.y + borde_v,
            cuadro_w - borde*2,
            cuadro_h - borde_v*2
        )

        def vida_inner(rect):
            xi = rect.x + int(rect.width  * 0.14)
            yi = rect.y + int(rect.height * 0.10)
            wi = int(rect.width  * 0.72)
            hi = int(rect.height * 0.82)
            return pygame.Rect(xi, yi, wi, hi)

        self.vida_inner_blue = vida_inner(self.rect_vida_blue)
        self.vida_inner_red  = vida_inner(self.rect_vida_red)

        self.log = TextLog(self.cuadro_inner, pkm_font(12), fg=PKM_BLACK)

        ci = self.cuadro_inner
        f  = pkm_font(11)
        bh = 28
        bw = (ci.width - 16) // 2
        by = ci.y + ci.height - bh - 4
        self._ctrl_btns = [
            Button(pygame.Rect(ci.x+4, by, bw, bh), "Menu Principal", f, tag="menu", text_align="left"),
            Button(pygame.Rect(ci.x+4+bw+8, by, bw, bh), "Nueva batalla", f, tag="restart", text_align="left"),
        ]
        self._go_btns = []

    def _start_new_game(self):
        pool = POKEMON_DB[:]
        random.shuffle(pool)
        num = self.battle_type
        self.blue_team = []
        self.red_team  = []
        for i in range(num):
            for team_list, offset in [(self.blue_team, 0), (self.red_team, num)]:
                data  = pool[i + offset]
                avail = data["movimientos"][:]
                random.shuffle(avail)
                movs  = []
                for m in avail[:4]:
                    mv = m.copy(); mv["pp"]=mv["ppMax"]; mv["pp_max"]=mv["ppMax"]
                    movs.append(mv)
                team_list.append(BattlePokemon(data, preassigned_moves=movs, level=55))

        self.blue_active_idx = 0
        self.red_active_idx  = 0
        self.turn = 1
        self.blue_hazards = {"stealth_rock":False,"spikes":0,"toxic_spikes":0}
        self.red_hazards  = {"stealth_rock":False,"spikes":0,"toxic_spikes":0}
        self._game_over_active = False
        self.state = self.STATE_RUNNING

        def _make_ia(level, team, enemy, enemy_team):
            if level == 1: return RandomAI(team, enemy)
            if level == 2: return HeuristicAI(team, enemy)
            if level == 3: return MinimaxAI(team, enemy, enemy_team=enemy_team)
            return MinimaxAI(team, enemy, enemy_team=enemy_team)
        self.blue_ia = _make_ia(self.ai_level,  self.blue_team, self.red_team[0],  self.red_team)
        self.red_ia  = _make_ia(self.ai2_level, self.red_team,  self.blue_team[0], self.blue_team)

        self.log.lines = []
        self._pending_log_lines = []
        self._log_callback = None

        self._log_msg("Batalla IA vs IA iniciada!", PKM_BLACK)
        self._log_msg(f"Azul: {', '.join(p.nombre for p in self.blue_team)}", PKM_BLUE)
        self._log_msg(f"Rojo: {', '.join(p.nombre for p in self.red_team)}",  PKM_RED)

        self._hp_anim = {
            "blue": {"cur":1.0,"tgt":1.0,"animating":False,"speed":0.025},
            "red":  {"cur":1.0,"tgt":1.0,"animating":False,"speed":0.025},
        }
        self._turn_pending   = True
        self._last_turn_time = pygame.time.get_ticks()

    def _log_msg(self, msg, color=None):
        self.log.add(msg, color or PKM_BLACK)

    def _log_lines_delayed(self, lines, callback=None):
        self._pending_log_lines = list(lines)
        self._log_callback      = callback
        self._last_log_time     = pygame.time.get_ticks()

    def _tick_log_lines(self):
        if not self._pending_log_lines:
            if self._log_callback:
                cb = self._log_callback; self._log_callback = None; cb()
            return
        now = pygame.time.get_ticks()
        if now - self._last_log_time >= self._log_delay_ms:
            line = self._pending_log_lines.pop(0)
            col = PKM_BLACK
            if line.startswith("[AZUL]"):   col = PKM_BLUE
            elif line.startswith("[ROJO]"): col = PKM_RED
            elif any(x in line for x in ["[DERROTA]","[DANO]"]) or "baja" in line: col = PKM_RED
            elif any(x in line for x in ["[CURACION]","[CRITICO]"]): col = PKM_GREEN
            elif "muy efectivo" in line: col = PKM_GOLD
            elif any(x in line for x in ["[CAMBIO]","[IMPACTO]"]): col = (100,50,160)
            self._log_msg(line, col)
            self._last_log_time = now
            if "[CAMBIO]" in line:
                self._sync_hp_on_switch()
            if "baja" in line or "[CURACION]" in line:
                self._trigger_hp_anim()

    def handle_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.W, self.H = event.w, event.h
            self._load_assets()
            self._compute_layout()
            self._refresh_ui()
            return
        self.log.handle_scroll(event)
        mouse = pygame.mouse.get_pos()
        btns  = self._go_btns if self.state == self.STATE_GAME_OVER else self._ctrl_btns
        for btn in btns: btn.update_hover(mouse)
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for btn in btns:
                if btn.handle_event(event):
                    self._on_btn_click(btn.tag)

    def _on_btn_click(self, tag):
        if tag == "menu":
            if self.on_exit_callback: self.on_exit_callback()
        elif tag == "restart":
            self._start_new_game()

    def _start_turn(self):
        if self._game_over_active: return
        # Sincronizar blue_ia con estado actual
        self.blue_ia.active_idx = self.blue_active_idx
        self.blue_ia.enemy      = self.red_team[self.red_active_idx]
        if hasattr(self.blue_ia, "enemy_team"):
            self.blue_ia.enemy_team = self.red_team
        if hasattr(self.blue_ia, "enemy_active_idx"):
            self.blue_ia.enemy_active_idx = self.red_active_idx
        blue_action = self.blue_ia.get_action()
        self.red_ia.active_idx  = self.red_active_idx
        self.red_ia.enemy       = self.blue_team[self.blue_active_idx]
        if hasattr(self.red_ia, "enemy_team"):
            self.red_ia.enemy_team = self.blue_team
        if hasattr(self.red_ia, "enemy_active_idx"):
            self.red_ia.enemy_active_idx = self.blue_active_idx
        red_action  = self.red_ia.get_action()
        self._execute_turn(blue_action, red_action)

    def _execute_turn(self, blue_action, red_action):
        log_lines   = []
        blue_switch = (blue_action[0]=="switch")
        red_switch  = (red_action[0]=="switch")

        if blue_switch:
            ni=blue_action[1]; e=self.blue_team[ni]
            self.blue_active_idx=ni
            e.mods={"atk":0,"def":0,"spe":0,"evasion":0}
            e.protect_success=True; e.protect_fail_count=0
            log_lines.append(f"[CAMBIO] Equipo AZUL envio a {e.nombre}")
            log_lines+=apply_hazards_on_switch(e,self.red_hazards,True)

        if red_switch:
            ni=red_action[1]; e=self.red_team[ni]
            self.red_active_idx=ni
            e.mods={"atk":0,"def":0,"spe":0,"evasion":0}
            e.protect_success=True; e.protect_fail_count=0
            log_lines.append(f"[CAMBIO] Equipo ROJO envio a {e.nombre}")
            log_lines+=apply_hazards_on_switch(e,self.blue_hazards,False)

        if blue_switch and red_switch:
            self._log_lines_delayed(log_lines[:], self._fin_de_turno)
            return
        if blue_switch:
            rmv=red_action[1]
            self._sim_blue_move_idx=None; self._sim_red_move_idx=rmv
            self._sim_orden=["red"]; self._sim_index=0; self._log_lines_temp=log_lines[:]
            self._log_lines_delayed(log_lines[:], self._procesar_sim)
            return
        if red_switch:
            bmv=blue_action[1]
            self._sim_blue_move_idx=bmv; self._sim_red_move_idx=None
            self._sim_orden=["blue"]; self._sim_index=0; self._log_lines_temp=log_lines[:]
            self._log_lines_delayed(log_lines[:], self._procesar_sim)
            return

        bmv=blue_action[1]; rmv=red_action[1]
        bp=self.blue_team[self.blue_active_idx]; rp=self.red_team[self.red_active_idx]
        bprio=get_priority(bmv,bp); rprio=get_priority(rmv,rp)
        bspd=bp.get_effective_stat("spe"); rspd=rp.get_effective_stat("spe")
        if bprio>rprio: orden=["blue","red"]
        elif rprio>bprio: orden=["red","blue"]
        else: orden=["blue","red"] if bspd>=rspd else ["red","blue"]

        self._sim_blue_move_idx=bmv; self._sim_red_move_idx=rmv
        self._log_lines_temp=log_lines[:]; self._sim_orden=orden; self._sim_index=0
        self._log_lines_delayed(log_lines[:], self._procesar_sim)

    def _procesar_sim(self):
        if self._sim_index >= len(self._sim_orden):
            rest=self._log_lines_temp[:]
            self._log_lines_temp=[]
            self._log_lines_delayed(rest, self._fin_de_turno)
            return
        quien=self._sim_orden[self._sim_index]
        if quien=="blue":
            p=self.blue_team[self.blue_active_idx]
            if p.fainted or p.current_hp<=0: self._sim_index+=1; self._procesar_sim(); return
            mv=self._sim_blue_move_idx
            if mv is not None:
                self._ataque_sim(p,self.red_team[self.red_active_idx],mv,True,
                                 self._log_lines_temp,self._sim_continuar)
            else: self._sim_continuar()
        else:
            p=self.red_team[self.red_active_idx]
            if p.fainted or p.current_hp<=0: self._sim_index+=1; self._procesar_sim(); return
            mv=self._sim_red_move_idx
            if mv is not None:
                self._ataque_sim(p,self.blue_team[self.blue_active_idx],mv,False,
                                 self._log_lines_temp,self._sim_continuar)
            else: self._sim_continuar()

    def _sim_continuar(self):
        self._sim_index+=1; self._procesar_sim()

    def _ataque_sim(self, atacante, defensor, move_idx, es_azul, log_lines, callback):
        if atacante.fainted or atacante.current_hp <= 0: callback(); return
        if defensor.fainted or defensor.current_hp <= 0: callback(); return
        move=atacante.movimientos[move_idx]
        tag="[AZUL]" if es_azul else "[ROJO]"
        log_lines.append(f"{tag} {atacante.nombre} uso {move['nombre']}!")
        if move["pp"]<=0:
            log_lines.append("Sin PP! Fallo.")
            self._log_lines_delayed(log_lines[:],callback); log_lines.clear(); return
        if move["nombre"] not in ["Vuelo","Bote"]: move["pp"]-=1
        if not rand(move["precision"]):
            log_lines.append(f"{atacante.nombre} fallo!")
            self._log_lines_delayed(log_lines[:],callback); log_lines.clear(); return
        effect_msgs=[]
        if move["poder"]>0:
            if hasattr(defensor,'is_protected') and defensor.is_protected:
                log_lines.append(f"[DEFENSA] {defensor.nombre} se protecio!")
                defensor.is_protected=False
                self._log_lines_delayed(log_lines[:],callback); log_lines.clear(); return
            damage,type_mult=calculate_damage(atacante,defensor,move)
            if rand(0.0625): damage=int(damage*1.5); log_lines.append("[CRITICO] Golpe critico!")
            defensor.current_hp=max(0,defensor.current_hp-damage)
            murio=(defensor.current_hp<=0)
            if type_mult>=2:   log_lines.append(f"Es muy efectivo! (x{type_mult})")
            elif type_mult==0: log_lines.append(f"No afecta a {defensor.nombre}!"); defensor.current_hp=min(defensor.max_hp,defensor.current_hp+damage); murio=False
            elif type_mult<1:  log_lines.append(f"No es muy efectivo... (x{type_mult})")
            log_lines.append(f"{defensor.nombre} baja {damage} de vida.")
            if move["nombre"] in ["Gigadrenado","Puno Drenaje"]:
                d=int(damage*0.5); atacante.heal(d); log_lines.append(f"[CURACION] {atacante.nombre} absorbe {d} HP!")
            if move["nombre"]=="Pajaro Osado":
                r=int(damage/3); atacante.apply_damage(r,True); log_lines.append(f"{atacante.nombre} recibe {r} de retroceso.")
            if murio:
                defensor.fainted = True
                log_lines.append(f"[DERROTA] {defensor.nombre} derrotado!")
            apply_move_effects(atacante,defensor,move,effect_msgs,es_azul,self.blue_hazards,self.red_hazards)
            log_lines+=effect_msgs
        else:
            apply_move_effects(atacante,defensor,move,effect_msgs,es_azul,self.blue_hazards,self.red_hazards)
            log_lines+=effect_msgs
        self._log_lines_delayed(log_lines[:],callback); log_lines.clear()

    def _fin_de_turno(self):
        if self._game_over_active: return
        self.turn+=1
        self._apply_end_effects()
        self._refresh_ui()
        self._verify_defeated()
        if not self._game_over_active:
            self._turn_pending=True; self._last_turn_time=pygame.time.get_ticks()

    def _apply_end_effects(self):
        bp=self.blue_team[self.blue_active_idx]
        rp=self.red_team[self.red_active_idx]
        for pokemon in [bp,rp]:
            if pokemon.fainted: continue
            if pokemon.status=="burn":
                d=max(1,int(pokemon.max_hp/16)); pokemon.apply_damage(d,True)
                self._log_msg(f"{pokemon.nombre} baja {d} de vida (quemadura).",PKM_RED)
            elif pokemon.status=="poison":
                d=max(1,int(pokemon.max_hp/16)); pokemon.apply_damage(d,True)
                self._log_msg(f"{pokemon.nombre} baja {d} de vida (veneno).",(140,0,180))
            elif pokemon.status=="toxic":
                d=max(1,int(pokemon.max_hp/16*pokemon.poison_counter))
                pokemon.poison_counter+=1; pokemon.apply_damage(d,True)
                self._log_msg(f"{pokemon.nombre} baja {d} de vida (veneno grave).",(100,0,150))
            elif pokemon.status=="infectado":
                d=max(1,int(pokemon.max_hp/8)); pokemon.apply_damage(d,True)
                self._log_msg(f"{pokemon.nombre} baja {d} de vida (drenadoras).",PKM_GREEN)
            if pokemon.current_hp<=0 and not pokemon.fainted:
                pokemon.fainted=True; self._log_msg(f"[DERROTA] {pokemon.nombre} derrotado!",PKM_RED)
        for p in [bp,rp]:
            wh=getattr(p,'wish_heal',0)
            if wh and not p.fainted:
                p.heal(wh); self._log_msg(f"[CURACION] {p.nombre} Deseo +{wh}HP.",PKM_GREEN); p.wish_heal=0

    def _verify_defeated(self):
        for p in self.blue_team:
            if p.current_hp<=0 and not p.fainted: p.fainted=True
        for p in self.red_team:
            if p.current_hp<=0 and not p.fainted: p.fainted=True
        bp=self.blue_team[self.blue_active_idx]; rp=self.red_team[self.red_active_idx]
        ba=[i for i,p in enumerate(self.blue_team) if not p.fainted]
        ra=[i for i,p in enumerate(self.red_team)  if not p.fainted]
        if not ba: self._game_over("red"); return
        if not ra: self._game_over("blue"); return
        if bp.fainted and ba:
            best=max(ba,key=lambda i:self.blue_team[i].current_hp)
            self.blue_active_idx=best; new=self.blue_team[best]
            new.mods={"atk":0,"def":0,"spe":0,"evasion":0}
            new.protect_success=True; new.protect_fail_count=0
            msgs=apply_hazards_on_switch(new,self.red_hazards,True)
            for m in msgs: self._log_msg(m,PKM_RED)
            self._log_msg(f"[CAMBIO] 🔄 Equipo AZUL envió a {new.nombre}!",PKM_BLUE)
            # Sincronizar enemy_active_idx de la IA roja
            if hasattr(self.red_ia, "enemy_active_idx"):
                self.red_ia.enemy_active_idx = self.blue_active_idx
        if rp.fainted and ra:
            best=max(ra,key=lambda i:self.red_team[i].current_hp)
            self.red_active_idx=best; new=self.red_team[best]
            new.mods={"atk":0,"def":0,"spe":0,"evasion":0}
            new.protect_success=True; new.protect_fail_count=0
            msgs=apply_hazards_on_switch(new,self.blue_hazards,False)
            for m in msgs: self._log_msg(m,PKM_RED)
            self._log_msg(f"[CAMBIO] 🔄 Equipo ROJO envió a {new.nombre}!",PKM_RED)
            # Sincronizar enemy_active_idx de la IA azul
            if hasattr(self.blue_ia, "enemy_active_idx"):
                self.blue_ia.enemy_active_idx = self.red_active_idx
        self._refresh_ui()

    def _game_over(self, winner):
        if self._game_over_active: return
        self._game_over_active=True
        registrar_resultado_simulation(winner,self.ai_level,self.ai2_level)
        self.state=self.STATE_GAME_OVER
        if winner=="blue":
            msg=f"VICTORIA EQUIPO AZUL! IA Nv{self.ai_level} gano."; col=PKM_BLUE
        else:
            msg=f"VICTORIA EQUIPO ROJO! IA Nv{self.ai2_level} gano."; col=PKM_RED
        self._go_msg=msg; self._go_col=col
        ci=self.cuadro_inner; f=pkm_font(12); bh=30
        bw=(ci.width-16)//2; by=ci.y+ci.height-bh-4
        self._go_btns=[
            Button(pygame.Rect(ci.x+4,by,bw,bh),"Nueva batalla",f,tag="restart",text_align="left"),
            Button(pygame.Rect(ci.x+4+bw+8,by,bw,bh),"Menu Principal",f,tag="menu",text_align="left"),
        ]

    def _sync_hp_on_switch(self):
        """Salta la barra al HP real del nuevo Pokémon activo (sin animación)."""
        if not self.blue_team or not self.red_team: return
        bp = self.blue_team[self.blue_active_idx]
        rp = self.red_team[self.red_active_idx]
        for key, poke in (("blue", bp), ("red", rp)):
            pct = max(0.0, poke.current_hp / poke.max_hp)
            self._hp_anim[key]["cur"]       = pct
            self._hp_anim[key]["tgt"]       = pct
            self._hp_anim[key]["animating"] = False

    def _trigger_hp_anim(self):
        """Lanza animación suave de HP desde el valor actual al HP real."""
        if not self.blue_team or not self.red_team: return
        bp = self.blue_team[self.blue_active_idx]
        rp = self.red_team[self.red_active_idx]
        for key, poke in (("blue", bp), ("red", rp)):
            pct = max(0.0, poke.current_hp / poke.max_hp)
            a   = self._hp_anim[key]
            if abs(pct - a["cur"]) > 0.005:
                a["tgt"]       = pct
                a["animating"] = True

    def _refresh_ui(self):
        if not self.blue_team or not self.red_team: return
        bp=self.blue_team[self.blue_active_idx]; rp=self.red_team[self.red_active_idx]
        self._hp_anim["blue"]["tgt"]=max(0,bp.current_hp/bp.max_hp)
        self._hp_anim["red"]["tgt"] =max(0,rp.current_hp/rp.max_hp)

    def update(self):
        self._tick_log_lines()
        for key in ("blue","red"):
            a = self._hp_anim[key]
            if a.get("animating", False):
                diff = a["tgt"] - a["cur"]
                if abs(diff) > 0.003:
                    a["cur"] += diff * a.get("speed", 0.025)
                else:
                    a["cur"] = a["tgt"]
                    a["animating"] = False
        if self._turn_pending and not self._pending_log_lines and not self._log_callback:
            now=pygame.time.get_ticks()
            if now-self._last_turn_time>=self._turn_delay_ms:
                self._turn_pending=False; self._start_turn()

    def draw(self):
        if self.bg_surf: self.screen.blit(self.bg_surf,(0,0))
        else: self.screen.fill(BG)

        self._draw_vida_panels()
        self._draw_sprites()
        self._draw_cuadro()

    def _draw_vida_panels(self):
        if not self.blue_team or not self.red_team: return
        bp=self.blue_team[self.blue_active_idx]; rp=self.red_team[self.red_active_idx]
        self._draw_one_vida(self.rect_vida_blue,self.vida_inner_blue,
                            bp,self.blue_team,self.blue_active_idx,
                            f"IA Nivel {self.ai_level}",self._hp_anim["blue"]["cur"],PKM_BLUE, flip=True)
        self._draw_one_vida(self.rect_vida_red,self.vida_inner_red,
                            rp,self.red_team,self.red_active_idx,
                            f"IA Nivel {self.ai2_level}",self._hp_anim["red"]["cur"],PKM_RED, flip=False)
        # Iconos debajo de cada cuadro
        dot_size = max(10, int(self.vida_w * 0.055))
        gap      = max(2, int(dot_size * 0.35))
        for team, rect, active_idx in [
            (self.blue_team, self.rect_vida_blue, self.blue_active_idx),
            (self.red_team,  self.rect_vida_red,  self.red_active_idx)
        ]:
            total_w = len(team) * dot_size + (len(team)-1) * gap
            sx = rect.x + (rect.width - total_w) // 2
            sy = rect.bottom + 3
            for i, p in enumerate(team):
                cx = sx + i*(dot_size+gap) + dot_size//2
                cy = sy + dot_size//2
                icon = self.icon_muerto if p.fainted else self.icon_vivo
                if icon:
                    si = pygame.transform.smoothscale(icon, (dot_size, dot_size))
                    self.screen.blit(si, (cx-dot_size//2, cy-dot_size//2))
                else:
                    color  = (68,68,68) if p.fainted else HP_GREEN_PKM
                    border = (180,120,0) if i==active_idx else PKM_BLACK
                    pygame.draw.circle(self.screen, color,  (cx,cy), dot_size//2)
                    pygame.draw.circle(self.screen, border, (cx,cy), dot_size//2, 2)

    def _draw_one_vida(self, rect, inner, poke, team, active_idx, label, hp_cur, name_col, flip=False):
        if self.vida_surf:
            surf = pygame.transform.flip(self.vida_surf, True, False) if flip else self.vida_surf
            self.screen.blit(surf, rect.topleft)
        else:
            pygame.draw.rect(self.screen,(255,255,255),rect)
            pygame.draw.rect(self.screen,PKM_BLACK,rect,2)

        elem_h   = max(1, inner.height // 4)
        base_sz  = max(6, min(elem_h - 2, 13))
        f_owner  = pkm_font(base_sz)
        f_name   = pkm_font(base_sz)
        f_hp     = pkm_font(base_sz)
        f_status = pkm_font(max(5, base_sz - 1))

        x = inner.x + 4
        y = inner.y + 2

        draw_text(self.screen, label, x, y, f_owner, name_col)
        y += f_owner.get_height() + 1

        draw_text(self.screen, f"{poke.nombre} N{poke.level}", x, y, f_name, PKM_BLACK)
        y += f_name.get_height() + 2

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

        bar_w = inner.width - 8
        bar_h = max(6, int(inner.height * 0.12))
        draw_hp_bar(self.screen, pygame.Rect(x,y,bar_w,bar_h), hp_cur, dark_bg=False)
        # Iconos dibujados en _draw_vida_panels debajo del cuadro

    def _draw_sprites(self):
        if not self.blue_team or not self.red_team: return
        bp = self.blue_team[self.blue_active_idx]
        rp = self.red_team[self.red_active_idx]
        
        for poke, rect, do_flip in [
            (bp, self.rect_sprite_blue, True),
            (rp, self.rect_sprite_red,  False)
        ]:
            gif = self._get_poke_gif(poke.nombre)
            img = gif.get_frame() if gif and gif.is_valid() else None
            if img:
                iw, ih = img.get_size()
                scale = min(rect.width / iw, rect.height / ih)
                nw, nh = int(iw * scale), int(ih * scale)
                if img.get_flags() & pygame.SRCALPHA:
                    scaled = pygame.transform.smoothscale(img, (nw, nh))
                else:
                    scaled = pygame.transform.smoothscale(img.convert_alpha(), (nw, nh))
                if do_flip:
                    scaled = pygame.transform.flip(scaled, True, False)
                ix = rect.x + (rect.width - nw) // 2
                iy = rect.y + (rect.height - nh) // 2
                if poke.fainted:
                    grey = pygame.Surface((nw, nh), pygame.SRCALPHA)
                    grey.fill((100, 100, 100, 180))
                    scaled.blit(grey, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
                self.screen.blit(scaled, (ix, iy))
        
        f_turn = pkm_font(13)
        lbl_az = f"IA Azul Nv{self.ai_level}" + (" (MM)" if self.ai_level in (3,4) else "")
        lbl_ro = f"IA Roja Nv{self.ai2_level}" + (" (MM)" if self.ai2_level in (3,4) else "")
        draw_text(self.screen, f"Turno {self.turn}  -  {lbl_az} vs {lbl_ro}",
                self.W//2, self.rect_sprite_zone.y+4, f_turn, (255,255,255), center=True)

    def _draw_cuadro(self):
        if self.cuadro_surf: self.screen.blit(self.cuadro_surf,self.rect_cuadro.topleft)
        else:
            pygame.draw.rect(self.screen,(255,255,255),self.rect_cuadro)
            pygame.draw.rect(self.screen,PKM_BLACK,self.rect_cuadro,3)

        self.log.draw(self.screen)

        f=pkm_font(12)
        btns=self._go_btns if self.state==self.STATE_GAME_OVER else self._ctrl_btns
        mouse=pygame.mouse.get_pos()
        for btn in btns:
            btn.update_hover(mouse)
            col = SEL_COL if btn.hovered else (PKM_RED if btn.tag=="menu" else NORM_COL)
            cursor="> " if btn.hovered else "  "
            rendered=f.render(cursor+btn.text,True,col)
            r=rendered.get_rect(midleft=(btn.rect.x+4,btn.rect.centery))
            self.screen.blit(rendered,r)
            pygame.draw.line(self.screen,(200,200,200),
                             (btn.rect.x,btn.rect.bottom),(btn.rect.right,btn.rect.bottom),1)

        if self.state==self.STATE_GAME_OVER:
            f_go=pkm_font(13)
            ci=self.cuadro_inner
            draw_text(self.screen,self._go_msg,ci.centerx,ci.y+6,f_go,self._go_col,center=True)