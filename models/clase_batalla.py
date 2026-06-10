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


class BattlePokemon:
    def __init__(self, data, preassigned_moves=None, level=55):
        self.data = data
        self.nombre = data["nombre"]
        self.tipo1 = data["tipo1"]
        self.tipo2 = data["tipo2"]
        self.level = level
        
        self.hp_base = data["hp"]
        self.atk_base = data["atk"]
        self.def_base = data["def_"]
        self.spe_base = data["spe"]
        
        self.max_hp = self._calcular_hp(self.hp_base)
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

        self.mega_evolved = False
        
        self.flying_turns = 0
        self.flying_move = None
        self.flying_active = False
        
        self.outrage_turns = 0
        self.outrage_active = False
        self.outrage_locked = False
        
        self.leech_seed_from = None

    def _calcular_estadistica(self, base):
        # Fórmula: ((2 * Base * Nivel) / 100) + 5
        nivel = self.level
        return int(((2 * base * nivel) / 100) + 5)
    
    def _calcular_hp(self, base):
        nivel = self.level
        return int(((2 * base * nivel) / 100) + nivel + 10)

    def get_effective_stat(self, stat):
        if stat == "evasion":
            return get_evasion_mod(self.mods["evasion"])
        
        if stat == "atk":
            base = self.atk
            if self.status == "burn":
                base = int(base * 0.5)  # Quemado: el Ataque baja a la mitad
        elif stat == "def":
            base = self.defensa
        elif stat == "spe":
            base = self.spe
        else:
            base = self.atk
        
        return int(base * get_stat_stage_mod(self.mods[stat]))

    def apply_damage(self, damage, ignore_substitute=False):
        if self.substitute and not ignore_substitute:
            # El muñeco recibe todo el daño; el Pokemon recibe 0
            self.sub_hp -= damage
            if self.sub_hp <= 0:
                self.substitute = False
                self.sub_hp = 0
            return False
        else:
            self.current_hp = clamp(self.current_hp - damage, 0, self.max_hp)
            if self.current_hp <= 0:
                self.fainted = True
            return True

    def heal(self, amount):
        self.current_hp = clamp(self.current_hp + amount, 0, self.max_hp)

    def create_substitute(self):
        cost = max(1, self.max_hp // 4)
        if not self.substitute and self.current_hp > cost:
            self.current_hp -= cost
            self.substitute = True
            self.sub_hp = cost
            return True
        return False

    def mega_evolve(self):
        if self.mega_evolved or self.nombre != "Pikachu":
            return False
        self.mega_evolved = True
        self.max_hp     += 100
        self.current_hp += 100
        self.atk        += 150
        self.defensa    += 100
        self.spe        += 150
        return True

    def get_hp_percent(self):
        return (self.current_hp / self.max_hp) * 100