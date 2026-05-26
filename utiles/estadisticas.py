import json
import os

STATS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "estadisticas_ia.json")

STATS_DEFAULTS = {
    "ia1": {"victorias": 0, "derrotas": 0},
    "ia2": {"victorias": 0, "derrotas": 0},
    "ia3": {"victorias": 0, "derrotas": 0},
    "ia4": {"victorias": 0, "derrotas": 0},
}

def _cargar():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Asegurar que existan todas las claves
            for key in STATS_DEFAULTS:
                if key not in data:
                    data[key] = dict(STATS_DEFAULTS[key])
                for subkey in STATS_DEFAULTS[key]:
                    if subkey not in data[key]:
                        data[key][subkey] = 0
            return data
        except Exception:
            pass
    return {k: dict(v) for k, v in STATS_DEFAULTS.items()}

def _guardar(data):
    try:
        with open(STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def registrar_resultado_pve(ganador, ai_level):
    data = _cargar()
    clave = f"ia{ai_level}"
    if clave not in data:
        data[clave] = {"victorias": 0, "derrotas": 0}
    if ganador == "ai":
        data[clave]["victorias"] += 1
    else:
        data[clave]["derrotas"] += 1
    _guardar(data)

def registrar_resultado_simulation(ganador_color, ai1_level, ai2_level):
    data = _cargar()
    clave1 = f"ia{ai1_level}"
    clave2 = f"ia{ai2_level}"
    for clave in [clave1, clave2]:
        if clave not in data:
            data[clave] = {"victorias": 0, "derrotas": 0}

    if ganador_color == "blue":
        data[clave1]["victorias"] += 1
        data[clave2]["derrotas"] += 1
    else:
        data[clave2]["victorias"] += 1
        data[clave1]["derrotas"] += 1
    _guardar(data)

def obtener_estadisticas():
    return _cargar()

def resetear_estadisticas():
    data = {k: dict(v) for k, v in STATS_DEFAULTS.items()}
    _guardar(data)
