from ui.menu_inicio import PokemonMenu
from ui.interfaz import PokemonGUI
from ui.interfaz_simulacion import PokemonSimulationGUI
import tkinter as tk

# Colores
BG = "#1a1a2e"

class PokemonApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("PokeFisi")
        self.root.configure(bg=BG)
        self.root.resizable(True, True)
        self.root.minsize(900, 700)
        self.root.geometry("1000x750")
        
        self.current_frame = None
        self.show_menu()
    
    def show_menu(self):
        if self.current_frame:
            self.current_frame.destroy()
        
        for widget in self.root.winfo_children():
            widget.destroy()
        
        self.current_frame = PokemonMenu(self.root, self.start_battle)
        self.current_frame.pack(fill="both", expand=True)
    
    def start_battle(self, mode, ai_level, ai2_level, battle_type):
        #Inicia la batalla con la configuración seleccionada
        if self.current_frame:
            self.current_frame.destroy()
        
        for widget in self.root.winfo_children():
            widget.destroy()
        
        if mode == "simulation":
            self.current_frame = PokemonSimulationGUI(
                self.root,
                ai_level=ai_level,
                ai2_level=ai2_level,
                battle_type=battle_type,
                on_exit_callback=self.show_menu
            )
        else:
            self.current_frame = PokemonGUI(
                self.root,
                ai_level=ai_level,
                battle_type=battle_type,
                on_exit_callback=self.show_menu
            )
        self.current_frame.pack(fill="both", expand=True)
    
    def run(self):
        self.root.mainloop()


def main():
    app = PokemonApp()
    app.run()


if __name__ == "__main__":
    main()