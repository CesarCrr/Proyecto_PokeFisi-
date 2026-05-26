import json, os

DEFAULT = {
    "w_hp_activo":     200.0,
    "w_hp_equipo":     150.0,
    "w_vivos":          60.0,
    "w_tipo_atk":       35.0,
    "w_tipo_def":       28.0,
    "w_mejor_dmg":     100.0,
    "w_status_enemy":    0.6,
    "w_ko_bonus":       80.0,
    "w_ko_done":       150.0,
    "w_velocidad":      15.0,
    "w_ace_penalty":   120.0,
    "w_successor":      40.0,
    "depth":             3,
    "rival_agresividad": 0.65,
    "rival_switch_bias": 0.45,
    "rival_presion_ko":  0.70,
    "switch_hp_thresh":  0.25,
    "switch_type_mult":  2.0,
}

_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "best_config.json"
)

def load_config(path: str = _DATA_PATH) -> dict:
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
            cfg = dict(DEFAULT)
            cfg.update({k: data[k] for k in DEFAULT if k in data})
            cfg["depth"] = max(1, min(5, int(round(cfg["depth"]))))
            return cfg
        except Exception:
            pass
    return dict(DEFAULT)

def save_config(cfg: dict, path: str = _DATA_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)

def cfg_to_genome(cfg: dict) -> list:
    keys = [k for k in DEFAULT]
    return [float(cfg.get(k, DEFAULT[k])) for k in keys]

def genome_to_cfg(genome: list) -> dict:
    keys = list(DEFAULT.keys())
    cfg  = {}
    for i, k in enumerate(keys):
        v = genome[i] if i < len(genome) else DEFAULT[k]
        cfg[k] = v
    cfg["depth"] = max(1, min(5, int(round(cfg["depth"]))))
    return cfg

GENOME_KEYS   = list(DEFAULT.keys())
GENOME_BOUNDS = {
    "w_hp_activo":      (50.0,  400.0),
    "w_hp_equipo":      (50.0,  300.0),
    "w_vivos":          (10.0,  150.0),
    "w_tipo_atk":       (5.0,   100.0),
    "w_tipo_def":       (5.0,   100.0),
    "w_mejor_dmg":      (20.0,  250.0),
    "w_status_enemy":   (0.1,   1.5),
    "w_ko_bonus":       (10.0,  200.0),
    "w_ko_done":        (50.0,  300.0),
    "w_velocidad":      (0.0,   50.0),
    "w_ace_penalty":    (20.0,  250.0),
    "w_successor":      (10.0,  120.0),
    "depth":            (1.0,   5.0),
    "rival_agresividad":(0.3,   1.0),
    "rival_switch_bias":(0.1,   0.9),
    "rival_presion_ko": (0.3,   1.0),
    "switch_hp_thresh": (0.1,   0.6),
    "switch_type_mult": (1.0,   4.0),
}
