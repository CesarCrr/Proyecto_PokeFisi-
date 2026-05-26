"""
minimax_ai.py — IA Nivel 4 (MinimaxAI4).

Hereda MinimaxAI (Nivel 3) y sobreescribe:
  - _evaluate: usa pesos del config en lugar de constantes
  - _rival (RivalModel): usa parámetros del config
  - DEPTH: tomado del config

MinimaxAI (Nivel 3) NO se modifica en absoluto.
"""

import random, copy
from ia.ia_levels  import MinimaxAI, HeuristicAI, RivalModel
from ia.config          import load_config
from ia.memoria_jugador import cargar_perfil, ajustar_rival_model
from batalla.tabla_tipos import get_type_multiplier


def _snap_spe(psnap):
    stages = [0.25,0.28,0.33,0.4,0.5,0.66,1,1.5,2,2.5,3,3.5,4]
    stage  = psnap["mods"].get("spe", 0)
    idx    = max(0, min(12, int(stage) + 6))
    return max(1, int(psnap["spe"] * stages[idx]))


def _snap_damage(atk, dfe, mv):
    from ia.ia_levels import _snap_damage as _sd
    return _sd(atk, dfe, mv)


class ConfiguredRivalModel(RivalModel):
    """RivalModel con parámetros fijos desde config (sin aleatoriedad)."""
    def __init__(self, cfg: dict):
        self.agresividad = cfg["rival_agresividad"]
        self.switch_bias = cfg["rival_switch_bias"]
        self.presion_ko  = cfg["rival_presion_ko"]


class MinimaxAI4(MinimaxAI):
    """
    IA Nivel 4 — cerebro MinimaxAI entrenado con algoritmo genético.
    Lee su config desde data/best_config.json (o usa DEFAULT si no existe).
    """

    def __init__(self, team, enemy_pokemon, enemy_team=None, cfg: dict = None):
        super().__init__(team, enemy_pokemon, enemy_team)
        self.cfg    = cfg or load_config()
        self.DEPTH  = self.cfg["depth"]
        self._rival = ConfiguredRivalModel(self.cfg)
        # Cargar perfil del jugador y ajustar el RivalModel
        self._perfil_jugador = cargar_perfil()
        ajustar_rival_model(self._rival, self._perfil_jugador)

    def _evaluate(self, snap) -> float:
        cfg     = self.cfg
        my_snap = self._my_snap(snap)
        en_snap = self._en_snap(snap)
        score   = 0.0

        my_pct = my_snap["hp"] / my_snap["max_hp"] if my_snap["max_hp"] > 0 else 0
        en_pct = en_snap["hp"] / en_snap["max_hp"] if en_snap["max_hp"] > 0 else 0
        score += (my_pct - en_pct) * cfg["w_hp_activo"]

        my_hp    = sum(p["hp"]     for p in snap["my_team"] if not p["fainted"])
        my_total = sum(p["max_hp"] for p in snap["my_team"] if not p["fainted"]) or 1
        en_hp    = (sum(p["hp"]     for p in snap["en_team"] if not p["fainted"])
                    if snap["en_team"] else en_snap["hp"])
        en_total = (sum(p["max_hp"] for p in snap["en_team"] if not p["fainted"]) or 1
                    if snap["en_team"] else en_snap["max_hp"] or 1)
        score += (my_hp / my_total - en_hp / en_total) * cfg["w_hp_equipo"]

        my_alive = sum(1 for p in snap["my_team"] if not p["fainted"])
        en_alive = (sum(1 for p in snap["en_team"] if not p["fainted"])
                    if snap["en_team"] else (0 if en_snap["fainted"] else 1))
        score += (my_alive - en_alive) * cfg["w_vivos"]

        for tipo in ([my_snap["tipo1"]] + ([my_snap["tipo2"]] if my_snap["tipo2"] else [])):
            mult  = get_type_multiplier(tipo, en_snap["tipo1"], en_snap["tipo2"])
            score += (mult - 1.0) * cfg["w_tipo_atk"]

        for tipo in ([en_snap["tipo1"]] + ([en_snap["tipo2"]] if en_snap["tipo2"] else [])):
            mult  = get_type_multiplier(tipo, my_snap["tipo1"], my_snap["tipo2"])
            score -= (mult - 1.0) * cfg["w_tipo_def"]

        best_dmg = 0.0
        for mv in my_snap["movs"]:
            if mv["pp"] > 0 and mv["poder"] > 0:
                dmg, tm = _snap_damage(my_snap, en_snap, mv)
                if tm > 0:
                    exp = dmg * mv["precision"]
                    if exp > best_dmg:
                        best_dmg = exp
        score += (best_dmg / en_snap["max_hp"]) * cfg["w_mejor_dmg"] if en_snap["max_hp"] > 0 else 0

        status_val = {"burn":25,"poison":20,"toxic":30,
                      "paralyze":20,"sleep":35,"freeze":40,"infectado":15}
        if my_snap["status"]:
            score -= status_val.get(my_snap["status"], 10)
        if en_snap["status"]:
            score += status_val.get(en_snap["status"], 10) * cfg["w_status_enemy"]

        if en_snap["max_hp"] > 0 and best_dmg >= en_snap["hp"]:
            score += cfg["w_ko_bonus"]
        if en_snap["fainted"] or en_snap["hp"] <= 0:
            score += cfg["w_ko_done"]

        my_spe = _snap_spe(my_snap)
        en_spe = _snap_spe(en_snap)
        spd_w  = cfg["w_velocidad"]
        score += spd_w if my_spe > en_spe else (-spd_w if my_spe < en_spe else 0)

        if len(snap["my_team"]) > 1:
            ace     = max(snap["my_team"], key=lambda p: p["max_hp"])
            ace_pct = ace["hp"] / ace["max_hp"] if ace["max_hp"] > 0 else 0
            if ace_pct < cfg["switch_hp_thresh"] and not ace["fainted"]:
                score -= (cfg["switch_hp_thresh"] - ace_pct) * cfg["w_ace_penalty"]

        if my_pct < cfg["switch_hp_thresh"]:
            best_succ = 0.0
            for i, cand in enumerate(snap["my_team"]):
                if i == snap["my_idx"] or cand["fainted"]:
                    continue
                for tipo in ([cand["tipo1"]] + ([cand["tipo2"]] if cand["tipo2"] else [])):
                    mult = get_type_multiplier(tipo, en_snap["tipo1"], en_snap["tipo2"])
                    if mult > best_succ:
                        best_succ = mult
            if best_succ >= cfg["switch_type_mult"]:
                score += (best_succ - 1.0) * cfg["w_successor"]

        if snap["en_team"]:
            en_hp_pct = en_snap["hp"] / en_snap["max_hp"] if en_snap["max_hp"] > 0 else 1
            if en_hp_pct > 0.50:
                for j, cand in enumerate(snap["en_team"]):
                    if j == snap["en_idx"] or cand["fainted"]:
                        continue
                    cand_adv = max(
                        get_type_multiplier(cand["tipo1"], my_snap["tipo1"], my_snap["tipo2"]),
                        get_type_multiplier(cand.get("tipo2") or cand["tipo1"],
                                            my_snap["tipo1"], my_snap["tipo2"])
                    )
                    if cand_adv >= cfg["switch_type_mult"]:
                        score -= 25

        return score