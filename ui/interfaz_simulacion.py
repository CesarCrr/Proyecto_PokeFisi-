import tkinter as tk
from tkinter import ttk
import random
from datos.datos_pokemon import POKEMON_DB
from models.clase_batalla import BattlePokemon
from batalla.logica_batalla import calculate_damage, get_priority
from batalla.peligros import apply_hazards_on_switch
from batalla.efectos import apply_move_effects
from utiles.funciones_auxiliares import rand, clamp
from ia.ia_levels import RandomAI, HeuristicAI
from utiles.estadisticas import registrar_resultado_simulation

# Colores
TYPE_COLORS = {
    "Dragon": ("#6f35fc", "#fff"), "Fantasma": ("#735797", "#fff"),
    "Tierra": ("#e2bf65", "#333"), "Fuego": ("#ff9c54", "#333"),
    "Agua": ("#6390f0", "#fff"), "Planta": ("#7ac74c", "#333"),
    "Electrico": ("#f7d02c", "#333"), "Hielo": ("#96d9d6", "#333"),
    "Psiquico": ("#f95587", "#fff"), "Lucha": ("#c22e28", "#fff"),
    "Acero": ("#b7b7ce", "#333"), "Volador": ("#a98ff3", "#fff"),
    "Hada": ("#d685ad", "#fff"), "Bicho": ("#a6b91a", "#333"),
    "Veneno": ("#a33ea1", "#fff"), "Siniestro": ("#705746", "#fff"),
    "Normal": ("#a8a77a", "#333"), "Roca": ("#b6a136", "#333"),
}

STATUS_COLORS = {
    "burn": "#ff7043", "poison": "#9c27b0", "toxic": "#6a0dad",
    "paralyze": "#ffc107", "sleep": "#607d8b", "freeze": "#80deea",
    "infectado": "#4caf50",
}

STATUS_LABELS = {
    "burn": "QUEMADO", "poison": "VENENO", "toxic": "VEN. GRAVE",
    "paralyze": "PARÁLISIS", "sleep": "DORMIDO", "freeze": "CONGELADO",
    "infectado": "INFECTADO",
}

BG = "#1a1a2e"
BG2 = "#16213e"
BG3 = "#0f3460"
ACCENT = "#e94560"
GOLD = "#f5a623"
TEXTCOL = "#e2e8f0"
TEXT2 = "#94a3b8"
GREEN = "#4ade80"
RED_COL = "#f87171"
BLUE_C = "#60a5fa"


class PokemonSimulationGUI(tk.Frame):
    #Ventana para modo espectador IA vs IA
    def __init__(self, parent, ai_level=1, ai2_level=1, battle_type=4, on_exit_callback=None):
        super().__init__(parent, bg=BG)
        self.parent = parent
        self.root = parent
        self.ai_level = ai_level
        self.ai2_level = ai2_level
        self.battle_type = battle_type
        self.on_exit_callback = on_exit_callback
        self.root.title("PokeFisi - IA vs IA (Espectador)")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.minsize(820, 620)

        self.blue_team = []
        self.red_team = []
        self.blue_active_idx = 0
        self.red_active_idx = 0
        self.turn = 1
        self.blue_ia = None
        self.red_ia = None
        self.blue_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        self.red_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        self._game_over_active = False
        self._sim_player_move_idx = None
        self._sim_ai_move_idx = None
        self._sim_orden = []
        self._sim_index = 0
        self._log_lines_temp = []
        self._cola_acciones = []
        
        self.pack(fill="both", expand=True)
        self._build_ui()
        self._start_new_game()

    def _build_ui(self):
        top = tk.Frame(self, bg=BG3, pady=6)
        top.pack(fill="x")
        self.lbl_turn = tk.Label(top, text="TURNO 1", font=("Courier", 13, "bold"),
                                 bg=BG3, fg=GOLD)
        self.lbl_turn.pack()

        mid = tk.Frame(self, bg=BG)
        mid.pack(fill="x", padx=12, pady=8)
        mid.columnconfigure(0, weight=1)
        mid.columnconfigure(1, weight=1)

        self.frame_blue = self._make_pokemon_panel(mid, "IA AZUL", BLUE_C, 0)
        self.frame_red = self._make_pokemon_panel(mid, "IA ROJA", ACCENT, 1)

        log_frame = tk.Frame(self, bg=BG2, bd=1, relief="flat")
        log_frame.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(log_frame, text="LOG DE BATALLA", font=("Courier", 9, "bold"),
                 bg=BG2, fg=TEXT2).pack(anchor="w", padx=8, pady=(4,0))
        self.log_text = tk.Text(log_frame, height=10, bg=BG2, fg=TEXTCOL,
                                font=("Courier", 10), state="disabled",
                                relief="flat", wrap="word", bd=0,
                                selectbackground=BG3)
        self.log_text.pack(fill="x", padx=8, pady=(2, 6))
        self.log_text.tag_config("blue", foreground=BLUE_C)
        self.log_text.tag_config("red", foreground=ACCENT)
        self.log_text.tag_config("effect", foreground="#c084fc")
        self.log_text.tag_config("info", foreground=TEXT2)
        self.log_text.tag_config("crit", foreground=GOLD)
        self.log_text.tag_config("good", foreground=GREEN)

        # Botón para volver al menú
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="VOLVER AL MENÚ",
                  font=("Courier", 10, "bold"), bg=BLUE_C, fg="#1a1a2e",
                  relief="flat", bd=0, padx=20, pady=8, cursor="hand2",
                  command=self._exit_to_menu).pack()

    def _make_pokemon_panel(self, parent, title, color, col):
        frame = tk.Frame(parent, bg=BG2, bd=0, relief="flat",
                         highlightthickness=2, highlightbackground=color)
        frame.grid(row=0, column=col, sticky="nsew", padx=6, pady=4)

        tk.Label(frame, text=title, font=("Courier", 10, "bold"),
                 bg=BG2, fg=color).pack(anchor="w", padx=10, pady=(8,2))

        name_row = tk.Frame(frame, bg=BG2)
        name_row.pack(fill="x", padx=10)
        name_lbl = tk.Label(name_row, text="—", font=("Courier", 13, "bold"),
                             bg=BG2, fg=TEXTCOL)
        name_lbl.pack(side="left")
        status_lbl = tk.Label(name_row, text="", font=("Courier", 8, "bold"),
                              bg=BG2, fg=TEXTCOL, padx=4, pady=1)
        status_lbl.pack(side="left", padx=6)

        type_row = tk.Frame(frame, bg=BG2)
        type_row.pack(anchor="w", padx=10, pady=2)
        type1_lbl = tk.Label(type_row, text="", font=("Courier", 8, "bold"),
                             padx=5, pady=1)
        type1_lbl.pack(side="left", padx=(0,3))
        type2_lbl = tk.Label(type_row, text="", font=("Courier", 8, "bold"),
                             padx=5, pady=1)
        type2_lbl.pack(side="left")

        hp_frame = tk.Frame(frame, bg=BG2)
        hp_frame.pack(fill="x", padx=10, pady=(4,2))
        hp_info = tk.Label(hp_frame, text="HP  100/100 (100%)",
                           font=("Courier", 9), bg=BG2, fg=TEXT2)
        hp_info.pack(anchor="w")

        canvas = tk.Canvas(hp_frame, height=14, bg=BG3, bd=0,
                           highlightthickness=0, relief="flat")
        canvas.pack(fill="x", pady=(3,0))
        bar_id = canvas.create_rectangle(0, 0, 0, 14, fill=GREEN, outline="")

        dots_frame = tk.Frame(frame, bg=BG2)
        dots_frame.pack(anchor="w", padx=10, pady=(4,8))
        dots = []
        for _ in range(4):
            c = tk.Canvas(dots_frame, width=14, height=14, bg=BG2,
                          bd=0, highlightthickness=0)
            c.pack(side="left", padx=2)
            oid = c.create_oval(1, 1, 13, 13, fill=GREEN, outline="")
            dots.append((c, oid))

        widgets = {
            "name": name_lbl, "status": status_lbl,
            "type1": type1_lbl, "type2": type2_lbl,
            "hp_info": hp_info,
            "canvas": canvas, "bar_id": bar_id,
            "bar_target": 1.0,
            "bar_current": 1.0,
            "dots": dots,
        }
        if col == 0:
            self._blue_widgets = widgets
        else:
            self._red_widgets = widgets
        return frame

    def _start_new_game(self):
        pool = POKEMON_DB[:]
        random.shuffle(pool)
        
        num_pokemon = self.battle_type
        
        # Generar equipo AZUL
        self.blue_team = []
        for i in range(num_pokemon):
            data = pool[i] if i < len(pool) else pool[0]
            available_moves = data["movimientos"][:]
            random.shuffle(available_moves)
            movimientos = []
            for m in available_moves[:4]:
                move = m.copy()
                move["pp"] = move["ppMax"]
                move["pp_max"] = move["ppMax"]
                movimientos.append(move)
            self.blue_team.append(BattlePokemon(data, preassigned_moves=movimientos, level=55))
        
        # Generar equipo ROJO
        self.red_team = []
        for i in range(num_pokemon):
            data = pool[i + num_pokemon] if len(pool) >= num_pokemon * 2 else pool[i % len(pool)]
            available_moves = data["movimientos"][:]
            random.shuffle(available_moves)
            movimientos = []
            for m in available_moves[:4]:
                move = m.copy()
                move["pp"] = move["ppMax"]
                move["pp_max"] = move["ppMax"]
                movimientos.append(move)
            self.red_team.append(BattlePokemon(data, preassigned_moves=movimientos, level=55))
        
        # Inicializar IAs
        if self.ai_level == 1:
            self.blue_ia = RandomAI(self.blue_team, self.red_team[0])
        else:
            self.blue_ia = HeuristicAI(self.blue_team, self.red_team[0])
        
        if self.ai2_level == 1:
            self.red_ia = RandomAI(self.red_team, self.blue_team[0])
        else:
            self.red_ia = HeuristicAI(self.red_team, self.blue_team[0])
        
        # Iniciar batalla directamente
        self._iniciar_batalla()

    def _iniciar_batalla(self):
        self.blue_active_idx = 0
        self.red_active_idx = 0
        self.turn = 1
        self.blue_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        self.red_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}

        lines = ["¡Equipos generados aleatoriamente!",
                f"Equipo AZUL (IA nivel {self.ai_level}): {', '.join(p.nombre for p in self.blue_team)}",
                f"Equipo ROJO (IA nivel {self.ai2_level}): {', '.join(p.nombre for p in self.red_team)}",
                "¡Que comience la batalla!"]
        for l in lines:
            self._log(l, "info")

        self._refresh_ui()
        self.root.after(1000, self._start_turn)

    def _update_panel(self, w, poke, team, active_idx):
        w["name"].config(text=f"{poke.nombre} (N{poke.level})")
        t1c = TYPE_COLORS.get(poke.tipo1, ("#888", "#fff"))
        w["type1"].config(text=poke.tipo1, bg=t1c[0], fg=t1c[1])
        if poke.tipo2:
            t2c = TYPE_COLORS.get(poke.tipo2, ("#888", "#fff"))
            w["type2"].config(text=poke.tipo2, bg=t2c[0], fg=t2c[1])
        else:
            w["type2"].config(text="", bg=BG2)
        if poke.status:
            sc = STATUS_COLORS.get(poke.status, "#888")
            w["status"].config(text=STATUS_LABELS.get(poke.status, poke.status.upper()),
                               bg=sc, fg="#fff")
        else:
            w["status"].config(text="", bg=BG2)
        pct = max(0, poke.current_hp / poke.max_hp)
        w["hp_info"].config(text=f"HP  {poke.current_hp}/{poke.max_hp}  ({int(pct*100)}%)")
        w["bar_target"] = pct
        self._animate_hp_bar(w)
        
        num_pokemon = len(team)
        for i, (c, oid) in enumerate(w["dots"]):
            if i < num_pokemon:
                p = team[i]
                fill = "#444" if p.fainted else GREEN
                outline = GOLD if i == active_idx else "#333"
                c.itemconfig(oid, fill=fill, outline=outline)
                c.config(highlightbackground=outline if i == active_idx else BG2)
                c.pack(side="left", padx=2)
            else:
                c.pack_forget()

    def _animate_hp_bar(self, w):
        target = w["bar_target"]
        current = w["bar_current"]
        step = 0.008

        if abs(current - target) <= 0.002:
            w["bar_current"] = target
            self._draw_hp_bar(w, target)
            return
        
        if current > target:
            new_current = max(target, current - step)
            w["bar_current"] = new_current
            self._draw_hp_bar(w, new_current)
            self.root.after(20, lambda: self._animate_hp_bar(w))
        else:
            new_current = min(target, current + step)
            w["bar_current"] = new_current
            self._draw_hp_bar(w, new_current)
            self.root.after(20, lambda: self._animate_hp_bar(w))

    def _draw_hp_bar(self, w, pct):
        canvas = w["canvas"]
        bar_id = w["bar_id"]
        canvas.update_idletasks()
        W = canvas.winfo_width()
        if W < 2:
            W = 200
        filled_w = int(W * pct)
        if pct > 0.5:
            color = GREEN
        elif pct > 0.2:
            color = GOLD
        else:
            color = RED_COL
        canvas.coords(bar_id, 0, 0, filled_w, 14)
        canvas.itemconfig(bar_id, fill=color)

    def _refresh_ui(self):
        if not self.blue_team or not self.red_team:
            return
        if self.blue_active_idx >= len(self.blue_team):
            self.blue_active_idx = 0
        if self.red_active_idx >= len(self.red_team):
            self.red_active_idx = 0
            
        bp = self.blue_team[self.blue_active_idx]
        rp = self.red_team[self.red_active_idx]
        self.lbl_turn.config(text=f"TURNO {self.turn}")
        self._update_panel(self._blue_widgets, bp, self.blue_team, self.blue_active_idx)
        self._update_panel(self._red_widgets, rp, self.red_team, self.red_active_idx)
        
        self.root.update_idletasks()

    def _log(self, msg, tag="info"):
        self.log_text.config(state="normal")
        self.log_text.insert("end", msg + "\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _log_lines(self, lines):
        def show_next(idx):
            if idx >= len(lines):
                self._refresh_ui()
                self._verify_defeated()
                return
            line = lines[idx]
            tag = "info"
            if line.startswith("[AZUL]"):
                tag = "blue"
            elif line.startswith("[ROJO]"):
                tag = "red"
            elif any(x in line for x in ["[IMPACTO]","[CAMBIO]","[EFECTO]","[DAÑO]","[PARALISIS]","[CONGELACION]","[DERROTA]","[CURACION]","[DEFENSA]","[ESTADO]"]):
                tag = "effect"
            elif "¡Es muy efectivo" in line:
                tag = "crit"
            self._log(line, tag)
            
            bp = self.blue_team[self.blue_active_idx]
            rp = self.red_team[self.red_active_idx]
            self._update_panel(self._blue_widgets, bp, self.blue_team, self.blue_active_idx)
            self._update_panel(self._red_widgets, rp, self.red_team, self.red_active_idx)
            
            self.root.after(800, lambda: show_next(idx + 1))

        show_next(0)

    def _start_turn(self):
        if self._game_over_active:
            return

        # Actualizar índices y enemy en ambas IAs antes de pedir acción
        self.blue_ia.active_idx = self.blue_active_idx
        self.blue_ia.enemy    = self.red_team[self.red_active_idx]
        self.red_ia.active_idx = self.red_active_idx
        self.red_ia.enemy     = self.blue_team[self.blue_active_idx]

        blue_action = self.blue_ia.get_action()
        red_action  = self.red_ia.get_action()

        self._execute_turn(blue_action, red_action)
        # El siguiente turno se programa desde _fin_de_turno() una vez
        # que toda la cadena asíncrona termina.

    def _execute_turn(self, blue_action, red_action):
        log_lines = []

        blue_switch = blue_action[0] == "switch"
        red_switch  = red_action[0]  == "switch"

        # ── Cambios simultáneos ──────────────────────────────────────────
        if blue_switch:
            nuevo_idx       = blue_action[1]
            entrante        = self.blue_team[nuevo_idx]
            old             = self.blue_team[self.blue_active_idx].nombre
            self.blue_active_idx = nuevo_idx
            entrante.mods   = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
            entrante.protect_success    = True
            entrante.protect_fail_count = 0
            log_lines.append(f"[CAMBIO] {entrante.nombre} fue enviado! El equipo AZUL envió a {entrante.nombre}")
            log_lines += apply_hazards_on_switch(entrante, self.red_hazards, True)

        if red_switch:
            nuevo_idx       = red_action[1]
            entrante        = self.red_team[nuevo_idx]
            old             = self.red_team[self.red_active_idx].nombre
            self.red_active_idx = nuevo_idx
            entrante.mods   = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
            entrante.protect_success    = True
            entrante.protect_fail_count = 0
            log_lines.append(f"[CAMBIO] {entrante.nombre} fue enviado! El equipo ROJO envió a {entrante.nombre}")
            log_lines += apply_hazards_on_switch(entrante, self.blue_hazards, False)

        # ── Caso: ambos cambian — finalizar turno ────────────────────────
        if blue_switch and red_switch:
            self._log_lines_temp = log_lines
            self._mostrar_log_y_cerrar_turno()
            return

        # ── Caso: un bando cambia, el otro ataca ────────────────────────
        #   El atacante ejecuta su movimiento DESPUÉS de mostrar el log de cambio.
        if blue_switch and not red_switch:
            red_move_idx = red_action[1]
            self._log_lines_temp = log_lines
            self._sim_blue_move_idx = None
            self._sim_red_move_idx  = red_move_idx
            # El que ataca tras el cambio rival siempre va segundo (tras el switch)
            self._sim_orden  = ["red"]
            self._sim_index  = 0
            self._mostrar_log_y_atacar()
            return

        if red_switch and not blue_switch:
            blue_move_idx = blue_action[1]
            self._log_lines_temp = log_lines
            self._sim_blue_move_idx = blue_move_idx
            self._sim_red_move_idx  = None
            self._sim_orden  = ["blue"]
            self._sim_index  = 0
            self._mostrar_log_y_atacar()
            return

        # ── Caso: ambos atacan — determinar orden por prioridad / velocidad
        blue_move_idx = blue_action[1]
        red_move_idx  = red_action[1]
        blue_pokemon  = self.blue_team[self.blue_active_idx]
        red_pokemon   = self.red_team[self.red_active_idx]

        blue_priority = get_priority(blue_move_idx, blue_pokemon)
        red_priority  = get_priority(red_move_idx,  red_pokemon)
        blue_speed    = blue_pokemon.get_effective_stat("spe")
        red_speed     = red_pokemon.get_effective_stat("spe")

        if blue_priority > red_priority:
            orden = ["blue", "red"]
        elif red_priority > blue_priority:
            orden = ["red", "blue"]
        else:
            orden = ["blue", "red"] if blue_speed >= red_speed else ["red", "blue"]

        self._sim_blue_move_idx = blue_move_idx
        self._sim_red_move_idx  = red_move_idx
        self._log_lines_temp    = log_lines
        self._sim_orden         = orden
        self._sim_index         = 0
        self._procesar_accion_simulacion()

    # ── helpers asíncronos ───────────────────────────────────────────────

    def _mostrar_log_y_cerrar_turno(self):
        """Muestra el log pendiente y cierra el turno (solo hubo cambios)."""
        lines = self._log_lines_temp[:]
        self._log_lines_temp = []

        def after_log():
            self._fin_de_turno()

        self._log_lines_async(lines, after_log)

    def _mostrar_log_y_atacar(self):
        """Muestra el log de cambio y luego ejecuta los ataques pendientes."""
        lines = self._log_lines_temp[:]
        self._log_lines_temp = []

        def after_log():
            self._procesar_accion_simulacion()

        self._log_lines_async(lines, after_log)

    def _fin_de_turno(self):
        """Cierra el turno: efectos de fin, verificar KOs y programar el siguiente."""
        if self._game_over_active:
            return
        self.turn += 1
        self._apply_end_turn_effects()
        self._refresh_ui()
        self._verify_defeated()
        if not self._game_over_active:
            self.root.after(1200, self._start_turn)

    def _log_lines_async(self, lines, on_done):
        """Muestra una lista de líneas de log con delay entre cada una,
        luego llama a on_done()."""
        if not lines:
            on_done()
            return

        def show_next(idx):
            if idx >= len(lines):
                self._refresh_ui()
                on_done()
                return
            line = lines[idx]
            tag = "info"
            if line.startswith("[AZUL]"):
                tag = "blue"
            elif line.startswith("[ROJO]"):
                tag = "red"
            elif any(x in line for x in ["[IMPACTO]","[CAMBIO]","[EFECTO]","[DAÑO]","[PARALISIS]","[CONGELACION]","[DERROTA]","[CURACION]","[DEFENSA]","[ESTADO]"]):
                tag = "effect"
            elif "¡Es muy efectivo" in line:
                tag = "crit"
            self._log(line, tag)
            bp = self.blue_team[self.blue_active_idx]
            rp = self.red_team[self.red_active_idx]
            self._update_panel(self._blue_widgets, bp, self.blue_team, self.blue_active_idx)
            self._update_panel(self._red_widgets, rp, self.red_team, self.red_active_idx)
            self.root.after(500, lambda: show_next(idx + 1))

        show_next(0)

    # ────────────────────────────────────────────────────────────────────

    def _procesar_accion_simulacion(self):
        if self._sim_index >= len(self._sim_orden):
            # Todos los ataques ejecutados → cerrar turno
            remaining = self._log_lines_temp[:]
            self._log_lines_temp = []

            def after_log():
                self._fin_de_turno()

            self._log_lines_async(remaining, after_log)
            return

        quien = self._sim_orden[self._sim_index]

        if quien == "blue":
            pokemon = self.blue_team[self.blue_active_idx]
            if pokemon.fainted:
                self._sim_index += 1
                self._procesar_accion_simulacion()
                return
            move_idx = self._sim_blue_move_idx
            if move_idx is not None:
                self._ejecutar_ataque_simulacion(
                    self.blue_team[self.blue_active_idx],
                    self.red_team[self.red_active_idx],
                    move_idx, True,
                    self._log_lines_temp,
                    self._sim_continuar
                )
            else:
                self._sim_continuar()
        else:
            pokemon = self.red_team[self.red_active_idx]
            if pokemon.fainted:
                self._sim_index += 1
                self._procesar_accion_simulacion()
                return
            move_idx = self._sim_red_move_idx
            if move_idx is not None:
                self._ejecutar_ataque_simulacion(
                    self.red_team[self.red_active_idx],
                    self.blue_team[self.blue_active_idx],
                    move_idx, False,
                    self._log_lines_temp,
                    self._sim_continuar
                )
            else:
                self._sim_continuar()

    def _sim_continuar(self):
        self._sim_index += 1
        self._procesar_accion_simulacion()

    def _ejecutar_ataque_simulacion(self, atacante, defensor, move_idx, es_azul, log_lines, callback):
        if atacante.fainted:
            callback()
            return
        
        move = atacante.movimientos[move_idx]
        
        if es_azul:
            log_lines.append(f"[AZUL] {atacante.nombre} usó {move['nombre']}!")
        else:
            log_lines.append(f"[ROJO] {atacante.nombre} usó {move['nombre']}!")
        
        self._log_lines(log_lines)
        log_lines.clear()
        
        if move["pp"] <= 0:
            self._log("¡Sin PP! El movimiento falló.", "effect")
            callback()
            return
        
        if move["nombre"] not in ["Vuelo", "Bote"]:
            move["pp"] -= 1
        
        if not rand(move["precision"]):
            self._log(f"¡{atacante.nombre} falló el ataque!", "effect")
            callback()
            return
        
        effect_msgs = []
        
        if move["poder"] > 0:
            if hasattr(defensor, 'is_protected') and defensor.is_protected:
                self._log(f"[DEFENSA] {defensor.nombre} se protegió del ataque de {atacante.nombre}!", "effect")
                defensor.is_protected = False
                self.root.after(500, callback)
                return
            
            damage, type_mult = calculate_damage(atacante, defensor, move)
            
            if rand(0.0625):
                damage = int(damage * 1.5)
                self._log("[CRITICO] Golpe crítico!", "crit")
            
            defensor.current_hp = max(0, defensor.current_hp - damage)
            murio = (defensor.current_hp <= 0)
            
            if defensor in self.blue_team:
                self._update_panel(self._blue_widgets, defensor, self.blue_team, self.blue_active_idx)
            else:
                self._update_panel(self._red_widgets, defensor, self.red_team, self.red_active_idx)
            
            if type_mult >= 2:
                self._log(f"¡Es muy efectivo! (x{type_mult})", "crit")
            elif type_mult == 0:
                self._log(f"¡No afecta a {defensor.nombre}!", "effect")
                defensor.current_hp = min(defensor.max_hp, defensor.current_hp + damage)
                murio = False
            elif type_mult < 1:
                self._log(f"No es muy efectivo... (x{type_mult})", "effect")
            
            self._log(f"[IMPACTO] {defensor.nombre} recibió {damage} de daño.", "effect")
            
            if move["nombre"] in ["Gigadrenado", "Puño Drenaje"]:
                drain = int(damage * 0.5)
                atacante.heal(drain)
                self._log(f"[CURACION] {atacante.nombre} absorbió {drain} HP!", "good")
            
            if move["nombre"] == "Pajaro Osado":
                recoil = int(damage / 3)
                atacante.apply_damage(recoil, True)
                self._log(f"[DAÑO] {atacante.nombre} recibió {recoil} de retroceso!", "effect")
            
            if murio:
                self._log(f"[DERROTA] {defensor.nombre} fue derrotado!", "effect")
                self._refresh_ui()
            
            apply_move_effects(atacante, defensor, move, effect_msgs, es_azul, self.blue_hazards, self.red_hazards)
            for msg in effect_msgs:
                self._log(msg, "effect")
            
            self.root.after(1200, callback)
        else:
            apply_move_effects(atacante, defensor, move, effect_msgs, es_azul, self.blue_hazards, self.red_hazards)
            for msg in effect_msgs:
                self._log(msg, "effect")
            self.root.after(500, callback)

    def _apply_end_turn_effects(self):
        bp = self.blue_team[self.blue_active_idx]
        rp = self.red_team[self.red_active_idx]
        for pokemon in [bp, rp]:
            if pokemon.fainted:
                continue
            if pokemon.status == "burn":
                damage = max(1, int(pokemon.max_hp / 16))
                pokemon.apply_damage(damage, True)
                self._log(f"[QUEMADURA] {pokemon.nombre} sufre daño por quemadura ({damage} HP).", "effect")
            elif pokemon.status == "poison":
                damage = max(1, int(pokemon.max_hp / 16))
                pokemon.apply_damage(damage, True)
                self._log(f"[VENENO] {pokemon.nombre} sufre daño por veneno ({damage} HP).", "effect")
            elif pokemon.status == "toxic":
                damage = max(1, int(pokemon.max_hp / 16 * pokemon.poison_counter))
                pokemon.poison_counter += 1
                pokemon.apply_damage(damage, True)
                self._log(f"[VENENO_GRAVE] {pokemon.nombre} sufre daño por veneno grave ({damage} HP).", "effect")
            elif pokemon.status == "infectado":
                damage = max(1, int(pokemon.max_hp / 8))
                pokemon.apply_damage(damage, True)
                self._log(f"[INFECCION] {pokemon.nombre} pierde {damage} HP por Drenadoras.", "effect")
            if pokemon.current_hp <= 0:
                pokemon.fainted = True
                self._log(f"[DERROTA] ¡{pokemon.nombre} fue derrotado por el estado!", "effect")
        
        if bp.wish_heal > 0 and not bp.fainted:
            bp.heal(bp.wish_heal)
            self._log(f"[CURACION] El Deseo se cumple! {bp.nombre} recupera {bp.wish_heal} HP.", "good")
            bp.wish_heal = 0
        if rp.wish_heal > 0 and not rp.fainted:
            rp.heal(rp.wish_heal)
            self._log(f"[CURACION] El Deseo se cumple! {rp.nombre} recupera {rp.wish_heal} HP.", "good")
            rp.wish_heal = 0
        
        self._refresh_ui()

    def _verify_defeated(self):
        for p in self.blue_team:
            if p.current_hp <= 0 and not p.fainted:
                p.fainted = True
        for p in self.red_team:
            if p.current_hp <= 0 and not p.fainted:
                p.fainted = True
        
        bp = self.blue_team[self.blue_active_idx]
        rp = self.red_team[self.red_active_idx]
        
        blue_alive = [i for i, p in enumerate(self.blue_team) if not p.fainted]
        red_alive = [i for i, p in enumerate(self.red_team) if not p.fainted]
        
        if not blue_alive:
            self._game_over(winner="red")
            return
        if not red_alive:
            self._game_over(winner="blue")
            return
        
        # Cambiar automáticamente si es necesario
        if bp.fainted and blue_alive:
            # Elegir el Pokémon con más HP
            best_idx = max(blue_alive, key=lambda i: self.blue_team[i].current_hp)
            self.blue_active_idx = best_idx
            new_pokemon = self.blue_team[best_idx]
            new_pokemon.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
            new_pokemon.protect_success = True
            new_pokemon.protect_fail_count = 0
            msgs = apply_hazards_on_switch(new_pokemon, self.red_hazards, True)
            for m in msgs:
                self._log(m, "effect")
            self._log(f"[CAMBIO] El equipo AZUL envió a {new_pokemon.nombre}!", "blue")
            self._refresh_ui()
        
        if rp.fainted and red_alive:
            best_idx = max(red_alive, key=lambda i: self.red_team[i].current_hp)
            self.red_active_idx = best_idx
            new_pokemon = self.red_team[best_idx]
            new_pokemon.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
            new_pokemon.protect_success = True
            new_pokemon.protect_fail_count = 0
            msgs = apply_hazards_on_switch(new_pokemon, self.blue_hazards, False)
            for m in msgs:
                self._log(m, "effect")
            self._log(f"[CAMBIO] El equipo ROJO envió a {new_pokemon.nombre}!", "red")
            self._refresh_ui()

    def _game_over(self, winner):
        if self._game_over_active:
            return
        self._game_over_active = True

        # Registrar estadisticas de IA
        registrar_resultado_simulation(winner, self.ai_level, self.ai2_level)
        
        self._refresh_ui()
        
        win = tk.Toplevel(self.root)
        win.title("¡Fin de la batalla!")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()
        win.transient(self.root)

        if winner == "blue":
            msg = "[VICTORIA] VICTORIA DEL EQUIPO AZUL!\nLa IA AZUL ha ganado la batalla."
            col = BLUE_C
        else:
            msg = "[VICTORIA] VICTORIA DEL EQUIPO ROJO!\nLa IA ROJA ha ganado la batalla."
            col = ACCENT

        tk.Label(win, text=msg, font=("Courier", 14, "bold"),
                 bg=BG, fg=col, justify="center").pack(pady=20, padx=30)
        
        frame_botones = tk.Frame(win, bg=BG)
        frame_botones.pack(pady=10)
        
        def restart_game():
            win.destroy()
            self._game_over_active = False
            self._restart()
        
        def exit_to_menu():
            win.destroy()
            self._game_over_active = False
            self.destroy()
            if self.on_exit_callback:
                self.root.after(100, self.on_exit_callback)
        
        tk.Button(frame_botones, text="JUGAR DE NUEVO",
                  font=("Courier", 10, "bold"), bg=BG3, fg=GOLD,
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                  command=restart_game).pack(side="left", padx=10)
        
        tk.Button(frame_botones, text="MENÚ PRINCIPAL",
                  font=("Courier", 10, "bold"), bg=BLUE_C, fg="#1a1a2e",
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                  command=exit_to_menu).pack(side="left", padx=10)

    def _restart(self):
        for widget in self.winfo_children():
            widget.destroy()
        
        self._game_over_active = False
        
        self.blue_team = []
        self.red_team = []
        self.blue_active_idx = 0
        self.red_active_idx = 0
        self.turn = 1
        self.blue_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        self.red_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        
        self._build_ui()
        self._start_new_game()

    def _exit_to_menu(self):
        self.destroy()
        if self.on_exit_callback:
            self.on_exit_callback()


def main():
    root = tk.Tk()
    app = PokemonSimulationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()