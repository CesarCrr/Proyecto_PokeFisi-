from utiles.funciones_auxiliares import clamp, get_stat_stage_mod

class BattlePokemon:
    def __init__(self, data, preassigned_moves=None, level=55):
        self.data = data
        self.nombre = data["nombre"]
        self.tipo1 = data["tipo1"]
        self.tipo2 = data["tipo2"]
        self.level = level
        
        # Estadísticas base
        self.hp_base = data["hp"]
        self.atk_base = data["atk"]
        self.def_base = data["def_"]
        self.spe_base = data["spe"]
        
        # Calcular estadísticas reales según nivel 55
        self.max_hp = self._calcular_estadistica(self.hp_base)
        self.current_hp = self.max_hp
        self.atk = self._calcular_estadistica(self.atk_base)
        self.defensa = self._calcular_estadistica(self.def_base)
        self.spe = self._calcular_estadistica(self.spe_base)
        
        self.movimientos = []
        
        if preassigned_moves is not None and len(preassigned_moves) > 0:
            for move in preassigned_moves:
                if "pp_max" not in move:
                    move["pp_max"] = move.get("ppMax", move.get("pp_max", 0))
                self.movimientos.append(move)
        else:
            import random
            movs_originales = data["movimientos"][:]
            random.shuffle(movs_originales)
            for m in movs_originales[:4]:
                self.movimientos.append({
                    "nombre": m["nombre"],
                    "tipo": m["tipo"],
                    "categoria": m["categoria"],
                    "poder": m["poder"],
                    "precision": m["precision"],
                    "efecto": m["efecto"],
                    "pp": m["ppMax"],
                    "pp_max": m["ppMax"]
                })
        
        self.status = None
        self.status_turns = 0
        self.mods = {"atk": 0, "def": 0, "spe": 0, "evasion": 0}
        self.fainted = False
        self.poison_counter = 1
        self.wish_heal = 0
        
        self.protect_success = True
        self.protect_fail_count = 0
        self.is_protected = False
        
        self.taunted = False
        self.taunted_turns = 0
        self.paralyze_turns = 0
        self.burn_turns = 0
        self.freeze_turns = 0
        self.sleep_next = False
        
        self.confused = False
        self.confused_turns = 0
        
        self.substitute = False
        self.sub_hp = 0
        
        self.flying_turns = 0
        self.flying_move = None
        self.flying_active = False
        
        self.outrage_turns = 0
        self.outrage_active = False
        self.outrage_locked = False
        
        self.leech_seed_from = None

    def _calcular_estadistica(self, base):
        #Calcula la estadística real según nivel 55
        #  Fórmula estándar de Pokémon: ((2 * base + IV + EV/4) * nivel / 100) + 5
        # Usamos IV=31 (máximo) y EV=0 para simplificar
        
        iv = 31  # Individual Values (máximo)
        ev = 0   # Effort Values (sin entrenamiento)
        nivel = self.level
        return int(((2 * base + iv + (ev // 4)) * nivel / 100) + 5)
    
    def _calcular_hp(self, base):
        #Calcula el HP real según nivel 55
        #  Fórmula de HP: ((2 * base + IV + EV/4) * nivel / 100) + nivel + 10
   
        iv = 31
        ev = 0
        nivel = self.level
        return int(((2 * base + iv + (ev // 4)) * nivel / 100) + nivel + 10)

    def get_effective_stat(self, stat):
        from utiles.funciones_auxiliares import get_stat_stage_mod, get_evasion_mod
        if stat == "evasion":
            return get_evasion_mod(self.mods["evasion"])
        
        # Obtener la estadística base según el nivel
        if stat == "atk":
            base = self.atk
        elif stat == "def":
            base = self.defensa
        elif stat == "spe":
            base = self.spe
        else:
            base = self.atk
        
        # Aplicar modificadores de stage
        return int(base * get_stat_stage_mod(self.mods[stat]))

    def apply_damage(self, damage, ignore_substitute=False):
        if self.substitute and not ignore_substitute:
            if self.sub_hp >= damage:
                self.sub_hp -= damage
                return False
            else:
                damage_remaining = damage - self.sub_hp
                self.substitute = False
                self.sub_hp = 0
                self.current_hp = clamp(self.current_hp - damage_remaining, 0, self.max_hp)
                if self.current_hp <= 0:
                    self.fainted = True
                return True
        else:
            self.current_hp = clamp(self.current_hp - damage, 0, self.max_hp)
            if self.current_hp <= 0:
                self.fainted = True
            return True

    def heal(self, amount):
        self.current_hp = clamp(self.current_hp + amount, 0, self.max_hp)

    def create_substitute(self):
        if not self.substitute:
            self.substitute = True
            self.sub_hp = max(1, self.max_hp // 4)
            return True
        return False

    def get_hp_percent(self):
        return (self.current_hp / self.max_hp) * 100