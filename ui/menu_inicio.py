import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import os
from utiles.estadisticas import obtener_estadisticas, resetear_estadisticas

# Colores
BG = "#1a1a2e"
ACCENT = "#e94560"
GOLD = "#f5a623"
TEXTCOL = "#ffffff"
TEXT2 = "#cbd5e1"
GREEN = "#4ade80"

# Color del panel
PANEL_BG = "#2a2a3e"

class PokemonMenu(tk.Frame):
    def __init__(self, parent, on_start_callback):
        super().__init__(parent, bg=BG)
        self.parent = parent
        self.on_start_callback = on_start_callback
        self.modo = "pve"
        self.ai_level = 1
        self.ai2_level = 1
        self.battle_type = 4
        self.bg_image_full = None
        self.bg_label = None
        self.current_step = 1
        
        self.pack(fill="both", expand=True)
        self._load_full_background()
        self._build_ui()
        self.bind("<Configure>", self._on_window_resize)
    
    def _load_full_background(self):
        #Carga imagen de fondo
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            images_dir = os.path.join(current_dir, "images")
            
            if not os.path.exists(images_dir):
                return
            
            img_path = None
            for archivo in os.listdir(images_dir):
                if archivo.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(images_dir, archivo)
                    break
            
            if img_path:
                self.original_img = Image.open(img_path)
                
                self.update_idletasks()
                window_width = self.winfo_width()
                window_height = self.winfo_height()
                
                if window_width < 100:
                    window_width = 1000
                    window_height = 750
                    self.parent.geometry(f"{window_width}x{window_height}")
                
                img_resized = self.original_img.resize((window_width, window_height), Image.Resampling.LANCZOS)
                self.bg_image_full = ImageTk.PhotoImage(img_resized)
                
                self.bg_label = tk.Label(self, image=self.bg_image_full)
                self.bg_label.place(x=0, y=0, width=window_width, height=window_height)
                self.bg_label.lower()
                
        except Exception as e:
            pass
    
    def _resize_background(self, width, height):
        try:
            if hasattr(self, 'original_img') and self.original_img:
                img_resized = self.original_img.resize((width, height), Image.Resampling.LANCZOS)
                self.bg_image_full = ImageTk.PhotoImage(img_resized)
                if self.bg_label:
                    self.bg_label.config(image=self.bg_image_full)
                    self.bg_label.place(x=0, y=0, width=width, height=height)
        except Exception as e:
            pass
    
    def _on_window_resize(self, event):
        self._resize_background(event.width, event.height)
    
    def _on_start(self):
        #Inicia la batalla con la configuración seleccionada
        self.ai_level = self.ai_level_var.get()
        if self.modo == "simulation":
            self.ai2_level = self.ai2_level_var.get()
        else:
            self.ai2_level = 1
        self.battle_type = self.battle_type_var.get()
        self.on_start_callback(self.modo, self.ai_level, self.ai2_level, self.battle_type)
    
    def _next_step(self):
        if self.current_step == 1:
            self.current_step = 2
            self._show_level_selection()
        elif self.current_step == 2:
            self._on_start()
    
    def _back_step(self):
        if self.current_step >= 2:
            self.current_step = 1
            self._show_mode_selection()
    
    def _show_mode_selection(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        self.container.place(relx=0.5, rely=0.5, anchor="center", width=550, height=550)
        tk.Label(self.container, text=" POKEFISI ", font=("Courier", 24, "bold"), 
                bg=PANEL_BG, fg=GOLD).pack(pady=(15, 5))
        tk.Label(self.container, text="Batallas Pokémon", font=("Courier", 10), 
                bg=PANEL_BG, fg=TEXTCOL).pack(pady=(0, 15))
        tk.Frame(self.container, bg=ACCENT, height=2).pack(fill="x", padx=40, pady=5)
        tk.Frame(self.container, bg=PANEL_BG, height=30).pack()
        
        # Selector de modo
        mode_frame = tk.LabelFrame(self.container, text="MODO DE JUEGO", 
                                font=("Courier", 11, "bold"),
                                bg=PANEL_BG, fg=GOLD, padx=30, pady=12)
        mode_frame.pack(pady=10, padx=30, fill="x")

        self.modo_var = tk.StringVar(value="pve")
        
        def on_mode_change():
            self.modo = self.modo_var.get()

        rb1 = tk.Radiobutton(mode_frame, text="Jugador vs IA", variable=self.modo_var,
                            value="pve", bg=PANEL_BG, fg=TEXTCOL, selectcolor='#1a1a2e',
                            font=("Courier", 10), activebackground=PANEL_BG, 
                            activeforeground=GOLD, command=on_mode_change)
        rb1.pack(anchor="w", pady=5)

        rb2 = tk.Radiobutton(mode_frame, text="IA vs IA (Espectador)", variable=self.modo_var,
                            value="simulation", bg=PANEL_BG, fg=TEXTCOL, selectcolor='#1a1a2e',
                            font=("Courier", 10), activebackground=PANEL_BG,
                            activeforeground=GOLD, command=on_mode_change)
        rb2.pack(anchor="w", pady=5)

        # Boton estadisticas
        tk.Button(self.container, text="ESTADÍSTICAS",
                 font=("Courier", 10, "bold"),
                 bg='#2d5a8e', fg=TEXTCOL, relief="flat", bd=0,
                 padx=20, pady=6, cursor="hand2",
                 activebackground='#3a70aa',
                 command=self._show_statistics).pack(pady=(8, 0))
        tk.Frame(self.container, bg=PANEL_BG, height=20).pack()    
        btn_frame = tk.Frame(self.container, bg=PANEL_BG)
        btn_frame.pack(pady=10)      
        tk.Button(btn_frame, text="  SIGUIENTE  ",
                 font=("Courier", 12, "bold"),
                 bg=GREEN, fg="#1a1a2e", relief="flat", bd=0,
                 padx=35, pady=8, cursor="hand2",
                 activebackground="#5ee89e",
                 command=self._next_step).pack()
    
    def _show_level_selection(self):
        for widget in self.container.winfo_children():
            widget.destroy()

        panel_height = 680 if self.modo == "simulation" else 550
        self.container.place(relx=0.5, rely=0.5, anchor="center", width=550, height=panel_height)

        tk.Label(self.container, text=" POKEFISI ", font=("Courier", 24, "bold"), 
                bg=PANEL_BG, fg=GOLD).pack(pady=(15, 5))
        tk.Label(self.container, text="Configura la batalla", font=("Courier", 10), 
                bg=PANEL_BG, fg=TEXTCOL).pack(pady=(0, 15))
        tk.Frame(self.container, bg=ACCENT, height=2).pack(fill="x", padx=40, pady=5)
        tk.Frame(self.container, bg=PANEL_BG, height=10).pack()

        # Selector de nivel IA (Jugador o IA1)
        if self.modo == "pve":
            level_label = "NIVEL DE IA (RIVAL)"
        else:
            level_label = "NIVEL DE IA 1 (AZUL)"
        
        level_frame = tk.LabelFrame(self.container, text=level_label, 
                                    font=("Courier", 11, "bold"),
                                    bg=PANEL_BG, fg=GOLD, padx=30, pady=12)
        level_frame.pack(pady=10, padx=30, fill="x")

        self.ai_level_var = tk.IntVar(value=1)

        rb_nivel1 = tk.Radiobutton(level_frame, text="Nivel 1 - Fácil ", 
                                variable=self.ai_level_var, value=1,
                                bg=PANEL_BG, fg=TEXTCOL, selectcolor='#1a1a2e',
                                font=("Courier", 10), activebackground=PANEL_BG,
                                activeforeground=GOLD)
        rb_nivel1.pack(anchor="w", pady=5)

        rb_nivel2 = tk.Radiobutton(level_frame, text="Nivel 2 - Medio ", 
                                variable=self.ai_level_var, value=2,
                                bg=PANEL_BG, fg=TEXTCOL, selectcolor='#1a1a2e',
                                font=("Courier", 10), activebackground=PANEL_BG,
                                activeforeground=GOLD)
        rb_nivel2.pack(anchor="w", pady=5)
        
        # Selector de nivel IA2 (solo para modo simulación)
        if self.modo == "simulation":
            tk.Frame(self.container, bg=PANEL_BG, height=10).pack()
            
            level2_frame = tk.LabelFrame(self.container, text="NIVEL DE IA 2 (ROJO)", 
                                        font=("Courier", 11, "bold"),
                                        bg=PANEL_BG, fg=GOLD, padx=30, pady=12)
            level2_frame.pack(pady=10, padx=30, fill="x")
            
            self.ai2_level_var = tk.IntVar(value=1)
            
            rb2_nivel1 = tk.Radiobutton(level2_frame, text="Nivel 1 - Fácil ", 
                                    variable=self.ai2_level_var, value=1,
                                    bg=PANEL_BG, fg=TEXTCOL, selectcolor='#1a1a2e',
                                    font=("Courier", 10), activebackground=PANEL_BG,
                                    activeforeground=GOLD)
            rb2_nivel1.pack(anchor="w", pady=5)
            
            rb2_nivel2 = tk.Radiobutton(level2_frame, text="Nivel 2 - Medio ", 
                                    variable=self.ai2_level_var, value=2,
                                    bg=PANEL_BG, fg=TEXTCOL, selectcolor='#1a1a2e',
                                    font=("Courier", 10), activebackground=PANEL_BG,
                                    activeforeground=GOLD)
            rb2_nivel2.pack(anchor="w", pady=5)
        
        tk.Frame(self.container, bg=PANEL_BG, height=10).pack()
        
        # Selector de tipo de combate
        battle_frame = tk.LabelFrame(self.container, text="TIPO DE COMBATE", 
                                    font=("Courier", 11, "bold"),
                                    bg=PANEL_BG, fg=GOLD, padx=30, pady=12)
        battle_frame.pack(pady=10, padx=30, fill="x")
        
        self.battle_type_var = tk.IntVar(value=4)
        
        rb_4v4 = tk.Radiobutton(battle_frame, text="4 vs 4 (4 Pokémon por equipo)", 
                               variable=self.battle_type_var, value=4,
                               bg=PANEL_BG, fg=TEXTCOL, selectcolor='#1a1a2e',
                               font=("Courier", 10), activebackground=PANEL_BG,
                               activeforeground=GOLD)
        rb_4v4.pack(anchor="w", pady=5)
        
        rb_3v3 = tk.Radiobutton(battle_frame, text="3 vs 3 (3 Pokémon por equipo)", 
                               variable=self.battle_type_var, value=3,
                               bg=PANEL_BG, fg=TEXTCOL, selectcolor='#1a1a2e',
                               font=("Courier", 10), activebackground=PANEL_BG,
                               activeforeground=GOLD)
        rb_3v3.pack(anchor="w", pady=5)
        
        tk.Frame(self.container, bg=PANEL_BG, height=15).pack()
        
        btn_frame = tk.Frame(self.container, bg=PANEL_BG)
        btn_frame.pack(pady=10)
        #Botones
        tk.Button(btn_frame, text="  ATRÁS  ",
                 font=("Courier", 11, "bold"),
                 bg='#3a3a4e', fg=TEXTCOL, relief="flat", bd=0,
                 padx=25, pady=8, cursor="hand2",
                 activebackground="#4a4a5e",
                 command=self._back_step).pack(side="left", padx=10)
        
        btn_text = "  EMPEZAR BATALLA  " if self.modo == "pve" else "OBSERVAR BATALLA"
        tk.Button(btn_frame, text=btn_text,
                 font=("Courier", 11, "bold"),
                 bg=GREEN, fg="#1a1a2e", relief="flat", bd=0,
                 padx=25, pady=8, cursor="hand2",
                 activebackground="#5ee89e",
                 command=self._on_start).pack(side="left", padx=10)
    
    def _show_statistics(self):
        #Muestra ventana con estadisticas de las IAs
        stats = obtener_estadisticas()

        win = tk.Toplevel(self.parent)
        win.title("Estadísticas de IAs")
        win.configure(bg=BG)
        win.resizable(False, False)
        win.grab_set()
        win.transient(self.parent)
        win.geometry("440x400")

        tk.Label(win, text="ESTADÍSTICAS DE IAs",
                 font=("Courier", 16, "bold"), bg=BG, fg=GOLD).pack(pady=(18, 4))
        tk.Frame(win, bg=ACCENT, height=2).pack(fill="x", padx=30, pady=4)

        def make_ia_panel(parent, titulo, clave, color):
            ia_data = stats.get(clave, {"victorias": 0, "derrotas": 0})
            victorias = ia_data.get("victorias", 0)
            derrotas = ia_data.get("derrotas", 0)
            total = victorias + derrotas
            pct = f"{(victorias/total*100):.0f}%" if total > 0 else "---"

            frame = tk.LabelFrame(parent, text=titulo,
                                  font=("Courier", 11, "bold"),
                                  bg=PANEL_BG, fg=color, padx=20, pady=10)
            frame.pack(pady=8, padx=30, fill="x")

            row = tk.Frame(frame, bg=PANEL_BG)
            row.pack(fill="x")

            tk.Label(row, text=f"Victorias: {victorias}",
                     font=("Courier", 10), bg=PANEL_BG, fg="#4ade80").pack(side="left", padx=10)
            tk.Label(row, text=f"Derrotas: {derrotas}",
                     font=("Courier", 10), bg=PANEL_BG, fg=ACCENT).pack(side="left", padx=10)
            tk.Label(row, text=f":D",
                     font=("Courier", 10), bg=PANEL_BG, fg=TEXT2).pack(side="left", padx=10)

        make_ia_panel(win, "IA NIVEL 1 - FÁCIL", "ia1", "#60a5fa")
        make_ia_panel(win, "IA NIVEL 2 - MEDIO", "ia2", "#f59e0b")

        tk.Frame(win, bg=BG, height=5).pack()
        tk.Label(win, text="Las estadísticas incluyen batallas contra jugador y entre IAs.",
                 font=("Courier", 8), bg=BG, fg=TEXT2, wraplength=380, justify="center").pack(pady=4)

        btn_frame = tk.Frame(win, bg=BG)
        btn_frame.pack(pady=10)

        def confirmar_reset():
            confirm = tk.Toplevel(win)
            confirm.title("Confirmar")
            confirm.configure(bg=BG)
            confirm.resizable(False, False)
            confirm.grab_set()
            confirm.transient(win)
            tk.Label(confirm, text="¿Reiniciar todas las estadísticas?",
                     font=("Courier", 11), bg=BG, fg=TEXTCOL).pack(pady=16, padx=20)
            bf = tk.Frame(confirm, bg=BG)
            bf.pack(pady=8)
            def do_reset():
                resetear_estadisticas()
                confirm.destroy()
                win.destroy()
                self._show_statistics()
            tk.Button(bf, text="SÍ, REINICIAR",
                      font=("Courier", 9, "bold"), bg=ACCENT, fg=TEXTCOL,
                      relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                      command=do_reset).pack(side="left", padx=8)
            tk.Button(bf, text="CANCELAR",
                      font=("Courier", 9, "bold"), bg='#3a3a4e', fg=TEXTCOL,
                      relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                      command=confirm.destroy).pack(side="left", padx=8)

        tk.Button(btn_frame, text="REINICIAR ESTADÍSTICAS",
                  font=("Courier", 9, "bold"), bg='#3a3a4e', fg=TEXT2,
                  relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                  command=confirmar_reset).pack(side="left", padx=8)
        tk.Button(btn_frame, text="CERRAR",
                  font=("Courier", 9, "bold"), bg='#2d5a8e', fg=TEXTCOL,
                  relief="flat", bd=0, padx=12, pady=6, cursor="hand2",
                  command=win.destroy).pack(side="left", padx=8)

    def _build_ui(self):
        for widget in self.winfo_children():
            if widget != self.bg_label:
                widget.destroy()
        
        self.container = tk.Frame(self, bg=PANEL_BG, bd=2, relief="solid",
                                  highlightbackground=ACCENT, highlightthickness=1)
        self.container.place(relx=0.5, rely=0.5, anchor="center", width=550, height=550)
        
        self._show_mode_selection()