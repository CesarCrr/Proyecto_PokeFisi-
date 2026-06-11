import json, os, math

MEMORIA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "memoria", "jugador.json"
)
MAX_BATALLAS = 20

PERFIL_VACIO = {
    "total_batallas": 0,
    "total_turnos":   0,
    "usa_ataques":    0,
    "usa_cambios":    0,
    "usa_estado":     0,   
    "cambios_por_ventaja_tipo": 0,
    "victorias_jugador": 0,
    "agresividad":    0.5, 
    "tipo_jugador":   "equilibrado",  
    "historial":      [],  
}

class BattleTracker:

    def __init__(self):
        self.reset()

    def reset(self):
        self.turnos       = 0
        self.ataques      = 0
        self.cambios      = 0
        self.uso_estado   = 0  
        self.cambios_ventaja = 0  

    def registrar_ataque(self, move: dict, player_pokemon, enemy_pokemon):
        self.turnos  += 1
        if move.get("poder", 0) > 0:
            self.ataques += 1
        else:
            self.uso_estado += 1

    def registrar_cambio(self, nuevo_pokemon, enemy_pokemon):
        self.cambios += 1
        self.turnos  += 1
        try:
            from batalla.tabla_tipos import get_type_multiplier
            mult = get_type_multiplier(
                nuevo_pokemon.tipo1,
                enemy_pokemon.tipo1,
                getattr(enemy_pokemon, "tipo2", None)
            )
            if mult >= 2.0:
                self.cambios_ventaja += 1
        except Exception:
            pass

    def resumen(self) -> dict:
        t = max(self.turnos, 1)
        return {
            "turnos":               self.turnos,
            "usa_ataques":          self.ataques,
            "usa_cambios":          self.cambios,
            "usa_estado":           self.uso_estado,
            "cambios_por_ventaja":  self.cambios_ventaja,
            "ratio_ataque":         round(self.ataques / t, 3),
            "ratio_cambio":         round(self.cambios / t, 3),
        }

def cargar_perfil() -> dict:
    if os.path.exists(MEMORIA_PATH):
        try:
            with open(MEMORIA_PATH, "r") as f:
                data = json.load(f)
            perfil = dict(PERFIL_VACIO)
            perfil.update(data)
            return perfil
        except Exception:
            pass
    return dict(PERFIL_VACIO)


def guardar_perfil(perfil: dict):
    os.makedirs(os.path.dirname(MEMORIA_PATH), exist_ok=True)
    with open(MEMORIA_PATH, "w") as f:
        json.dump(perfil, f, indent=2, ensure_ascii=False)

def actualizar_perfil(tracker: BattleTracker, jugador_gano: bool) -> dict:

    perfil = cargar_perfil()
    res    = tracker.resumen()
    # Agregar al historial
    entrada = {
        "turnos":               res["turnos"],
        "usa_ataques":          res.get("usa_ataques", 0),
        "usa_cambios":          res.get("usa_cambios", 0),
        "uso_estado":           res.get("uso_estado", res.get("usa_estado", 0)),
        "cambios_por_ventaja":  res.get("cambios_por_ventaja", res.get("cambios_por_ventaja_tipo", 0)),
        "gano": jugador_gano,
    }
    perfil["historial"].append(entrada)
    if len(perfil["historial"]) > MAX_BATALLAS:
        perfil["historial"] = perfil["historial"][-MAX_BATALLAS:]

    n = len(perfil["historial"])
    pesos = [math.exp(0.15 * i) for i in range(n)]
    total_peso = sum(pesos)

    wa = sum(h.get("usa_ataques", 0) / max(h["turnos"],1) * pesos[i]
             for i, h in enumerate(perfil["historial"])) / total_peso
    wc = sum(h.get("usa_cambios", 0) / max(h["turnos"],1) * pesos[i]
             for i, h in enumerate(perfil["historial"])) / total_peso
    we = sum(h.get("usa_estado", h.get("uso_estado", 0)) / max(h["turnos"],1) * pesos[i]
             for i, h in enumerate(perfil["historial"])) / total_peso

    perfil["total_batallas"] += 1
    perfil["total_turnos"]   += res["turnos"]
    perfil["usa_ataques"]    += res["usa_ataques"]
    perfil["usa_cambios"]    += res["usa_cambios"]
    perfil["usa_estado"]     += res.get("uso_estado", res.get("usa_estado", 0))
    perfil["cambios_por_ventaja_tipo"] += res["cambios_por_ventaja"]
    if jugador_gano:
        perfil["victorias_jugador"] += 1

    perfil["agresividad"] = round(wa / max(wa + wc + we, 0.001), 3)

    if wa > 0.70:
        perfil["tipo_jugador"] = "ofensivo"
    elif wc > 0.25:
        perfil["tipo_jugador"] = "estratégico" if we > 0.10 else "defensivo"
    elif we > 0.20:
        perfil["tipo_jugador"] = "estratégico"
    else:
        perfil["tipo_jugador"] = "equilibrado"

    guardar_perfil(perfil)
    return perfil


#Ajuste del RivalModel en MinimaxAI4

def ajustar_rival_model(rival_model, perfil: dict):
    if not perfil or perfil["total_batallas"] == 0:
        return 

    confianza = min(1.0, perfil["total_batallas"] / 5.0) 
    ag  = perfil["agresividad"]
    tip = perfil["tipo_jugador"]

    base_ag  = rival_model.agresividad
    base_ko  = rival_model.presion_ko
    base_sw  = rival_model.switch_bias

    if tip == "ofensivo":
        nuevo_ko  = base_ko  + 0.15 * confianza
        nuevo_ag  = base_ag  + 0.10 * confianza
        nuevo_sw  = base_sw  - 0.05 * confianza
    elif tip == "defensivo":
        nuevo_ko  = base_ko  - 0.05 * confianza
        nuevo_ag  = base_ag  - 0.05 * confianza
        nuevo_sw  = base_sw  + 0.15 * confianza
    elif tip == "estratégico":
        nuevo_ko  = base_ko  + 0.05 * confianza
        nuevo_ag  = base_ag  - 0.05 * confianza
        nuevo_sw  = base_sw  + 0.10 * confianza
    else:  # equilibrado
        nuevo_ko  = base_ko
        nuevo_ag  = base_ag
        nuevo_sw  = base_sw

    rival_model.agresividad = max(0.30, min(1.0, nuevo_ag))
    rival_model.presion_ko  = max(0.30, min(1.0, nuevo_ko))
    rival_model.switch_bias = max(0.10, min(0.90, nuevo_sw))