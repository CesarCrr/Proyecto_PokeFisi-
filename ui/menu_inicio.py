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
        self.logo_image = None
        self.logo_label = None
        self.recuadro_image = None
        self.container_image_label = None
        self.small_logo_image = None
        self.container_canvas = None
        self.logo_canvas_img_id = None
        self.modo_var = tk.StringVar(value=self.modo)
        self.ai_level_var = tk.IntVar(value=self.ai_level)
        self.ai2_level_var = tk.IntVar(value=self.ai2_level)
        self.battle_type_var = tk.IntVar(value=self.battle_type)
        
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
        self._resize_logo_and_recuadro(event.width, event.height)
        self._redraw_current_step()

    def _redraw_current_step(self):
        if self.current_step == 1:
            self._show_mode_selection()
        elif self.current_step == 2:
            self._show_level_selection()
    
    def _load_logo_and_recuadro(self):
        """Carga las imágenes del logo y el recuadro"""
        try:
            current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            images_dir = os.path.join(current_dir, "images")
            
            if not os.path.exists(images_dir):
                return
            
            # Cargar logo
            logo_path = os.path.join(images_dir, "Logo_Pokefisi.png")
            if os.path.exists(logo_path):
                self.logo_original = Image.open(logo_path)
        except Exception as e:
            pass
    
    def _resize_logo_and_recuadro(self, window_width, window_height):
        """Redimensiona el logo y el recuadro según el tamaño de la ventana"""
        try:
            canvas_width = min(max(int(window_width * 0.62), 520), max(window_width - 40, 520))
            canvas_height = min(max(int(window_height * 0.75), 560), max(window_height - 40, 520))
            if self.container_canvas:
                self.container_canvas.place(relx=0.5, rely=0.47, anchor="center", width=canvas_width, height=canvas_height)

            if hasattr(self, 'logo_original') and self.logo_original:
                ratio = self.logo_original.width / self.logo_original.height
                logo_height = min(240, max(180, int(window_height * 0.22)))
                logo_width = int(logo_height * ratio)
                logo_resized = self.logo_original.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(logo_resized)

                small_logo_height = min(180, max(140, int(window_height * 0.16)))
                small_logo_width = int(small_logo_height * ratio)
                small_logo_resized = self.logo_original.resize((small_logo_width, small_logo_height), Image.Resampling.LANCZOS)
                self.small_logo_image = ImageTk.PhotoImage(small_logo_resized)

                if self.container_canvas and self.logo_canvas_img_id is not None:
                    self.container_canvas.coords(self.logo_canvas_img_id, canvas_width // 2, min(150, canvas_height // 5))
                    self.container_canvas.itemconfig(self.logo_canvas_img_id, image=self.small_logo_image)
        except Exception:
            pass
    
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
        # Limpiar widgets anteriores
        for item in self.container_canvas.find_all():
            if item not in [self.logo_canvas_img_id]:
                self.container_canvas.delete(item)

        self.container_canvas.update_idletasks()
        canvas_width = max(self.container_canvas.winfo_width(), 520)
        canvas_height = max(self.container_canvas.winfo_height(), 520)
        center_x = canvas_width // 2

        y_offset = max(100, int(canvas_height * 0.15))

        if hasattr(self, 'small_logo_image') and self.small_logo_image:
            if self.logo_canvas_img_id is None:
                self.logo_canvas_img_id = self.container_canvas.create_image(center_x, y_offset, image=self.small_logo_image, anchor="center")
            else:
                self.container_canvas.itemconfig(self.logo_canvas_img_id, image=self.small_logo_image)
                self.container_canvas.coords(self.logo_canvas_img_id, center_x, y_offset)
            y_offset += min(120, int(canvas_height * 0.18))
        else:
            title_id = self.container_canvas.create_text(center_x, y_offset, text="POKEFISI", font=("Courier", 24, "bold"), fill=GOLD, anchor="center")
            y_offset += 35

        subtitle_id = self.container_canvas.create_text(center_x, y_offset, text="Selecciona el modo de juego", font=("Courier", 10), fill=TEXTCOL, anchor="center")
        y_offset += 18

        line_width = min(170, int(canvas_width * 0.35))
        self.container_canvas.create_line(center_x - line_width, y_offset, center_x + line_width, y_offset, fill=ACCENT, width=2)
        y_offset += 16

        # Radio buttons para modo
        def on_mode_change():
            self.modo = self.modo_var.get()

        rb1_id = self.container_canvas.create_window(center_x, y_offset, window=tk.Radiobutton(self.container_canvas, text="Jugador vs IA", variable=self.modo_var,
                            value="pve", bg=BG, fg=TEXTCOL, selectcolor=BG,
                            font=("Courier", 10), activebackground=BG,
                            activeforeground=GOLD, command=on_mode_change), anchor="center")
        y_offset += 28

        rb2_id = self.container_canvas.create_window(center_x, y_offset, window=tk.Radiobutton(self.container_canvas, text="IA vs IA (Espectador)", variable=self.modo_var,
                            value="simulation", bg=BG, fg=TEXTCOL, selectcolor=BG,
                            font=("Courier", 10), activebackground=BG,
                            activeforeground=GOLD, command=on_mode_change), anchor="center")
        y_offset += 30

        stats_btn = tk.Button(self.container_canvas, text="ESTADÍSTICAS",
                 font=("Courier", 10, "bold"),
                 bg='#2d5a8e', fg=TEXTCOL, relief="flat", bd=0,
                 padx=20, pady=6, cursor="hand2",
                 activebackground='#3a70aa',
                 command=self._show_statistics)
        self.container_canvas.create_window(center_x, y_offset, window=stats_btn, anchor="center", width=min(canvas_width - 80, 300))
        y_offset += 50

        next_btn = tk.Button(self.container_canvas, text="  SIGUIENTE  ",
                 font=("Courier", 12, "bold"),
                 bg=GREEN, fg="#1a1a2e", relief="flat", bd=0,
                 padx=35, pady=8, cursor="hand2",
                 activebackground="#5ee89e",
                 command=self._next_step)
        self.container_canvas.create_window(center_x, y_offset, window=next_btn, anchor="center", width=min(canvas_width - 80, 320))
    
    def _show_level_selection(self):
        # Limpiar widgets anteriores
        for item in self.container_canvas.find_all():
            if item not in [self.logo_canvas_img_id]:
                self.container_canvas.delete(item)

        self.container_canvas.update_idletasks()
        canvas_width = max(self.container_canvas.winfo_width(), 520)
        canvas_height = max(self.container_canvas.winfo_height(), 520)
        center_x = canvas_width // 2

        y_offset = max(100, int(canvas_height * 0.15))

        # Logo pequeño
        if hasattr(self, 'small_logo_image') and self.small_logo_image:
            if self.logo_canvas_img_id is None:
                self.logo_canvas_img_id = self.container_canvas.create_image(center_x, y_offset, image=self.small_logo_image, anchor="center")
            else:
                self.container_canvas.itemconfig(self.logo_canvas_img_id, image=self.small_logo_image)
                self.container_canvas.coords(self.logo_canvas_img_id, center_x, y_offset)
            y_offset += 120
        else:
            title_id = self.container_canvas.create_text(center_x, y_offset, text="POKEFISI", font=("Courier", 24, "bold"), fill=GOLD, anchor="center")
            y_offset += 40

        # Subtítulo
        subtitle_id = self.container_canvas.create_text(center_x, y_offset, text="Configura la batalla", font=("Courier", 10), fill=TEXTCOL, anchor="center")
        y_offset += 18

        # Línea separadora
        line_width = min(170, int(canvas_width * 0.35))
        self.container_canvas.create_line(center_x - line_width, y_offset, center_x + line_width, y_offset, fill=ACCENT, width=2)
        y_offset += 18

        # Selector de nivel IA
        if self.modo == "pve":
            level_label = "NIVEL DE IA (RIVAL)"
        else:
            level_label = "NIVEL DE IA 1 (AZUL)"

        level_title_id = self.container_canvas.create_text(center_x, y_offset, text=level_label, font=("Courier", 11, "bold"), fill=GOLD, anchor="center")
        y_offset += 24
        if not hasattr(self, 'ai_level_var') or self.ai_level_var is None:
            self.ai_level_var = tk.IntVar(value=1)

        rb_nivel1_id = self.container_canvas.create_window(center_x, y_offset, window=tk.Radiobutton(self.container_canvas, text="Nivel 1 - Fácil ",
                                variable=self.ai_level_var, value=1,
                                bg=BG, fg=TEXTCOL, selectcolor=BG,
                                font=("Courier", 10), activebackground=BG,
                                activeforeground=GOLD), anchor="center")
        y_offset += 24

        rb_nivel2_id = self.container_canvas.create_window(center_x, y_offset, window=tk.Radiobutton(self.container_canvas, text="Nivel 2 - Medio ",
                                variable=self.ai_level_var, value=2,
                                bg=BG, fg=TEXTCOL, selectcolor=BG,
                                font=("Courier", 10), activebackground=BG,
                                activeforeground=GOLD), anchor="center")
        y_offset += 26

        # Selector de nivel IA2 (solo para modo simulación)
        if self.modo == "simulation":
            level2_title_id = self.container_canvas.create_text(center_x, y_offset, text="NIVEL DE IA 2 (ROJO)", font=("Courier", 11, "bold"), fill=GOLD, anchor="center")
            y_offset += 18

            self.ai2_level_var = tk.IntVar(value=1)

            rb2_nivel1_id = self.container_canvas.create_window(center_x, y_offset, window=tk.Radiobutton(self.container_canvas, text="Nivel 1 - Fácil ",
                                    variable=self.ai2_level_var, value=1,
                                    bg=BG, fg=TEXTCOL, selectcolor=BG,
                                    font=("Courier", 10), activebackground=BG,
                                    activeforeground=GOLD), anchor="center")
            y_offset += 20

            rb2_nivel2_id = self.container_canvas.create_window(center_x, y_offset, window=tk.Radiobutton(self.container_canvas, text="Nivel 2 - Medio ",
                                    variable=self.ai2_level_var, value=2,
                                    bg=BG, fg=TEXTCOL, selectcolor=BG,
                                    font=("Courier", 10), activebackground=BG,
                                    activeforeground=GOLD), anchor="center")
            y_offset += 24

        # Selector de tipo de combate
        battle_title_id = self.container_canvas.create_text(center_x, y_offset, text="TIPO DE COMBATE", font=("Courier", 11, "bold"), fill=GOLD, anchor="center")
        y_offset += 18

        if not hasattr(self, 'battle_type_var') or self.battle_type_var is None:
            self.battle_type_var = tk.IntVar(value=4)

        rb_4v4_id = self.container_canvas.create_window(center_x, y_offset, window=tk.Radiobutton(self.container_canvas, text="4 vs 4 (4 Pokémon por equipo)",
                               variable=self.battle_type_var, value=4,
                               bg=BG, fg=TEXTCOL, selectcolor=BG,
                               font=("Courier", 10), activebackground=BG,
                               activeforeground=GOLD), anchor="center")
        y_offset += 20

        rb_3v3_id = self.container_canvas.create_window(center_x, y_offset, window=tk.Radiobutton(self.container_canvas, text="3 vs 3 (3 Pokémon por equipo)",
                               variable=self.battle_type_var, value=3,
                               bg=BG, fg=TEXTCOL, selectcolor=BG,
                               font=("Courier", 10), activebackground=BG,
                               activeforeground=GOLD), anchor="center")
        y_offset += 30

        buttons_frame = tk.Frame(self.container_canvas, bg=BG)
        back_btn = tk.Button(buttons_frame, text="  ATRÁS  ",
                 font=("Courier", 11, "bold"),
                 bg='#3a3a4e', fg=TEXTCOL, relief="flat", bd=0,
                 padx=20, pady=8, cursor="hand2",
                 activebackground="#4a4a5e",
                 command=self._back_step)
        start_btn_text = "  EMPEZAR BATALLA  " if self.modo == "pve" else "OBSERVAR BATALLA"
        start_btn = tk.Button(buttons_frame, text=start_btn_text,
                 font=("Courier", 11, "bold"),
                 bg=GREEN, fg="#1a1a2e", relief="flat", bd=0,
                 padx=20, pady=8, cursor="hand2",
                 activebackground="#5ee89e",
                 command=self._on_start)

        container_width = max(self.container_canvas.winfo_width(), 520)
        if container_width > 520:
            back_btn.pack(side="left", padx=10, pady=4)
            start_btn.pack(side="left", padx=10, pady=4)
        else:
            back_btn.pack(fill="x", pady=4)
            start_btn.pack(fill="x", pady=4)

        self.container_canvas.create_window(center_x, y_offset, window=buttons_frame, anchor="n", width=min(container_width - 60, 420))
    
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
        
        # Cargar imágenes
        self._load_logo_and_recuadro()
        
        # Crear canvas para el logo y el recuadro transparente
        self.container_canvas = tk.Canvas(self, highlightthickness=0, bg=BG)
        self.container_canvas.place(relx=0.5, rely=0.47, anchor="center", width=620, height=700)
        self.update_idletasks()
        window_width = self.winfo_width()
        window_height = self.winfo_height()
        if window_width < 100:
            window_width = 1000
            window_height = 750
        self._resize_logo_and_recuadro(window_width, window_height)
        
        self._show_mode_selection()