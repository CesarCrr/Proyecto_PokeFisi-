import random
import copy
from batalla.tabla_tipos import get_type_multiplier
from batalla.logica_batalla import calculate_damage

#  sin depender de objetos BattlePokemon reales.

def _get_stat_stage_mod(stage):
    """Replicar get_stat_stage_mod sin importar utiles."""
    clamp = max(-6, min(6, stage))
    table = {-6: 2/8, -5: 2/7, -4: 2/6, -3: 2/5, -2: 2/4, -1: 2/3,
              0: 1.0,
              1: 3/2,  2: 4/2,  3: 5/2,  4: 6/2,  5: 7/2,  6: 8/2}
    return table.get(clamp, 1.0)

def _snap_damage(atk_snap, def_snap, move):
    """
    Calcula daño usando solo datos del snapshot (dicts).
    Devuelve (damage, type_mult).  No toca ningun objeto real.
    """
    if move["poder"] <= 0:
        return 0, 1.0

    atk_base  = atk_snap["atk"]
    def_base  = def_snap["def"]
    atk_mod   = _get_stat_stage_mod(atk_snap["mods"].get("atk", 0))
    def_mod   = _get_stat_stage_mod(def_snap["mods"].get("def", 0))
    atk_stat  = int(atk_base * atk_mod)
    def_stat  = max(1, int(def_base * def_mod))

    type_mult = get_type_multiplier(move["tipo"], def_snap["tipo1"], def_snap["tipo2"])
    if type_mult == 0:
        return 0, 0.0

    base_dmg  = (atk_stat / def_stat) * move["poder"]
    damage    = max(1, int(base_dmg * type_mult))
    if atk_snap["status"] == "burn" and move["categoria"] == "Fisico":
        damage = int(damage * 0.5)
    return damage, type_mult

def _snap_spe(psnap):
    """Velocidad efectiva desde snapshot."""
    return max(1, int(psnap["spe"] * _get_stat_stage_mod(psnap["mods"].get("spe", 0))))

#  IA Nivel 1 — Aleatoria
class RandomAI:
    def __init__(self, team, enemy_pokemon):
        self.team       = team
        self.active_idx = 0
        self.enemy      = enemy_pokemon

    def get_action(self):
        current = self.team[self.active_idx]
        outrage = getattr(current, 'outrage_locked', False)
        flying  = getattr(current, 'flying_active', False)
        if outrage:
            # Forzar movimiento Enfado
            for i, m in enumerate(current.movimientos):
                if m["nombre"] == "Enfado":
                    return ("move", i)
        if flying:
            moves_with_pp = [i for i, m in enumerate(current.movimientos) if m["pp"] > 0]
            if moves_with_pp:
                return ("move", moves_with_pp[0])
        if random.random() < 0.7:
            moves_with_pp = [i for i, m in enumerate(current.movimientos)
                             if m["pp"] > 0]
            if moves_with_pp:
                return ("move", random.choice(moves_with_pp))
        alive = [i for i, p in enumerate(self.team) if not p.fainted and i != self.active_idx]
        if alive:
            return ("switch", random.choice(alive))
        moves_with_pp = [i for i, m in enumerate(current.movimientos)
                         if m["pp"] > 0]
        if moves_with_pp:
            return ("move", random.choice(moves_with_pp))
        return ("move", 0)

#  IA Nivel 2 — Heuristica basica
class HeuristicAI:
    def __init__(self, team, enemy_pokemon):
        self.team       = team
        self.active_idx = 0
        self.enemy      = enemy_pokemon

    def _get_hp_percent(self, pokemon):
        return (pokemon.current_hp / pokemon.max_hp) * 100

    def _should_switch(self, current, enemy):
        hp_percent = self._get_hp_percent(current)
        if hp_percent < 25:
            alive = [i for i, p in enumerate(self.team)
                     if not p.fainted and i != self.active_idx]
            if alive:
                best, best_score = None, -999
                for idx in alive:
                    c = self.team[idx]
                    mult = get_type_multiplier(c.tipo1, enemy.tipo1, enemy.tipo2)
                    if c.tipo2:
                        mult *= get_type_multiplier(c.tipo2, enemy.tipo1, enemy.tipo2)
                    score = mult + self._get_hp_percent(c) / 50
                    if score > best_score:
                        best_score, best = score, idx
                if best is not None and best_score > 0.8:
                    return True, best

        mult_vs_me = get_type_multiplier(enemy.tipo1, current.tipo1, current.tipo2)
        if current.tipo2:
            mult_vs_me *= get_type_multiplier(enemy.tipo1, current.tipo2, None)
        if mult_vs_me >= 2 and hp_percent < 50:
            alive = [i for i, p in enumerate(self.team)
                     if not p.fainted and i != self.active_idx]
            if alive:
                best, best_def = None, 999
                for idx in alive:
                    c = self.team[idx]
                    d = get_type_multiplier(enemy.tipo1, c.tipo1, c.tipo2)
                    if c.tipo2:
                        d *= get_type_multiplier(enemy.tipo1, c.tipo2, None)
                    if d < best_def:
                        best_def, best = d, idx
                if best is not None and best_def < 1:
                    return True, best

        if current.status in ["paralyze", "burn"] and hp_percent < 40:
            alive = [i for i, p in enumerate(self.team)
                     if not p.fainted and i != self.active_idx]
            if alive:
                return True, random.choice(alive)
        return False, None

    def _score_move(self, move, attacker, defender):
        score = 0
        type_mult = get_type_multiplier(move["tipo"], defender.tipo1, defender.tipo2)
        if defender.tipo2:
            type_mult *= get_type_multiplier(move["tipo"], defender.tipo2, None)

        if   type_mult >= 2: score += 100
        elif type_mult == 0: score -= 500
        elif type_mult  < 1: score += 10
        else:                score += 40

        power  = move["poder"] if move["poder"] else 0
        score += power

        if move["poder"] == 0:
            effect = move["efecto"].lower()
            nome   = move["nombre"].lower()
            if "recupera" in effect:
                score += 80 if (attacker.current_hp / attacker.max_hp) < 0.5 else -20
            elif "danza" in nome or "paz mental" in effect:
                score += 45
            elif "mofa" in nome:
                score += 35
            elif "proteccion" in nome:
                score += 20
            elif "drenadoras" in nome and defender.status != "infectado":
                score += 50
            elif "fuego fatuo" in nome and defender.status is None:
                score += 40
            elif "onda trueno" in nome and defender.status is None:
                score += 35
            elif "tox" in effect and defender.status is None:
                score += 45
            else:
                score += 15

        if move["pp"] <= max(1, move["pp_max"] // 4):
            score -= 15
        if "quema"    in move["efecto"].lower() and defender.status == "burn":    score -= 40
        if "paraliza" in move["efecto"].lower() and defender.status == "paralyze": score -= 40
        if "envenena" in move["efecto"].lower() and defender.status in ("poison","toxic"): score -= 40
        if "duerme"   in move["efecto"].lower() and defender.status == "sleep":   score -= 40
        if defender.tipo2:
            if get_type_multiplier(move["tipo"], defender.tipo2, None) >= 2:
                score += 30
        return score

    def _get_best_move(self, current, enemy):
        best_score, best_idx = -999, 0
        for i, move in enumerate(current.movimientos):
            if move["pp"] <= 0:
                continue
            s = self._score_move(move, current, enemy)
            if s > best_score:
                best_score, best_idx = s, i
        if best_score == -999:
            best_pp, best_idx = -1, 0
            for i, m in enumerate(current.movimientos):
                if m["pp"] > best_pp:
                    best_pp, best_idx = m["pp"], i
        return best_idx

    def get_action(self):
        current = self.team[self.active_idx]
        if current.fainted:
            alive = [i for i, p in enumerate(self.team) if not p.fainted]
            if alive:
                return ("switch", random.choice(alive))
            return ("move", 0)
        outrage = getattr(current, 'outrage_locked', False)
        flying  = getattr(current, 'flying_active', False)
        if outrage:
            for i, m in enumerate(current.movimientos):
                if m["nombre"] == "Enfado":
                    return ("move", i)
        if flying:
            moves_with_pp = [i for i, m in enumerate(current.movimientos) if m["pp"] > 0]
            if moves_with_pp:
                return ("move", moves_with_pp[0])
        should_switch, switch_idx = self._should_switch(current, self.enemy)
        if should_switch and switch_idx is not None:
            return ("switch", switch_idx)
        return ("move", self._get_best_move(current, self.enemy))

#
#  Principios de disenio:
#
#  1. ARBOL 100% BASADO EN SNAPSHOTS
#
#     Perfil adaptativo con tres dimensiones:
#
#  3. EVALUACION ESTRATEGICA
#       de un umbral de HP critico.
#       ataque super efectivo el proximo turno.
#
#     snapshots, nunca mutando el estado real.

class RivalModel:
    """
    Perfil del comportamiento esperado del rival.

    En lugar de asumir que el rival siempre jugara optimo (MIN puro),
    RivalModel estima una distribucion de probabilidad sobre sus acciones
    segun tres rasgos: agresividad, tendencia a cambiar y presion de KO.

    Esto permite anticipar cambios defensivos cuando el rival esta en
    desventaja, y cambios ofensivos cuando detecta ventaja de tipo.

    Los rasgos se inicializan con ruido aleatorio para que cada instancia
    de la IA sea unica y menos predecible desde el lado del rival humano.
    """

    def __init__(self):
        # Ruido inicial para variabilidad entre partidas
        self.agresividad  = 0.65 + random.uniform(-0.15, 0.15)  # 0=pasivo, 1=agresivo
        self.switch_bias  = 0.45 + random.uniform(-0.10, 0.10)  # prob base de cambiar
        self.presion_ko   = 0.70 + random.uniform(-0.10, 0.10)  # prioridad al KO

    def accion_weights(self, en_snap, my_snap, enemy_movs, enemy_team_snaps, en_idx):
        """
        Devuelve lista de (peso, action) para las acciones del rival.
        Los pesos NO suman 1; se normalizan al usarlos.

        Logica:
          - Si el rival esta en desventaja de tipo severa  => bonus a switch
          - Si puede hacer KO este turno                   => bonus a ataque
          - Si tiene el activo muy bajo de HP              => bonus a switch
          - Si hay un cambio con ventaja de tipo clara     => bonus a ese cambio
        """
        results = []

        best_atk_dmg = 0
        for i, mv in enumerate(enemy_movs):
            if mv["pp"] <= 0:
                continue
            dmg, tm = _snap_damage(en_snap, my_snap, mv)
            if tm == 0:
                w = 0.01
            elif mv["poder"] > 0:
                expected = dmg * mv["precision"]
                # Bonus por presion de KO
                ko_bonus  = self.presion_ko * 2.0 if dmg >= my_snap["hp"] else 0
                w = self.agresividad * (expected / max(my_snap["max_hp"], 1) * 3 + ko_bonus)
                if expected > best_atk_dmg:
                    best_atk_dmg = expected
            else:
                w = (1 - self.agresividad) * 0.4
            results.append((max(0.01, w), ("move", i)))

        if enemy_team_snaps:
            en_hp_pct  = en_snap["hp"] / en_snap["max_hp"] if en_snap["max_hp"] > 0 else 1.0
            type_dis = get_type_multiplier(my_snap["tipo1"], en_snap["tipo1"], en_snap["tipo2"])

            for j, cand_snap in enumerate(enemy_team_snaps):
                if j == en_idx or cand_snap["fainted"] or cand_snap["hp"] <= 0:
                    continue

                cand_adv = 0.0
                for tipo in ([cand_snap["tipo1"]] +
                             ([cand_snap["tipo2"]] if cand_snap["tipo2"] else [])):
                    cand_adv += get_type_multiplier(tipo, my_snap["tipo1"], my_snap["tipo2"])

                cand_def = get_type_multiplier(my_snap["tipo1"],
                                               cand_snap["tipo1"], cand_snap["tipo2"])
                cand_hp_pct = cand_snap["hp"] / cand_snap["max_hp"] if cand_snap["max_hp"] > 0 else 0

                # Peso base del cambio
                w  = self.switch_bias
                w *= (cand_adv / 2.0)
                w *= (1.0 / max(cand_def, 0.25))
                w *= cand_hp_pct

                if en_hp_pct < 0.30:
                    w *= 1.8
                if type_dis >= 2:
                    w *= 1.6

                results.append((max(0.01, w), ("switch_enemy", j)))

        if not results:
            results.append((1.0, ("move", 0)))
        return results

class MinimaxAI:
    """
    IA Nivel 3: Expectiminimax con arbol 100% basado en snapshots.

    Ver cabecera del modulo para descripcion completa del disenio.
    """

    DEPTH     = 3
    CRIT_PROB = 0.0625
    CRIT_MULT = 1.5

    def __init__(self, team, enemy_pokemon, enemy_team=None):
        self.team             = team
        self.active_idx       = 0
        self.enemy            = enemy_pokemon
        self.enemy_team       = enemy_team or []
        self.enemy_active_idx = 0
        self._heuristic       = HeuristicAI(team, enemy_pokemon)
        self._rival           = RivalModel()

    #

    def _make_psnap(self, p):
        """Snapshot de un BattlePokemon."""
        return {
            "hp":      p.current_hp,
            "max_hp":  p.max_hp,
            "atk":     p.atk,
            "def":     p.defensa,
            "spe":     p.spe,
            "tipo1":   p.tipo1,
            "tipo2":   p.tipo2,
            "status":  p.status,
            "fainted": p.fainted,
            "mods":    dict(p.mods),
            "movs":    [dict(m) for m in p.movimientos],
        }

    def _snapshot(self):
        return {
            "my_team":  [self._make_psnap(p) for p in self.team],
            "en_team":  [self._make_psnap(p) for p in self.enemy_team]
                        if self.enemy_team else [],
            "my_idx":   self.active_idx,
            "en_idx":   self.enemy_active_idx,
        }

    def _restore(self, snap):
        for i, ps in enumerate(snap["my_team"]):
            if i < len(self.team):
                p = self.team[i]
                p.current_hp = ps["hp"]
                p.fainted    = ps["fainted"]
                p.status     = ps["status"]
                p.mods       = dict(ps["mods"])
        self.active_idx = snap["my_idx"]

    #  ACCESORES SEGUROS sobre snapshots

    def _my_snap(self, snap):
        return snap["my_team"][snap["my_idx"]]

    def _en_snap(self, snap):
        if snap["en_team"]:
            return snap["en_team"][snap["en_idx"]]
        return self._make_psnap(self.enemy)

    #  EVALUACION ESTRATEGICA

    def _evaluate(self, snap):
        my_snap = self._my_snap(snap)
        en_snap = self._en_snap(snap)
        score   = 0.0

        # 1. HP relativo del activo
        my_pct = my_snap["hp"] / my_snap["max_hp"] if my_snap["max_hp"] > 0 else 0
        en_pct = en_snap["hp"] / en_snap["max_hp"] if en_snap["max_hp"] > 0 else 0
        score += (my_pct - en_pct) * 200

        # 2. HP total del equipo
        my_team_hp    = sum(p["hp"] for p in snap["my_team"] if not p["fainted"])
        my_team_total = sum(p["max_hp"] for p in snap["my_team"] if not p["fainted"]) or 1
        en_team_hp    = sum(p["hp"] for p in snap["en_team"] if not p["fainted"]) if snap["en_team"] else en_snap["hp"]
        en_team_total = sum(p["max_hp"] for p in snap["en_team"] if not p["fainted"]) or 1 if snap["en_team"] else en_snap["max_hp"] or 1
        score += (my_team_hp / my_team_total - en_team_hp / en_team_total) * 150

        # 3. Numero de Pokemon vivos
        my_alive = sum(1 for p in snap["my_team"] if not p["fainted"])
        en_alive = sum(1 for p in snap["en_team"] if not p["fainted"]) if snap["en_team"] else (0 if en_snap["fainted"] else 1)
        score += (my_alive - en_alive) * 60

        for tipo in ([my_snap["tipo1"]] + ([my_snap["tipo2"]] if my_snap["tipo2"] else [])):
            mult = get_type_multiplier(tipo, en_snap["tipo1"], en_snap["tipo2"])
            score += (mult - 1.0) * 35

        # 5. Resistencia defensiva del activo propio
        for tipo in ([en_snap["tipo1"]] + ([en_snap["tipo2"]] if en_snap["tipo2"] else [])):
            def_mult = get_type_multiplier(tipo, my_snap["tipo1"], my_snap["tipo2"])
            score -= (def_mult - 1.0) * 28  # castigo por permanecer en desventaja

        best_dmg = 0.0
        for mv in my_snap["movs"]:
            if mv["pp"] > 0 and mv["poder"] > 0:
                dmg, tm = _snap_damage(my_snap, en_snap, mv)
                if tm > 0:
                    exp = dmg * mv["precision"]
                    if exp > best_dmg:
                        best_dmg = exp
        score += (best_dmg / en_snap["max_hp"]) * 100 if en_snap["max_hp"] > 0 else 0

        # 7. Estados de alteracion
        status_val = {"burn": 25, "poison": 20, "toxic": 30,
                      "paralyze": 20, "sleep": 35, "freeze": 40, "infectado": 15}
        if my_snap["status"]:
            score -= status_val.get(my_snap["status"], 10)
        if en_snap["status"]:
            score += status_val.get(en_snap["status"], 10) * 0.6

        # 8. Amenaza de KO inmediato
        if en_snap["max_hp"] > 0 and best_dmg >= en_snap["hp"]:
            score += 80
        if en_snap["fainted"] or en_snap["hp"] <= 0:
            score += 150

        # 9. Ventaja de velocidad
        my_spe = _snap_spe(my_snap)
        en_spe = _snap_spe(en_snap)
        score += 15 if my_spe > en_spe else (-15 if my_spe < en_spe else 0)

        if len(snap["my_team"]) > 1:
            ace = max(snap["my_team"], key=lambda p: p["max_hp"])
            ace_pct = ace["hp"] / ace["max_hp"] if ace["max_hp"] > 0 else 0
            if ace_pct < 0.40 and not ace["fainted"]:
                score -= (0.40 - ace_pct) * 120  # penalizacion progresiva

        if my_pct < 0.25:
            best_successor = 0.0
            for i, cand in enumerate(snap["my_team"]):
                if i == snap["my_idx"] or cand["fainted"]:
                    continue
                for tipo in ([cand["tipo1"]] + ([cand["tipo2"]] if cand["tipo2"] else [])):
                    mult = get_type_multiplier(tipo, en_snap["tipo1"], en_snap["tipo2"])
                    if mult > best_successor:
                        best_successor = mult
            if best_successor >= 2.0:
                score += (best_successor - 1.0) * 40

        if snap["en_team"]:
            en_hp_pct = en_snap["hp"] / en_snap["max_hp"] if en_snap["max_hp"] > 0 else 1
            if en_hp_pct > 0.50:
                for j, cand in enumerate(snap["en_team"]):
                    if j == snap["en_idx"] or cand["fainted"]:
                        continue
                    cand_adv = max(
                        get_type_multiplier(cand["tipo1"], my_snap["tipo1"], my_snap["tipo2"]),
                        get_type_multiplier(cand["tipo2"] or cand["tipo1"],
                                            my_snap["tipo1"], my_snap["tipo2"])
                    )
                    if cand_adv >= 2.0:
                        score -= 25

        return score

    #  MOVE ORDERING sobre snapshots

    def _score_move_snap(self, mv, atk_snap, def_snap):
        """Score rapido de un movimiento usando snapshots."""
        if mv["pp"] <= 0:
            return -9999
        dmg, tm = _snap_damage(atk_snap, def_snap, mv)
        if tm == 0:
            return -9999
        if mv["poder"] > 0:
            return dmg * mv["precision"]
        # Movimiento de estado: score heuristico simplificado
        eff  = mv["efecto"].lower()
        nome = mv["nombre"].lower()
        s    = 15
        if "recupera" in eff:
            s = 70 if (atk_snap["hp"] / atk_snap["max_hp"]) < 0.5 else -10
        elif "danza" in nome or "paz" in eff:
            s = 40
        elif "tox" in eff and def_snap["status"] is None:
            s = 45
        elif "fuego fatuo" in nome and def_snap["status"] is None:
            s = 38
        return s

    def _score_switch_snap(self, cand_snap, en_snap):
        """Score de traer a cand_snap contra en_snap."""
        if cand_snap["fainted"] or cand_snap["hp"] <= 0:
            return -9999
        hp_pct   = cand_snap["hp"] / cand_snap["max_hp"] if cand_snap["max_hp"] > 0 else 0
        type_adv = 0.0
        for tipo in ([cand_snap["tipo1"]] + ([cand_snap["tipo2"]] if cand_snap["tipo2"] else [])):
            type_adv += (get_type_multiplier(tipo, en_snap["tipo1"], en_snap["tipo2"]) - 1.0) * 40
        for tipo in ([en_snap["tipo1"]] + ([en_snap["tipo2"]] if en_snap["tipo2"] else [])):
            type_adv -= (get_type_multiplier(tipo, cand_snap["tipo1"], cand_snap["tipo2"]) - 1.0) * 25
        return hp_pct * 100 + type_adv

    def _my_actions_ordered(self, snap):
        """Top-3 movimientos + Top-2 cambios propios, desde el snapshot."""
        my_snap = self._my_snap(snap)
        en_snap = self._en_snap(snap)

        move_scores = []
        for i, mv in enumerate(my_snap["movs"]):
            if mv["pp"] > 0:
                s = self._score_move_snap(mv, my_snap, en_snap)
                move_scores.append((s, ("move", i)))
        move_scores.sort(key=lambda x: x[0], reverse=True)
        best_moves = [a for _, a in move_scores[:3]]

        switch_scores = []
        for i, cand in enumerate(snap["my_team"]):
            if i != snap["my_idx"] and not cand["fainted"]:
                s = self._score_switch_snap(cand, en_snap)
                switch_scores.append((s, ("switch", i)))
        switch_scores.sort(key=lambda x: x[0], reverse=True)
        best_switches = [a for _, a in switch_scores[:2]]

        actions = best_moves + best_switches
        return actions if actions else [("move", 0)]

    def _apply_my_action(self, action, snap, crit=False, miss=False):
        """Devuelve snapshot nuevo tras la accion de la IA."""
        new = copy.deepcopy(snap)

        if action[0] == "switch":
            new["my_idx"] = action[1]
            return new

        move_idx = action[1]
        my_snap  = new["my_team"][new["my_idx"]]
        en_snap  = new["en_team"][new["en_idx"]] if new["en_team"] else None

        if en_snap is None:
            return new

        if move_idx >= len(my_snap["movs"]):
            return new

        mv = my_snap["movs"][move_idx]
        if not miss and mv["poder"] > 0:
            dmg, tm = _snap_damage(my_snap, en_snap, mv)
            if tm > 0:
                if crit:
                    dmg = int(dmg * self.CRIT_MULT)
                en_snap["hp"]      = max(0, en_snap["hp"] - dmg)
                en_snap["fainted"] = en_snap["hp"] <= 0
        return new

    def _apply_enemy_action(self, action, snap, crit=False, miss=False):
        """Devuelve snapshot nuevo tras la accion del rival."""
        new = copy.deepcopy(snap)

        if action[0] == "switch_enemy":
            new["en_idx"] = action[1]
            return new

        move_idx = action[1]
        en_snap  = new["en_team"][new["en_idx"]] if new["en_team"] else None
        my_snap  = new["my_team"][new["my_idx"]]

        if en_snap is None:
            return new

        if move_idx >= len(en_snap["movs"]):
            return new

        mv = en_snap["movs"][move_idx]
        if not miss and mv["poder"] > 0:
            dmg, tm = _snap_damage(en_snap, my_snap, mv)
            if tm > 0:
                if crit:
                    dmg = int(dmg * self.CRIT_MULT)
                my_snap["hp"]      = max(0, my_snap["hp"] - dmg)
                my_snap["fainted"] = my_snap["hp"] <= 0
        return new

    #  EXPECTIMINIMAX con poda alfa-beta
    #
    #  Flujo de nodos por turno completo:
    #

    def _avg_precision(self, psnap):
        atk_movs = [m for m in psnap["movs"] if m["pp"] > 0 and m["poder"] > 0]
        if not atk_movs:
            return 1.0
        return sum(m["precision"] for m in atk_movs) / len(atk_movs)

    def _terminal(self, snap):
        my_alive = any(not p["fainted"] for p in snap["my_team"])
        en_alive = any(not p["fainted"] for p in snap["en_team"]) if snap["en_team"] else True
        return not my_alive or not en_alive

    def _expectiminimax(self, depth, alpha, beta, node_type, snap):
        # Caso base
        if depth == 0 or self._terminal(snap):
            return self._evaluate(snap)

        if node_type == "max":
            my_snap = self._my_snap(snap)
            skip_p  = 0.25 if my_snap["status"] == "paralyze" else 0.0
            max_val = float("-inf")

            for action in self._my_actions_ordered(snap):
                child = self._apply_my_action(action, snap)
                val   = self._expectiminimax(depth - 1, alpha, beta, "chance_my", child)
                if val > max_val:
                    max_val = val
                alpha = max(alpha, val)
                if beta <= alpha:
                    break

            if skip_p > 0 and max_val != float("-inf"):
                val_skip = self._expectiminimax(depth - 1, alpha, beta, "min", snap)
                max_val  = (1.0 - skip_p) * max_val + skip_p * val_skip

            return max_val

        elif node_type == "chance_my":
            val_normal = self._expectiminimax(depth - 1, alpha, beta, "min", snap)

            en_snap    = self._en_snap(snap)
            crit_extra = max(1, int(en_snap["max_hp"] * 0.08))

            snap_crit = copy.deepcopy(snap)
            eptr      = snap_crit["en_team"][snap_crit["en_idx"]] if snap_crit["en_team"] else None
            if eptr:
                eptr["hp"]      = max(0, eptr["hp"] - crit_extra)
                eptr["fainted"] = eptr["hp"] <= 0
            val_crit = self._expectiminimax(depth - 1, alpha, beta, "min", snap_crit)

            snap_miss = copy.deepcopy(snap)
            eptr2     = snap_miss["en_team"][snap_miss["en_idx"]] if snap_miss["en_team"] else None
            if eptr2:
                eptr2["hp"]      = min(en_snap["max_hp"], eptr2["hp"] + crit_extra * 5)
                eptr2["fainted"] = False
            val_miss = self._expectiminimax(depth - 1, alpha, beta, "min", snap_miss)

            my_snap = self._my_snap(snap)
            prec    = self._avg_precision(my_snap)
            return (prec * (1 - self.CRIT_PROB) * val_normal
                  + prec * self.CRIT_PROB       * val_crit
                  + (1 - prec)                  * val_miss)

        elif node_type == "min":
            en_snap  = self._en_snap(snap)
            my_snap  = self._my_snap(snap)
            skip_p   = 0.25 if en_snap["status"] == "paralyze" else 0.0

            # Obtener pesos del RivalModel
            weights_actions = self._rival.accion_weights(
                en_snap, my_snap,
                en_snap["movs"],
                snap["en_team"],
                snap["en_idx"]
            )

            weights_actions.sort(key=lambda x: x[0], reverse=True)
            total_w = sum(w for w, _ in weights_actions)

            # con 30% ponderado por el modelo.
            min_pure = float("inf")
            weighted_val = 0.0

            for w, action in weights_actions:
                child = self._apply_enemy_action(action, snap)
                val   = self._expectiminimax(depth - 1, alpha, beta, "chance_en", child)

                if val < min_pure:
                    min_pure = val
                weighted_val += (w / total_w) * val

                beta = min(beta, val)
                if beta <= alpha:
                    break

            if min_pure == float("inf"):
                return self._evaluate(snap)

            min_val = 0.70 * min_pure + 0.30 * weighted_val

            # Paralizacion del rival
            if skip_p > 0:
                val_skip = self._expectiminimax(depth - 1, alpha, beta, "max", snap)
                min_val  = (1.0 - skip_p) * min_val + skip_p * val_skip

            return min_val

        elif node_type == "chance_en":
            val_normal = self._expectiminimax(depth - 1, alpha, beta, "max", snap)

            my_snap    = self._my_snap(snap)
            crit_extra = max(1, int(my_snap["max_hp"] * 0.08))

            snap_crit = copy.deepcopy(snap)
            mptr      = snap_crit["my_team"][snap_crit["my_idx"]]
            mptr["hp"]      = max(0, mptr["hp"] - crit_extra)
            mptr["fainted"] = mptr["hp"] <= 0
            val_crit  = self._expectiminimax(depth - 1, alpha, beta, "max", snap_crit)

            snap_miss = copy.deepcopy(snap)
            mptr2     = snap_miss["my_team"][snap_miss["my_idx"]]
            mptr2["hp"]      = min(my_snap["max_hp"], mptr2["hp"] + crit_extra * 5)
            mptr2["fainted"] = False
            val_miss  = self._expectiminimax(depth - 1, alpha, beta, "max", snap_miss)

            en_snap = self._en_snap(snap)
            prec    = self._avg_precision(en_snap)
            return (prec * (1 - self.CRIT_PROB) * val_normal
                  + prec * self.CRIT_PROB       * val_crit
                  + (1 - prec)                  * val_miss)

        # Fallback
        return self._evaluate(snap)

    #  ENTRADA PRINCIPAL

    def get_action(self):
        current = self.team[self.active_idx]

        outrage = getattr(current, 'outrage_locked', False)
        flying  = getattr(current, 'flying_active', False)
        if outrage:
            for i, m in enumerate(current.movimientos):
                if m["nombre"] == "Enfado":
                    return ("move", i)
        if flying:
            moves_with_pp = [i for i, m in enumerate(current.movimientos) if m["pp"] > 0]
            if moves_with_pp:
                return ("move", moves_with_pp[0])

        if current.fainted or current.current_hp <= 0:
            snap = self._snapshot()
            en_snap = self._en_snap(snap)
            alive = [
                (i, self._score_switch_snap(snap["my_team"][i], en_snap))
                for i, p in enumerate(snap["my_team"])
                if not p["fainted"]
            ]
            if alive:
                alive.sort(key=lambda x: x[1], reverse=True)
                return ("switch", alive[0][0])
            return ("move", 0)

        # Transicion: rival caido, usar heuristica
        if self.enemy.fainted or self.enemy.current_hp <= 0:
            self._heuristic.team       = self.team
            self._heuristic.active_idx = self.active_idx
            self._heuristic.enemy      = self.enemy
            return self._heuristic.get_action()

        initial_snap = self._snapshot()
        best_action  = None
        best_val     = float("-inf")
        alpha        = float("-inf")
        beta         = float("inf")

        for action in self._my_actions_ordered(initial_snap):
            child = self._apply_my_action(action, initial_snap)
            val   = self._expectiminimax(
                self.DEPTH - 1, alpha, beta, "chance_my", child)
            if val > best_val:
                best_val    = val
                best_action = action
            alpha = max(alpha, val)

        self._restore(initial_snap)

        if best_action is None:
            self._heuristic.team       = self.team
            self._heuristic.active_idx = self.active_idx
            self._heuristic.enemy      = self.enemy
            return self._heuristic.get_action()

        return best_action