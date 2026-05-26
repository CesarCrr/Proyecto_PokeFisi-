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
    "usa_estado":     0,   # movimientos sin daño (buff/debuff/estado)
    "cambios_por_ventaja_tipo": 0,
    "victorias_jugador": 0,
    "agresividad":    0.5, # 0=pasivo, 1=muy agresivo
    "tipo_jugador":   "equilibrado",  # ofensivo | defensivo | equilibrado | estratégico
    "historial":      [],  # últimas MAX_BATALLAS batallas resumidas
}


# ── Tracker de una batalla ────────────────────────────────────────────────

class BattleTracker:
    """Registra las acciones del jugador durante una batalla."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.turnos       = 0
        self.ataques      = 0
        self.cambios      = 0
        self.uso_estado   = 0  # movimientos poder==0
        self.cambios_ventaja = 0  # cambios donde el entrante tiene ventaja de tipo

    def registrar_ataque(self, move: dict, player_pokemon, enemy_pokemon):
        """Llamar cuando el jugador usa un movimiento."""
        self.turnos  += 1
        if move.get("poder", 0) > 0:
            self.ataques += 1
        else:
            self.uso_estado += 1

    def registrar_cambio(self, nuevo_pokemon, enemy_pokemon):
        """Llamar cuando el jugador cambia de Pokémon."""
        self.cambios += 1
        self.turnos  += 1
        # Detectar si el cambio aprovecha ventaja de tipo
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


# ── Carga y guardado ─────────────────────────────────────────────────────

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


# ── Actualización del perfil tras una batalla ────────────────────────────

def actualizar_perfil(tracker: BattleTracker, jugador_gano: bool) -> dict:
    """
    Fusiona el resumen de la batalla con el perfil acumulado.
    Devuelve el perfil actualizado.
    """
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

    # Acumular globales (ponderado: últimas batallas pesan más)
    n = len(perfil["historial"])
    # Pesos exponenciales: la batalla más reciente pesa más
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

    # Agresividad: ratio de ataques directos vs total de acciones
    perfil["agresividad"] = round(wa / max(wa + wc + we, 0.001), 3)

    # Clasificar tipo de jugador
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


# ── Ajuste del RivalModel en MinimaxAI4 ─────────────────────────────────

def ajustar_rival_model(rival_model, perfil: dict):
    """
    Ajusta los parámetros del RivalModel de MinimaxAI4
    según el perfil del jugador. Cuantas más batallas hay,
    más confianza tiene el ajuste.
    """
    if not perfil or perfil["total_batallas"] == 0:
        return  # sin datos, no ajustar

    confianza = min(1.0, perfil["total_batallas"] / 5.0)  # máx confianza a 5 batallas
    ag  = perfil["agresividad"]
    tip = perfil["tipo_jugador"]

    # Ajustar agresividad: si el jugador es muy agresivo, la IA
    # sube su presión_ko para anticipar ataques directos
    base_ag  = rival_model.agresividad
    base_ko  = rival_model.presion_ko
    base_sw  = rival_model.switch_bias

    if tip == "ofensivo":
        # Jugador ataca mucho → IA prioriza KO antes de que el jugador lo haga
        nuevo_ko  = base_ko  + 0.15 * confianza
        nuevo_ag  = base_ag  + 0.10 * confianza
        nuevo_sw  = base_sw  - 0.05 * confianza
    elif tip == "defensivo":
        # Jugador cambia mucho → IA penaliza más los cambios del rival
        nuevo_ko  = base_ko  - 0.05 * confianza
        nuevo_ag  = base_ag  - 0.05 * confianza
        nuevo_sw  = base_sw  + 0.15 * confianza
    elif tip == "estratégico":
        # Jugador mezcla estado + cambios → IA más cautelosa
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