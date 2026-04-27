import tkinter as tk
from tkinter import ttk
import random
from datos.datos_pokemon import POKEMON_DB
from models.clase_batalla import BattlePokemon
from batalla.logica_batalla import resolve_turn, calculate_damage, get_priority
from batalla.peligros import apply_hazards_on_switch
from batalla.efectos import apply_move_effects
from utiles.funciones_auxiliares import rand, clamp
from ia.ia_levels import RandomAI, HeuristicAI

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


class PokemonGUI(tk.Frame):
    def __init__(self, parent, ai_level=1, battle_type=4, on_exit_callback=None):
        super().__init__(parent, bg=BG)
        self.parent = parent
        self.root = parent
        self.ai_level = ai_level
        self.battle_type = battle_type
        self.on_exit_callback = on_exit_callback
        self.root.title("PokeFisi - Batallas Pokémon")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.minsize(820, 620)

        self.player_team = []
        self.ai_team = []
        self.player_active_idx = 0
        self.ai_active_idx = 0
        self.turn = 1
        self.ia = None
        self.player_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        self.ai_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        self.buttons_locked = False
        self.pending_switch = False
        self.pending_switch_idx = None
        self.switch_source = None
        self.just_switched_by_move = False
        self.pokemon_data_list = []
        self.pending_move_idx = None
        self._auto_enfado_active = False
        self._auto_vuelo_active = False
        self._pending_vuelo = False
        self._game_over_active = False
        self._cola_acciones = []
        self._esperando_cambio = False
        self._procesando_derrotado = False
        self._pokemon_ia_pendiente = None
        self._ventana_cambio_abierta = False

        self.pack(fill="both", expand=True)
        self._build_ui()
        self.after(500, self._start_new_game)

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

        self.frame_player = self._make_pokemon_panel(mid, "🔵 JUGADOR", BLUE_C, 0)
        self.frame_ai     = self._make_pokemon_panel(mid, "🔴 RIVAL (IA)", ACCENT, 1)

        log_frame = tk.Frame(self, bg=BG2, bd=1, relief="flat")
        log_frame.pack(fill="x", padx=12, pady=(0, 6))
        tk.Label(log_frame, text="📋 LOG DE BATALLA", font=("Courier", 9, "bold"),
                 bg=BG2, fg=TEXT2).pack(anchor="w", padx=8, pady=(4,0))
        self.log_text = tk.Text(log_frame, height=7, bg=BG2, fg=TEXTCOL,
                                font=("Courier", 10), state="disabled",
                                relief="flat", wrap="word", bd=0,
                                selectbackground=BG3)
        self.log_text.pack(fill="x", padx=8, pady=(2, 6))
        self.log_text.tag_config("player", foreground=BLUE_C)
        self.log_text.tag_config("ai", foreground=ACCENT)
        self.log_text.tag_config("effect", foreground="#c084fc")
        self.log_text.tag_config("info", foreground=TEXT2)
        self.log_text.tag_config("crit", foreground=GOLD)
        self.log_text.tag_config("good", foreground=GREEN)

        act_outer = tk.Frame(self, bg=BG)
        act_outer.pack(fill="x", padx=12, pady=(0, 10))

        tabs = tk.Frame(act_outer, bg=BG)
        tabs.pack(fill="x", pady=(0,4))
        self.btn_tab_moves = tk.Button(tabs, text="⚔  ATAQUES",
                                        command=lambda: self._show_tab("moves"),
                                        font=("Courier", 9, "bold"), bg=BG3, fg=GOLD,
                                        relief="flat", bd=0, padx=14, pady=6,
                                        activebackground=ACCENT, cursor="hand2")
        self.btn_tab_switch = tk.Button(tabs, text="🔄  CAMBIAR",
                                        command=lambda: self._show_tab("switch"),
                                        font=("Courier", 9, "bold"), bg=BG2, fg=TEXT2,
                                        relief="flat", bd=0, padx=14, pady=6,
                                        activebackground=BG3, cursor="hand2")
        self.btn_tab_moves.pack(side="left", padx=(0,4))
        self.btn_tab_switch.pack(side="left")

        self.panel_moves = tk.Frame(act_outer, bg=BG)
        self.panel_switch = tk.Frame(act_outer, bg=BG)

        self.move_buttons = []
        for i in range(4):
            btn = tk.Button(self.panel_moves, text="", font=("Courier", 9),
                            bg=BG2, fg=TEXTCOL, relief="flat", bd=0,
                            padx=6, pady=8, anchor="w", justify="left",
                            activebackground=BG3, cursor="hand2",
                            command=lambda idx=i: self._on_move(idx))
            btn.grid(row=i//2, column=i%2, sticky="ew", padx=4, pady=3)
            self.move_buttons.append(btn)
        self.panel_moves.columnconfigure(0, weight=1)
        self.panel_moves.columnconfigure(1, weight=1)

        self.switch_buttons = []
        for i in range(4):
            btn = tk.Button(self.panel_switch, text="", font=("Courier", 9),
                            bg=BG2, fg=TEXTCOL, relief="flat", bd=0,
                            padx=6, pady=7, anchor="w", justify="left",
                            activebackground=BG3, cursor="hand2",
                            command=lambda idx=i: self._on_switch(idx))
            btn.grid(row=i//2, column=i%2, sticky="ew", padx=4, pady=3)
            self.switch_buttons.append(btn)
        self.panel_switch.columnconfigure(0, weight=1)
        self.panel_switch.columnconfigure(1, weight=1)

        self._show_tab("moves")

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
            self._player_widgets = widgets
        else:
            self._ai_widgets = widgets
        return frame

    def _show_tab(self, tab):
        if tab == "moves":
            self.panel_moves.pack(fill="x")
            self.panel_switch.pack_forget()
            self.btn_tab_moves.config(bg=BG3, fg=GOLD)
            self.btn_tab_switch.config(bg=BG2, fg=TEXT2)
        else:
            self.panel_switch.pack(fill="x")
            self.panel_moves.pack_forget()
            self.btn_tab_moves.config(bg=BG2, fg=TEXT2)
            self.btn_tab_switch.config(bg=BG3, fg=GOLD)

    def _seleccionar_movimientos(self):
        self.seleccion_movimientos = {}
        self.pokemon_actual = 0
        
        self.win_moves = tk.Toplevel(self.root)
        self.win_moves.title("Seleccionar Movimientos")
        self.win_moves.configure(bg=BG)
        self.win_moves.resizable(False, False)
        self.win_moves.grab_set()
        
        self.win_moves.update_idletasks()
        x = (self.win_moves.winfo_screenwidth() // 2) - 350
        y = (self.win_moves.winfo_screenheight() // 2) - 300
        self.win_moves.geometry(f"750x600+{x}+{y}")
        
        main = tk.Frame(self.win_moves, bg=BG)
        main.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.lbl_progreso = tk.Label(main, text="", font=("Courier", 14, "bold"),
                                      bg=BG, fg=GOLD)
        self.lbl_progreso.pack(pady=10)
        
        info_frame = tk.Frame(main, bg=BG2)
        info_frame.pack(fill="x", padx=10, pady=5)
        tk.Label(info_frame, text=f"⚔️ Combate {self.battle_type} vs {self.battle_type}", 
                 font=("Courier", 10, "bold"), bg=BG2, fg=GOLD).pack()
        
        frame_poke = tk.Frame(main, bg=BG2, bd=2, relief="solid",
                              highlightbackground=ACCENT, highlightthickness=2)
        frame_poke.pack(fill="x", padx=10, pady=10)
        
        self.lbl_nombre_poke = tk.Label(frame_poke, text="", font=("Courier", 16, "bold"),
                                        bg=BG2, fg=BLUE_C)
        self.lbl_nombre_poke.pack(pady=10)
        
        container = tk.Frame(main, bg=BG2)
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        canvas = tk.Canvas(container, bg=BG2, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.frame_moves = tk.Frame(canvas, bg=BG2)
        
        self.frame_moves.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.frame_moves, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.lbl_contador = tk.Label(main, text="Movimientos seleccionados: 0/4",
                                     font=("Courier", 12, "bold"), bg=BG, fg=GREEN)
        self.lbl_contador.pack(pady=5)
        
        frame_botones = tk.Frame(main, bg=BG)
        frame_botones.pack(pady=15, fill="x")
        
        self.btn_anterior = tk.Button(frame_botones, text="◀ ANTERIOR", font=("Courier", 11, "bold"),
                                      bg=BG3, fg=TEXT2, relief="flat", bd=0,
                                      padx=20, pady=10, cursor="hand2",
                                      command=self._anterior_pokemon)
        self.btn_anterior.pack(side="left", padx=10, expand=True)
        
        self.btn_aleatorio = tk.Button(frame_botones, text="🔄 ALEATORIO", font=("Courier", 11, "bold"),
                                       bg=BG3, fg=GOLD, relief="flat", bd=0,
                                       padx=20, pady=10, cursor="hand2",
                                       command=self._aleatorio_actual)
        self.btn_aleatorio.pack(side="left", padx=10, expand=True)
        
        self.btn_siguiente = tk.Button(frame_botones, text="SIGUIENTE ▶", font=("Courier", 11, "bold"),
                                       bg=GREEN, fg="#333", relief="flat", bd=0,
                                       padx=20, pady=10, cursor="hand2",
                                       command=self._siguiente_pokemon)
        self.btn_siguiente.pack(side="left", padx=10, expand=True)
        
        self._cargar_pokemon_seleccion(0)
    
    def _cargar_pokemon_seleccion(self, idx):
        self.pokemon_actual = idx
        pokemon = self.pokemon_data_list[idx]
        
        self.lbl_progreso.config(text=f"Pokémon {idx+1} de {len(self.pokemon_data_list)}")
        self.lbl_nombre_poke.config(text=f"✨ {pokemon['nombre']} ✨")
        
        for widget in self.frame_moves.winfo_children():
            widget.destroy()
        
        self.vars_movimientos = []
        
        for move_idx, move in enumerate(pokemon["movimientos"]):
            var = tk.BooleanVar()
            if idx in self.seleccion_movimientos and move_idx in self.seleccion_movimientos[idx]:
                var.set(True)
            self.vars_movimientos.append(var)
            
            frame = tk.Frame(self.frame_moves, bg=BG2, pady=5)
            frame.pack(fill="x", padx=10, pady=5)
            
            cb = tk.Checkbutton(frame, variable=var, bg=BG2, selectcolor=BG3,
                                command=self._actualizar_contador)
            cb.pack(side="left")
            
            cat_sym = "⚔" if move["categoria"] == "Fisico" else "🔮" if move["categoria"] == "Especial" else "✨"
            info = f"{cat_sym} {move['nombre']}  |  Tipo: {move['tipo']}  |  Poder: {move['poder'] or '—'}  |  PP: {move['ppMax']}"
            tk.Label(frame, text=info, font=("Courier", 10), bg=BG2, fg=TEXTCOL, anchor="w").pack(side="left", padx=5)
            
            effect = move['efecto'][:50] + ("..." if len(move['efecto']) > 50 else "")
            tk.Label(frame, text=f"Efecto: {effect}", font=("Courier", 8), bg=BG2, fg=TEXT2).pack(side="left", padx=10)
        
        self._actualizar_contador()
        
        if idx == 0:
            self.btn_anterior.config(state="disabled", bg=BG3, fg="#555")
        else:
            self.btn_anterior.config(state="normal", bg=BG3, fg=TEXT2)
        
        if idx == len(self.pokemon_data_list) - 1:
            self.btn_siguiente.config(text="✅ INICIAR", bg=GREEN, fg="#333")
        else:
            self.btn_siguiente.config(text="SIGUIENTE ▶", bg=GREEN, fg="#333")
    
    def _actualizar_contador(self):
        seleccionados = [i for i, v in enumerate(self.vars_movimientos) if v.get()]
        count = len(seleccionados)
        self.lbl_contador.config(text=f"Movimientos seleccionados: {count}/4")
        self.lbl_contador.config(fg=GREEN if count == 4 else GOLD)
        
        if count > 4:
            for i, var in enumerate(self.vars_movimientos):
                if var.get() and i not in seleccionados[:4]:
                    var.set(False)
    
    def _aleatorio_actual(self):
        for var in self.vars_movimientos:
            var.set(False)
        indices = list(range(len(self.vars_movimientos)))
        random.shuffle(indices)
        for i in indices[:4]:
            self.vars_movimientos[i].set(True)
        self._actualizar_contador()
    
    def _anterior_pokemon(self):
        if self.pokemon_actual > 0:
            self.seleccion_movimientos[self.pokemon_actual] = [i for i, v in enumerate(self.vars_movimientos) if v.get()]
            self._cargar_pokemon_seleccion(self.pokemon_actual - 1)
    
    def _siguiente_pokemon(self):
        seleccionados = [i for i, v in enumerate(self.vars_movimientos) if v.get()]
        if len(seleccionados) != 4:
            error = tk.Label(self.win_moves, text="❌ ¡Debes seleccionar exactamente 4 movimientos!",
                             font=("Courier", 10, "bold"), bg=BG, fg=RED_COL)
            error.pack(pady=5)
            self.win_moves.after(2000, error.destroy)
            return
        
        self.seleccion_movimientos[self.pokemon_actual] = seleccionados
        
        if self.pokemon_actual + 1 < len(self.pokemon_data_list):
            self._cargar_pokemon_seleccion(self.pokemon_actual + 1)
        else:
            self.win_moves.destroy()
            self._crear_equipo_jugador()
    
    def _crear_equipo_jugador(self):
        self.player_team = []
        for idx, data in enumerate(self.pokemon_data_list):
            indices_seleccionados = self.seleccion_movimientos.get(idx, [])
            movimientos = []
            for move_idx in indices_seleccionados:
                move = data["movimientos"][move_idx].copy()
                move["pp"] = move["ppMax"]
                move["pp_max"] = move["ppMax"]
                movimientos.append(move)
            pokemon = BattlePokemon(data, preassigned_moves=movimientos, level=55)
            pokemon.selected_moves = movimientos
            self.player_team.append(pokemon)
        
        self._iniciar_batalla()
        
    def _start_new_game(self):
        pool = POKEMON_DB[:]
        random.shuffle(pool)
        
        num_pokemon = self.battle_type
        self.pokemon_data_list = [pool[i] for i in range(num_pokemon)]
        
        # Generar equipo de la IA (roja)
        self.ai_team = []
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
            self.ai_team.append(BattlePokemon(data, preassigned_moves=movimientos, level=55))

        # Modo PVE: permitir selección manual de movimientos
        self._seleccionar_movimientos()
    
    def _iniciar_batalla(self):
        self.player_active_idx = 0
        self.ai_active_idx = 0
        self.turn = 1
        self.player_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        self.ai_hazards = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}
        
        # Modo PVE: inicializar IA rival
        if self.ai_level == 1:
            self.ia = RandomAI(self.ai_team, self.player_team[0])
        else:
            self.ia = HeuristicAI(self.ai_team, self.player_team[0])

        self.buttons_locked = False
        self.pending_switch = False
        self.pending_switch_idx = None
        self.switch_source = None
        self.just_switched_by_move = False

        lines = ["🎲 ¡Equipos generados aleatoriamente!",
                f"🔵 Tu equipo: {', '.join(p.nombre for p in self.player_team)}",
                f"🔴 Rival (IA): {', '.join(p.nombre for p in self.ai_team)}",
                "── ¡Que comience la batalla! ──"]
        for l in lines:
            self._log(l, "info")

        self._refresh_ui()

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

    def _update_move_buttons(self, player_poke, ai_poke):
        for i, btn in enumerate(self.move_buttons):
            if i >= len(player_poke.movimientos):
                btn.config(text="—", state="disabled")
                continue
            m = player_poke.movimientos[i]
            cat_sym = "⚔" if m["categoria"] == "Fisico" else "🔮" if m["categoria"] == "Especial" else "✨"
            pp_warn = " ⚠" if m["pp"] <= max(1, m["pp_max"] // 4) else ""
            disabled = m["pp"] <= 0 or self.buttons_locked or self.pending_switch
            btn.config(
                text=f"{cat_sym} {m['nombre']}\n"
                     f"Tipo: {m['tipo']}  PWR:{m['poder'] or '—'}  PP:{m['pp']}/{m['pp_max']}{pp_warn}\n"
                     f"Efecto: {m['efecto'][:38]}",
                state="disabled" if disabled else "normal",
                bg=BG2 if not disabled else "#111",
                fg=TEXTCOL if not disabled else "#555",
                disabledforeground="#555",
            )

    def _update_switch_buttons(self):
        if not self.player_team:
            return
        team = self.player_team
        active = self.player_active_idx
        num_pokemon = len(team)
        
        for i, btn in enumerate(self.switch_buttons):
            if i >= num_pokemon:
                btn.config(text="—", state="disabled")
                continue
            p = team[i]
            is_active = (i == active)
            disabled = p.fainted or is_active or self.buttons_locked or self.pending_switch
            star = "⭐ " if is_active else "   "
            status_txt = f" [{STATUS_LABELS.get(p.status,'')}]" if p.status else ""
            hp_pct = int(p.current_hp / p.max_hp * 100) if not p.fainted else 0
            bar_len = 12
            filled = int(bar_len * hp_pct / 100)
            bar_txt = "█" * filled + "░" * (bar_len - filled)
            fainted_txt = "💀 DERROTADO" if p.fainted else f"HP:{p.current_hp}/{p.max_hp} [{bar_txt}] {hp_pct}%{status_txt}"
            btn.config(
                text=f"{star}{p.nombre} (N{p.level})\n{fainted_txt}",
                state="disabled" if disabled else "normal",
                bg=BG2 if not disabled else "#111",
                fg=TEXTCOL if not disabled else "#555",
                disabledforeground="#555",
            )

    def _refresh_ui(self):
        if not self.player_team or not self.ai_team:
            return
        if self.player_active_idx >= len(self.player_team):
            self.player_active_idx = 0
        if self.ai_active_idx >= len(self.ai_team):
            self.ai_active_idx = 0
            
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]
        self.lbl_turn.config(text=f"TURNO {self.turn}")
        self._update_panel(self._player_widgets, pp, self.player_team, self.player_active_idx)
        self._update_panel(self._ai_widgets, ap, self.ai_team, self.ai_active_idx)
        
        if pp.outrage_locked:
            for btn in self.move_buttons:
                btn.config(state="disabled", text="😤 ENFURECIDO\nUsando Enfado automáticamente...")
            for btn in self.switch_buttons:
                btn.config(state="disabled")
        elif hasattr(pp, 'flying_active') and pp.flying_active:
            for btn in self.move_buttons:
                btn.config(state="disabled", text="🕊️ VOLANDO\nAtacará automáticamente...")
            for btn in self.switch_buttons:
                btn.config(state="disabled")
        else:
            self._update_move_buttons(pp, ap)
            self._update_switch_buttons()
        
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
                self._verificar_derrotados_y_preguntar()
                return
            line = lines[idx]
            tag = "info"
            if line.startswith("🔵"):
                tag = "player"
            elif line.startswith("🔴"):
                tag = "ai"
            elif any(x in line for x in ["💥","📈","📉","🔥","⚡","❄️","☠️","💊","💚","🎭","🛡"]):
                tag = "effect"
            elif "¡Es muy efectivo" in line:
                tag = "crit"
            elif "💀" in line:
                tag = "ai" if "RIVAL" in line.upper() or any(p.nombre in line for p in self.ai_team) else "player"
            self._log(line, tag)
            
            pp = self.player_team[self.player_active_idx]
            ap = self.ai_team[self.ai_active_idx]
            self._update_panel(self._player_widgets, pp, self.player_team, self.player_active_idx)
            self._update_panel(self._ai_widgets, ap, self.ai_team, self.ai_active_idx)
            
            self.root.after(800, lambda: show_next(idx + 1))

        self.buttons_locked = True
        self._refresh_ui()
        show_next(0)

    def _show_switch_dialog_before_attack(self, pokemon, move_idx, move_name):
        win = tk.Toplevel(self.root)
        win.title("¡Cambio de Pokémon!")
        win.configure(bg=BG)
        win.grab_set()
        win.transient(self.root)

        tk.Label(win, text=f"⚡ ¡{pokemon.nombre} usará {move_name}!\n¿A qué Pokémon quieres cambiar después de atacar?",
                 font=("Courier", 11, "bold"), bg=BG, fg=ACCENT,
                 justify="center").pack(pady=12, padx=20)
        
        for i, p in enumerate(self.player_team):
            if p.fainted or i == self.player_active_idx:
                continue
            hp_pct = int(p.current_hp / p.max_hp * 100)
            bar_len = 14
            filled = int(bar_len * hp_pct / 100)
            bar_txt = "█" * filled + "░" * (bar_len - filled)
            status_txt = f" [{STATUS_LABELS.get(p.status,'')}]" if p.status else ""
            lbl = (f"{p.nombre}  ({p.tipo1}"
                   + (f"/{p.tipo2}" if p.tipo2 else "")
                   + f")\nHP: {p.current_hp}/{p.max_hp} [{bar_txt}] {hp_pct}%{status_txt}")
            btn = tk.Button(win, text=lbl, font=("Courier", 10),
                            bg=BG2, fg=TEXTCOL, relief="flat", bd=0,
                            padx=10, pady=6, anchor="w", justify="left",
                            activebackground=BG3, cursor="hand2",
                            command=lambda idx=i, w=win: self._execute_switch_with_move(idx, move_idx, move_name, w))
            btn.pack(fill="x", padx=16, pady=3)
        
        tk.Button(win, text="✖  Cancelar (usar solo el ataque)",
                  font=("Courier", 9), bg=BG3, fg=TEXT2,
                  relief="flat", bd=0, padx=10, pady=5, cursor="hand2",
                  command=lambda: self._cancel_move_switch(win, move_idx)).pack(pady=10)

    def _execute_switch_with_move(self, new_idx, move_idx, move_name, win):
        win.destroy()
        self.pending_switch_idx = new_idx
        self.pending_switch = True
        self.switch_source = self.player_team[self.player_active_idx]
        self.pending_move_idx = move_idx
        player_action = ("move", move_idx)
        self._execute_turn(player_action)

    def _cancel_move_switch(self, win, move_idx):
        win.destroy()
        self.pending_switch = False
        self.pending_switch_idx = None
        self.switch_source = None
        player_action = ("move", move_idx)
        self._execute_turn(player_action)

    def _on_move(self, move_idx):
        if hasattr(self, '_auto_enfado_active') and self._auto_enfado_active:
            return
        if hasattr(self, '_auto_vuelo_active') and self._auto_vuelo_active:
            return
        
        if self.buttons_locked or self.pending_switch:
            return
        pp = self.player_team[self.player_active_idx]
        move = pp.movimientos[move_idx]
        
        if hasattr(pp, 'flying_active') and pp.flying_active:
            self._log(f"🕊️ ¡{pp.nombre} está volando! Debe completar el movimiento.", "effect")
            return
        
        if pp.outrage_locked:
            self._log(f"😤 ¡{pp.nombre} está enfurecido! Usará Enfado automáticamente.", "effect")
            return
        
        if move["pp"] <= 0:
            self._log(f"⚠️ ¡{move['nombre']} no tiene PP!", "effect")
            return

        if move["nombre"] in ["Ida y Vuelta", "Voltio Cambio"]:
            available = [i for i, p in enumerate(self.player_team) 
                         if not p.fainted and i != self.player_active_idx]
            if available:
                self.pending_move_idx = move_idx
                self.pending_switch = True
                self.switch_source = pp
                self._show_switch_dialog_before_attack(pp, move_idx, move["nombre"])
            else:
                player_action = ("move", move_idx)
                self._execute_turn(player_action)
        else:
            player_action = ("move", move_idx)
            self._execute_turn(player_action)

    def _on_switch(self, target_idx):
        if self.buttons_locked or self.pending_switch:
            return
        if target_idx == self.player_active_idx:
            return
        if self.player_team[target_idx].fainted:
            return
        
        pp = self.player_team[self.player_active_idx]
        
        if pp.outrage_locked:
            self._log(f"😤 ¡{pp.nombre} está enfurecido! No puede cambiar hasta que termine el Enfado.", "effect")
            return
        
        if hasattr(pp, 'flying_active') and pp.flying_active:
            self._log(f"🕊️ ¡{pp.nombre} está volando! No puede cambiar hasta que termine el movimiento.", "effect")
            return
        
        player_action = ("switch", target_idx)
        self._execute_turn(player_action)
        self._show_tab("moves")

    def _auto_enfado_turn(self):
        if not self.player_team or not self.ai_team:
            return
        
        pp = self.player_team[self.player_active_idx]
        
        if pp.outrage_locked and not pp.fainted:
            enfado_idx = None
            for i, m in enumerate(pp.movimientos):
                if m["nombre"] == "Enfado":
                    enfado_idx = i
                    break
            
            if enfado_idx is not None and pp.movimientos[enfado_idx]["pp"] > 0:
                self._log(f"😤 ¡{pp.nombre} sigue enfurecido! Usando Enfado automáticamente...", "effect")
                self._auto_enfado_active = True
                player_action = ("move", enfado_idx)
                self._execute_turn(player_action)
                self._auto_enfado_active = False
            else:
                self.buttons_locked = False
                self._refresh_ui()
        else:
            self.buttons_locked = False
            self._refresh_ui()
            if not pp.fainted:
                self._log(f"😤 ¡El enfado de {pp.nombre} ha terminado!", "effect")

    def _auto_vuelo_turn(self):
        if not self.player_team or not self.ai_team:
            return
        pp = self.player_team[self.player_active_idx]
        
        if hasattr(pp, 'flying_active') and pp.flying_active and pp.flying_turns == 1:
            self._log(f"🕊️ ¡{pp.nombre} continúa su vuelo! Atacará automáticamente...", "effect")
            self._auto_vuelo_active = True
            player_action = ("move", None)  
            self._execute_turn(player_action)
            self._auto_vuelo_active = False
            self._pending_vuelo = False
            
            if hasattr(pp, 'flying_active'):
                pp.flying_turns = 0
                pp.flying_active = False
                pp.flying_move = None

    def _execute_turn(self, player_action):
        self.ia.active_idx = self.ai_active_idx
        ai_action = self.ia.get_action()

        log_lines = []

        player_switch = False
        player_move_idx = None
        player_force_idx = None
        ai_switch = False
        ai_move_idx = None
        self._pokemon_derrotado_en_turno = None
        
        is_auto_enfado = False
        if hasattr(self, '_auto_enfado_active') and self._auto_enfado_active:
            is_auto_enfado = True
        is_auto_vuelo = False
        if hasattr(self, '_auto_vuelo_active') and self._auto_vuelo_active:
            is_auto_vuelo = True
        
        if not (is_auto_enfado or is_auto_vuelo) and self.buttons_locked:
            return
        
        pp_check = self.player_team[self.player_active_idx]
        if pp_check.outrage_locked and not is_auto_enfado:
            for i, m in enumerate(pp_check.movimientos):
                if m["nombre"] == "Enfado":
                    player_move_idx = i
                    break
            if player_move_idx is not None:
                player_action = ("move", player_move_idx)
                log_lines.append(f"😤 ¡{pp_check.nombre} está enfurecido! Usará Enfado automáticamente.")
        
        if player_action[0] == "switch":
            player_switch = True
            nuevo_idx = player_action[1]
            
            pokemon_entrante = self.player_team[nuevo_idx]
            self.player_active_idx = nuevo_idx
            pokemon_entrante.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
            pokemon_entrante.protect_success = True
            pokemon_entrante.protect_fail_count = 0
            
            log_lines.append(f"🔄 Cambiaste a {pokemon_entrante.nombre}")
            msgs_hazard = apply_hazards_on_switch(pokemon_entrante, self.player_hazards, True)
            log_lines += msgs_hazard
            
            if pokemon_entrante.fainted:
                log_lines.append("💀 ¡El Pokémon fue derrotado por las trampas!")
                self._log_lines(log_lines)
                self._refresh_ui()
                return
            
            if ai_action[0] == "move":
                ai_move_idx = ai_action[1]
                if ai_move_idx is not None:
                    self._ejecutar_ataque_con_animacion_y_cambio(
                        self.ai_team[self.ai_active_idx],
                        pokemon_entrante,
                        ai_move_idx,
                        False,
                        log_lines,
                        lambda: self._finalizar_turno(log_lines)
                    )
                    return
            else:
                self._log_lines(log_lines)
                self._finalizar_turno(log_lines)
                return
            
        elif ai_action[0] == "switch":
            ai_switch = True
            nuevo_idx = ai_action[1]
            
            pokemon_entrante = self.ai_team[nuevo_idx]
            self.ai_active_idx = nuevo_idx
            self.ia.active_idx = nuevo_idx
            pokemon_entrante.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
            pokemon_entrante.protect_success = True
            pokemon_entrante.protect_fail_count = 0
            
            msgs = apply_hazards_on_switch(pokemon_entrante, self.ai_hazards, False)
            log_lines += msgs
            log_lines.append(f"🔄 La IA cambió a {pokemon_entrante.nombre}")
            
            if pokemon_entrante.fainted:
                log_lines.append("💀 ¡El Pokémon fue derrotado por las trampas!")
                self._log_lines(log_lines)
                self._refresh_ui()
                return
            
            if player_action[0] == "move":
                player_move_idx = player_action[1] if player_action[1] is not None else None
                if player_move_idx is not None:
                    self._ejecutar_ataque_con_animacion_y_cambio(
                        self.player_team[self.player_active_idx],
                        pokemon_entrante,
                        player_move_idx,
                        True,
                        log_lines,
                        lambda: self._finalizar_turno(log_lines)
                    )
                    return
            
            self._log_lines(log_lines)
            self._finalizar_turno(log_lines)
            return

        if player_action[0] == "move":
            if player_action[1] is not None:
                player_move_idx = player_action[1]
            else:
                player_move_idx = None
            if self.pending_switch_idx is not None:
                player_force_idx = self.pending_switch_idx
        else:
            player_move_idx = player_action[1]
            player_force_idx = player_action[2] if len(player_action) > 2 else None

        if ai_action[0] == "move":
            ai_move_idx = ai_action[1]
        else:
            ai_move_idx = ai_action[1] if len(ai_action) > 1 else None

        if not player_switch and not ai_switch:
            player_pokemon = self.player_team[self.player_active_idx]
            ai_pokemon = self.ai_team[self.ai_active_idx]
            
            player_speed = player_pokemon.get_effective_stat("spe")
            ai_speed = ai_pokemon.get_effective_stat("spe")
            
            player_priority = get_priority(player_move_idx, player_pokemon) if player_move_idx is not None else 0
            ai_priority = get_priority(ai_move_idx, ai_pokemon) if ai_move_idx is not None else 0
            
            if player_priority > ai_priority:
                orden = ["player", "ai"]
            elif ai_priority > player_priority:
                orden = ["ai", "player"]
            else:
                orden = ["player", "ai"] if player_speed >= ai_speed else ["ai", "player"]
            
            self._cola_acciones = []
            self._player_move_idx = player_move_idx
            self._ai_move_idx = ai_move_idx
            self._player_force_idx = player_force_idx
            self._log_lines_temp = log_lines.copy()
            
            self._procesar_accion_siguiente(orden, 0)
            
            pp = self.player_team[self.player_active_idx]
            if not is_auto_vuelo and hasattr(pp, 'flying_active') and pp.flying_active and pp.flying_turns == 1:
                if not self._pending_vuelo:
                    self._pending_vuelo = True
                    self.root.after(200, self._auto_vuelo_turn)

    def _ejecutar_ataque_con_animacion_y_cambio(self, atacante, defensor, move_idx, es_jugador, log_lines, callback):
        if atacante.fainted:
            callback()
            return
        
        move = atacante.movimientos[move_idx]
        
        if es_jugador:
            log_lines.append(f"🔵 {atacante.nombre} usó {move['nombre']}!")
        else:
            log_lines.append(f"🔴 {atacante.nombre} usó {move['nombre']}!")
        
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
        
        if move["poder"] > 0:
            if hasattr(defensor, 'is_protected') and defensor.is_protected:
                self._log(f"🛡️ ¡{defensor.nombre} se protegió del ataque de {atacante.nombre}!", "effect")
                defensor.is_protected = False
                self.root.after(1200, callback)
                return
            
            damage, type_mult = calculate_damage(atacante, defensor, move)
            
            if rand(0.0625):
                damage = int(damage * 1.5)
                self._log("💥 ¡Golpe crítico!", "crit")
            
            defensor.current_hp = max(0, defensor.current_hp - damage)
            if defensor.current_hp <= 0:
                defensor.fainted = True
            
            if defensor in self.player_team:
                self._update_panel(self._player_widgets, defensor, self.player_team, self.player_active_idx)
            else:
                self._update_panel(self._ai_widgets, defensor, self.ai_team, self.ai_active_idx)
            
            if type_mult >= 2:
                self._log(f"¡Es muy efectivo! (x{type_mult})", "crit")
            elif type_mult == 0:
                self._log(f"¡No afecta a {defensor.nombre}!", "effect")
                defensor.current_hp = min(defensor.max_hp, defensor.current_hp + damage)
            elif type_mult < 1:
                self._log(f"No es muy efectivo... (x{type_mult})", "effect")
            
            self._log(f"💢 {defensor.nombre} recibió {damage} de daño.", "effect")
            
            if defensor.current_hp <= 0:
                self._log(f"💀 ¡{defensor.nombre} fue derrotado!", "effect")
                self._refresh_ui()
                self._pokemon_derrotado_en_turno = "ai" if defensor in self.ai_team else "player"
            
            apply_move_effects(atacante, defensor, move, [], es_jugador, self.player_hazards, self.ai_hazards)
        
        self.root.after(1200, callback)

    def _procesar_accion_siguiente(self, orden, index):
        if index >= len(orden):
            self.turn += 1
            self._log_lines(self._log_lines_temp)
            self._aplicar_efectos_fin_turno()
            self._refresh_ui()
            return
        
        quien = orden[index]
        
        if quien == "player":
            pokemon = self.player_team[self.player_active_idx]
            if pokemon.fainted:
                self._procesar_accion_siguiente(orden, index + 1)
                return
            move_idx = self._player_move_idx
            if move_idx is not None:
                self._ejecutar_ataque_secuencial(
                    self.player_team[self.player_active_idx],
                    self.ai_team[self.ai_active_idx],
                    move_idx,
                    self._player_force_idx,
                    True,
                    self._log_lines_temp,
                    lambda: self._procesar_accion_siguiente(orden, index + 1)
                )
            else:
                self._procesar_accion_siguiente(orden, index + 1)
        else:
            pokemon = self.ai_team[self.ai_active_idx]
            if pokemon.fainted:
                self._procesar_accion_siguiente(orden, index + 1)
                return
            move_idx = self._ai_move_idx
            if move_idx is not None:
                self._ejecutar_ataque_secuencial(
                    self.ai_team[self.ai_active_idx],
                    self.player_team[self.player_active_idx],
                    move_idx,
                    None,
                    False,
                    self._log_lines_temp,
                    lambda: self._procesar_accion_siguiente(orden, index + 1)
                )
            else:
                self._procesar_accion_siguiente(orden, index + 1)

    def _aplicar_efectos_fin_turno(self):
        if not self.player_team or not self.ai_team:
            return
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]
        for pokemon in [pp, ap]:
            if pokemon.fainted:
                continue
            if pokemon.status == "burn":
                damage = max(1, int(pokemon.max_hp / 16))
                pokemon.apply_damage(damage, True)
                self._log(f"🔥 {pokemon.nombre} sufre daño por quemadura ({damage} HP).", "effect")
                if hasattr(pokemon, 'burn_turns') and pokemon.burn_turns > 0:
                    pokemon.burn_turns -= 1
                    if pokemon.burn_turns <= 0:
                        pokemon.status = None
                        self._log(f"🔥 ¡La quemadura de {pokemon.nombre} terminó!", "effect")
            elif pokemon.status == "poison":
                damage = max(1, int(pokemon.max_hp / 16))
                pokemon.apply_damage(damage, True)
                self._log(f"☠️ {pokemon.nombre} sufre daño por veneno ({damage} HP).", "effect")
            elif pokemon.status == "toxic":
                damage = max(1, int(pokemon.max_hp / 16 * pokemon.poison_counter))
                pokemon.poison_counter += 1
                pokemon.apply_damage(damage, True)
                self._log(f"☠️ {pokemon.nombre} sufre daño por veneno grave ({damage} HP).", "effect")
            elif pokemon.status == "infectado":
                damage = max(1, int(pokemon.max_hp / 8))
                pokemon.apply_damage(damage, True)
                if hasattr(pokemon, 'leech_seed_from') and pokemon.leech_seed_from and not pokemon.leech_seed_from.fainted:
                    pokemon.leech_seed_from.heal(damage)
                    self._log(f"🌱 {pokemon.nombre} pierde {damage} HP por Drenadoras. {pokemon.leech_seed_from.nombre} recupera {damage} HP.", "effect")
                else:
                    self._log(f"🌱 {pokemon.nombre} pierde {damage} HP por Drenadoras.", "effect")
            if pokemon.current_hp <= 0 and not pokemon.fainted:
                pokemon.fainted = True
                self._log(f"💀 ¡{pokemon.nombre} fue derrotado por el estado!", "effect")
        if pp.wish_heal > 0 and not pp.fainted:
            pp.heal(pp.wish_heal)
            self._log(f"✨ ¡El Deseo se cumple! {pp.nombre} recupera {pp.wish_heal} HP.", "good")
            pp.wish_heal = 0
        if ap.wish_heal > 0 and not ap.fainted:
            ap.heal(ap.wish_heal)
            self._log(f"✨ ¡El Deseo se cumple! {ap.nombre} recupera {ap.wish_heal} HP.", "good")
            ap.wish_heal = 0
        
        if hasattr(pp, 'is_protected'):
            pp.is_protected = False
        if hasattr(ap, 'is_protected'):
            ap.is_protected = False
        
        self._refresh_ui()

    def _ejecutar_ataque_secuencial(self, atacante, defensor, move_idx, force_idx, es_jugador, log_lines, callback):
        if atacante.fainted:
            self._log(f"⚠️ {atacante.nombre} está debilitado y no puede atacar!", "effect")
            callback()
            return
        
        move = atacante.movimientos[move_idx]
        
        if es_jugador:
            self._log(f"🔵 {atacante.nombre} usó {move['nombre']}!", "player")
        else:
            self._log(f"🔴 {atacante.nombre} usó {move['nombre']}!", "ai")
        
        if move["pp"] <= 0:
            self._log("¡Sin PP! El movimiento falló.", "effect")
            self.root.after(500, callback)
            return
        
        if move["nombre"] not in ["Vuelo", "Bote"]:
            move["pp"] -= 1
        
        if not rand(move["precision"]):
            self._log(f"¡{atacante.nombre} falló el ataque!", "effect")
            self.root.after(500, callback)
            return
        
        effect_msgs = []

        if move["poder"] > 0:
            if hasattr(defensor, 'is_protected') and defensor.is_protected:
                self._log(f"🛡️ ¡{defensor.nombre} se protegió del ataque de {atacante.nombre}!", "effect")
                defensor.is_protected = False
                self.root.after(500, callback)
                return
            
            damage, type_mult = calculate_damage(atacante, defensor, move)
            
            if rand(0.0625):
                damage = int(damage * 1.5)
                self._log("💥 ¡Golpe crítico!", "crit")
            
            defensor.current_hp = max(0, defensor.current_hp - damage)
            if defensor.current_hp <= 0:
                defensor.fainted = True
            
            if defensor in self.player_team:
                self._update_panel(self._player_widgets, defensor, self.player_team, self.player_active_idx)
            else:
                self._update_panel(self._ai_widgets, defensor, self.ai_team, self.ai_active_idx)
            
            if type_mult >= 2:
                self._log(f"¡Es muy efectivo! (x{type_mult})", "crit")
            elif type_mult == 0:
                self._log(f"¡No afecta a {defensor.nombre}!", "effect")
                defensor.current_hp = min(defensor.max_hp, defensor.current_hp + damage)
                defensor.fainted = False
            elif type_mult < 1:
                self._log(f"No es muy efectivo... (x{type_mult})", "effect")
            
            self._log(f"💢 {defensor.nombre} recibió {damage} de daño.", "effect")

            if move["nombre"] in ["Gigadrenado", "Puño Drenaje"]:
                drain = int(damage * 0.5)
                atacante.heal(drain)
                self._log(f"💚 {atacante.nombre} absorbió {drain} HP!", "good")

            if move["nombre"] == "Pajaro Osado":
                recoil = int(damage / 3)
                atacante.apply_damage(recoil, True)
                self._log(f"⚠️ {atacante.nombre} recibió {recoil} de retroceso!", "effect")
            
            if defensor.current_hp <= 0:
                self._log(f"💀 ¡{defensor.nombre} fue derrotado!", "effect")
                self._refresh_ui()
                if defensor in self.ai_team:
                    self._pokemon_derrotado_en_turno = "ai"
                else:
                    self._pokemon_derrotado_en_turno = "player"
            
            apply_move_effects(atacante, defensor, move, effect_msgs, es_jugador, self.player_hazards, self.ai_hazards)
            for msg in effect_msgs:
                self._log(msg, "effect")
            
            if move["nombre"] == "Enfado" and hasattr(atacante, 'outrage_active') and atacante.outrage_active:
                atacante.outrage_turns -= 1
                if atacante.outrage_turns <= 0:
                    atacante.outrage_active = False
                    atacante.outrage_locked = False
                    atacante.confused = True
                    atacante.confused_turns = random.randint(2, 5)
                    self._log(f"😵 ¡El Enfado de {atacante.nombre} terminó y ahora está confundido!", "effect")
                else:
                    self._log(f"😤 ¡{atacante.nombre} sigue enfurecido! (Turnos restantes: {atacante.outrage_turns})", "effect")
            
            if move["nombre"] in ["Ida y Vuelta", "Voltio Cambio"] and not atacante.fainted:
                if force_idx is not None:
                    old_nombre = atacante.nombre
                    self.player_active_idx = force_idx
                    new_pokemon = self.player_team[self.player_active_idx]
                    new_pokemon.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
                    new_pokemon.protect_success = True
                    new_pokemon.protect_fail_count = 0
                    hazard_msgs = apply_hazards_on_switch(new_pokemon, self.player_hazards, True)
                    self._log(f"🔄 ¡{old_nombre} regresó! ¡{new_pokemon.nombre} entra al campo!", "effect")
                    for hm in hazard_msgs:
                        self._log(hm, "effect")
                    self.pending_switch_idx = None
                    self.pending_switch = False
                    self.switch_source = None
                    self.pending_move_idx = None
                    self._refresh_ui()
            
            self.root.after(1200, callback)
        else:
            apply_move_effects(atacante, defensor, move, effect_msgs, es_jugador, self.player_hazards, self.ai_hazards)
            for msg in effect_msgs:
                self._log(msg, "effect")
            self._update_panel(self._player_widgets, self.player_team[self.player_active_idx], self.player_team, self.player_active_idx)
            self._update_panel(self._ai_widgets, self.ai_team[self.ai_active_idx], self.ai_team, self.ai_active_idx)
            self.root.after(500, callback)

    def _finalizar_turno(self, log_lines):
        self.turn += 1
        self._log_lines(log_lines)
        self._aplicar_efectos_fin_turno()
        self._refresh_ui()
        self._verificar_derrotados_y_preguntar()

    def _verificar_derrotados_y_preguntar(self):
        if self._procesando_derrotado:
            return
        self._procesando_derrotado = True
        
        for p in self.player_team:
            if p.current_hp <= 0 and not p.fainted:
                p.fainted = True
        for p in self.ai_team:
            if p.current_hp <= 0 and not p.fainted:
                p.fainted = True
        
        pp = self.player_team[self.player_active_idx]
        ap = self.ai_team[self.ai_active_idx]

        player_alive = [i for i, p in enumerate(self.player_team) if not p.fainted]
        ai_alive = [i for i, p in enumerate(self.ai_team) if not p.fainted]

        if not player_alive:
            self._procesando_derrotado = False
            self._game_over(winner="ai")
            return
        if not ai_alive:
            self._procesando_derrotado = False
            self._game_over(winner="player")
            return

        # Modo PVE
        if pp.fainted and player_alive:
            self._procesando_derrotado = False
            if not self._ventana_cambio_abierta:
                self._force_switch_dialog()
            return

        if ap.fainted and ai_alive:
            nuevo_idx = random.choice(ai_alive)
            nuevo_pokemon = self.ai_team[nuevo_idx]
            self._pokemon_ia_pendiente = (nuevo_idx, nuevo_pokemon)
            
            if not pp.fainted and not pp.outrage_locked and not (hasattr(pp, 'flying_active') and pp.flying_active):
                if not self._ventana_cambio_abierta:
                    self._procesando_derrotado = False
                    self._mostrar_pregunta_cambio(nuevo_pokemon, nuevo_idx)
                return
            else:
                self.ai_active_idx = nuevo_idx
                new_ap = self.ai_team[nuevo_idx]
                new_ap.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
                new_ap.protect_success = True
                new_ap.protect_fail_count = 0
                msgs = apply_hazards_on_switch(new_ap, self.ai_hazards, False)
                for m in msgs:
                    self._log(m, "effect")
                self._log(f"🔄 La IA envió a {new_ap.nombre}!", "ai")
                self._refresh_ui()
                self._procesando_derrotado = False
                if pp.outrage_locked and not pp.fainted:
                    self.root.after(500, self._auto_enfado_turn)
                return
        elif ap.fainted and not ai_alive:
            self._procesando_derrotado = False
            self._game_over(winner="player")
            return

        self.buttons_locked = False
        self._refresh_ui()
        self._procesando_derrotado = False
        if pp.outrage_locked and not pp.fainted:
            self.root.after(500, self._auto_enfado_turn)

    def _mostrar_pregunta_cambio(self, nuevo_pokemon, nuevo_idx):
        """Muestra la ventana preguntando si quiere cambiar"""
        if self._ventana_cambio_abierta:
            return
        self._ventana_cambio_abierta = True
        
        available = [i for i, p in enumerate(self.player_team) 
                    if not p.fainted and i != self.player_active_idx]
        
        if not available:
            self._ventana_cambio_abierta = False
            self.ai_active_idx = nuevo_idx
            new_ap = self.ai_team[nuevo_idx]
            new_ap.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
            new_ap.protect_success = True
            new_ap.protect_fail_count = 0
            msgs = apply_hazards_on_switch(new_ap, self.ai_hazards, False)
            for m in msgs:
                self._log(m, "effect")
            self._log(f"🔄 La IA envió a {new_ap.nombre}!", "ai")
            self.buttons_locked = False
            self._refresh_ui()
            self._procesando_derrotado = False
            return
        
        self.buttons_locked = True
        win = tk.Toplevel(self.root)
        win.title("¡Pokémon rival derrotado!")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()
        win.transient(self.root)
        win.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - 200
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - 120
        win.geometry(f"+{x}+{y}")

        tk.Label(win, text=f"✨ ¡Derrotaste al Pokémon rival!\nEl rival va a enviar a {nuevo_pokemon.nombre}.\n¿Quieres cambiar tu Pokémon?",
                font=("Courier", 11, "bold"), bg=BG, fg=GOLD,
                justify="center").pack(pady=12, padx=20)
        btn_frame = tk.Frame(win, bg=BG)
        btn_frame.pack(pady=10)

        def on_yes():
            win.destroy()
            self._ventana_cambio_abierta = False
            self._mostrar_seleccion_cambio()

        def on_no():
            win.destroy()
            self._ventana_cambio_abierta = False
            self.buttons_locked = False
            nuevo_idx, nuevo_pokemon = self._pokemon_ia_pendiente
            self.ai_active_idx = nuevo_idx
            new_ap = self.ai_team[nuevo_idx]
            new_ap.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
            new_ap.protect_success = True
            new_ap.protect_fail_count = 0
            msgs = apply_hazards_on_switch(new_ap, self.ai_hazards, False)
            for m in msgs:
                self._log(m, "effect")
            self._log(f"🔄 La IA envió a {new_ap.nombre}!", "ai")
            self._refresh_ui()
            self._procesando_derrotado = False
            pp = self.player_team[self.player_active_idx]
            if pp.outrage_locked and not pp.fainted:
                self.root.after(500, self._auto_enfado_turn)

        tk.Button(btn_frame, text="✅ SÍ, cambiar", font=("Courier", 10, "bold"),
                bg=GREEN, fg="#333", relief="flat", bd=0, padx=20, pady=8,
                cursor="hand2", command=on_yes).pack(side="left", padx=10)
        tk.Button(btn_frame, text="❌ NO, seguir", font=("Courier", 10, "bold"),
                bg=ACCENT, fg="white", relief="flat", bd=0, padx=20, pady=8,
                cursor="hand2", command=on_no).pack(side="left", padx=10)

    def _mostrar_seleccion_cambio(self):
        """Muestra los Pokémon disponibles para cambiar"""
        if self._ventana_cambio_abierta:
            return
        self._ventana_cambio_abierta = True
        
        win = tk.Toplevel(self.root)
        win.title("Cambiar Pokémon")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="🔄 Elige tu próximo Pokémon:",
                 font=("Courier", 11, "bold"), bg=BG, fg=BLUE_C,
                 justify="center").pack(pady=12, padx=20)
        
        for i, p in enumerate(self.player_team):
            if p.fainted or i == self.player_active_idx:
                continue
            hp_pct = int(p.current_hp / p.max_hp * 100)
            bar_len = 14
            filled = int(bar_len * hp_pct / 100)
            bar_txt = "█" * filled + "░" * (bar_len - filled)
            status_txt = f" [{STATUS_LABELS.get(p.status,'')}]" if p.status else ""
            lbl = (f"{p.nombre} (N{p.level})  ({p.tipo1}"
                   + (f"/{p.tipo2}" if p.tipo2 else "")
                   + f")\nHP: {p.current_hp}/{p.max_hp} [{bar_txt}] {hp_pct}%{status_txt}")
            btn = tk.Button(win, text=lbl, font=("Courier", 10),
                            bg=BG2, fg=TEXTCOL, relief="flat", bd=0,
                            padx=10, pady=6, anchor="w", justify="left",
                            activebackground=BG3, cursor="hand2",
                            command=lambda idx=i, w=win: self._ejecutar_cambio_despues_ko(idx, w))
            btn.pack(fill="x", padx=16, pady=3)

    def _ejecutar_cambio_despues_ko(self, new_idx, win):
        """Ejecuta el cambio del jugador y luego la IA envía a su Pokémon"""
        win.destroy()
        self._ventana_cambio_abierta = False
        
        self.player_active_idx = new_idx
        new_pokemon = self.player_team[new_idx]
        new_pokemon.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
        new_pokemon.protect_success = True
        new_pokemon.protect_fail_count = 0
        msgs_player = apply_hazards_on_switch(new_pokemon, self.player_hazards, True)
        self._log(f"🔄 Cambiaste a {new_pokemon.nombre}!", "player")
        for m in msgs_player:
            self._log(m, "effect")
        
        nuevo_idx, nuevo_pokemon = self._pokemon_ia_pendiente
        self.ai_active_idx = nuevo_idx
        new_ap = self.ai_team[nuevo_idx]
        new_ap.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
        new_ap.protect_success = True
        new_ap.protect_fail_count = 0
        msgs = apply_hazards_on_switch(new_ap, self.ai_hazards, False)
        for m in msgs:
            self._log(m, "effect")
        self._log(f"🔄 La IA envió a {new_ap.nombre}!", "ai")
        
        self.buttons_locked = False
        self._refresh_ui()
        self._procesando_derrotado = False
        if new_pokemon.outrage_locked and not new_pokemon.fainted:
            self.root.after(500, self._auto_enfado_turn)

    def _force_switch_dialog(self):
        if self._ventana_cambio_abierta:
            return
        self._ventana_cambio_abierta = True        
        win = tk.Toplevel(self.root)
        win.title("¡Tu Pokémon fue derrotado!")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()

        tk.Label(win, text="💀 ¡Tu Pokémon fue derrotado!\nElige un sustituto:",
                 font=("Courier", 11, "bold"), bg=BG, fg=ACCENT,
                 justify="center").pack(pady=12, padx=20)

        for i, p in enumerate(self.player_team):
            if p.fainted:
                continue
            hp_pct = int(p.current_hp / p.max_hp * 100)
            bar_len = 14
            filled = int(bar_len * hp_pct / 100)
            bar_txt = "█"*filled + "░"*(bar_len - filled)
            status_txt = f" [{STATUS_LABELS.get(p.status,'')}]" if p.status else ""
            lbl = (f"{p.nombre} (N{p.level})  ({p.tipo1}"
                   + (f"/{p.tipo2}" if p.tipo2 else "")
                   + f")\nHP: {p.current_hp}/{p.max_hp} [{bar_txt}] {hp_pct}%{status_txt}")
            btn = tk.Button(win, text=lbl, font=("Courier", 10),
                            bg=BG2, fg=TEXTCOL, relief="flat", bd=0,
                            padx=10, pady=6, anchor="w", justify="left",
                            activebackground=BG3, cursor="hand2",
                            command=lambda idx=i, w=win: self._forced_switch(idx, w))
            btn.pack(fill="x", padx=16, pady=3)

    def _forced_switch(self, idx, win):
        win.destroy()
        self._ventana_cambio_abierta = False
        p = self.player_team[idx]
        msgs = apply_hazards_on_switch(p, self.player_hazards, True)
        for m in msgs:
            self._log(m, "effect")
        if p.fainted:
            self._log("💀 ¡El Pokémon murió por los peligros!", "ai")
            alive = [i for i, pk in enumerate(self.player_team) if not pk.fainted]
            if not alive:
                self._game_over("ai")
                return
            self._force_switch_dialog()
            return
        self.player_active_idx = idx
        p.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
        p.protect_success = True
        p.protect_fail_count = 0
        self._log(f"🔄 ¡{p.nombre} al campo!", "player")
        self.buttons_locked = False
        self._refresh_ui()

    def _game_over(self, winner):
        if self._game_over_active:
            return
        self._game_over_active = True
        
        self.buttons_locked = True
        self._refresh_ui()
        
        win = tk.Toplevel(self.root)
        win.title("¡Fin de la batalla!")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()
        win.transient(self.root)

        if winner == "player":
            msg = "🏆 ¡VICTORIA! 🏆\n¡Derrotaste a todos los\nPokémon rivales!"
            col = GOLD
        else:
            msg = "💀 DERROTA 💀\n¡Todos tus Pokémon\nhan sido derrotados!"
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
        
        tk.Button(frame_botones, text="🔄  JUGAR DE NUEVO",
                  font=("Courier", 10, "bold"), bg=BG3, fg=GOLD,
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                  command=restart_game).pack(side="left", padx=10)
        
        tk.Button(frame_botones, text="🏠  MENÚ PRINCIPAL",
                  font=("Courier", 10, "bold"), bg=BLUE_C, fg="#1a1a2e",
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                  command=exit_to_menu).pack(side="left", padx=10)
        
        tk.Button(frame_botones, text="✖  SALIR",
                  font=("Courier", 10, "bold"), bg=ACCENT, fg="white",
                  relief="flat", bd=0, padx=14, pady=8, cursor="hand2",
                  command=self.root.destroy).pack(side="left", padx=10)

    def _restart(self):
        self.log_text.config(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.config(state="disabled")
        
        self._game_over_active = False
        self.buttons_locked = False
        self.pending_switch = False
        self.pending_switch_idx = None
        self.just_switched_by_move = False
        self._auto_enfado_active = False
        self._auto_vuelo_active = False
        self._pending_vuelo = False
        self._cola_acciones = []
        self._procesando_derrotado = False
        self._pokemon_derrotado_en_turno = None
        self._pokemon_ia_pendiente = None
        self._ventana_cambio_abierta = False

        self.player_team = []
        self.ai_team = []
        self.pokemon_data_list = []

        for widget in self.winfo_children():
            widget.destroy()

        self._build_ui()
        self._start_new_game()


def main():
    root = tk.Tk()
    app = PokemonGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()