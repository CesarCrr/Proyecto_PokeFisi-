import random, copy
from batalla.logica_batalla import resolve_turn
from datos.datos_pokemon    import POKEMON_DB
from models.clase_batalla   import BattlePokemon

_HAZARDS = {"stealth_rock": False, "spikes": 0, "toxic_spikes": 0}

def _random_team(size: int = 6) -> list:
    chosen = random.sample(POKEMON_DB, min(size, len(POKEMON_DB)))
    return [BattlePokemon(p) for p in chosen]

def _alive(team):
    return [i for i, p in enumerate(team) if not p.fainted]

def _hp_frac(team):
    total   = sum(p.max_hp for p in team)
    current = sum(p.current_hp for p in team if not p.fainted)
    return current / total if total > 0 else 0.0

def _sync(ia, team, active_idx, enemy, enemy_team, enemy_active_idx):
    ia.team             = team
    ia.active_idx       = active_idx
    ia.enemy            = enemy
    if hasattr(ia, "enemy_team"):
        ia.enemy_team       = enemy_team
    if hasattr(ia, "enemy_active_idx"):
        ia.enemy_active_idx = enemy_active_idx

def simulate_battle(ia_a, ia_b, team_a: list, team_b: list,
                    max_turns: int = 80) -> dict:
    team_a = [copy.deepcopy(p) for p in team_a]
    team_b = [copy.deepcopy(p) for p in team_b]
    ha     = copy.deepcopy(_HAZARDS)
    hb     = copy.deepcopy(_HAZARDS)
    ai_a   = 0 
    ai_b   = 0  

    for turn in range(max_turns):
        la = _alive(team_a)
        lb = _alive(team_b)
        if not la or not lb:
            break
        if team_a[ai_a].fainted:
            ai_a = la[0]
        if team_b[ai_b].fainted:
            ai_b = lb[0]
        pa = team_a[ai_a]
        pb = team_b[ai_b]
        _sync(ia_a, team_a, ai_a, pb, team_b, ai_b)
        action_a = ia_a.get_action()
        _sync(ia_b, team_b, ai_b, pa, team_a, ai_a)
        action_b = ia_b.get_action()
        a_switch   = action_a[0] == "switch"
        b_switch   = action_b[0] == "switch"
        a_move_idx = None if a_switch else action_a[1]
        b_move_idx = None if b_switch else action_b[1]
        a_new_idx  = action_a[1] if a_switch else None
        b_new_idx  = action_b[1] if b_switch else None

        log = []
        resolve_turn(
            player_pokemon               = pa,
            ai_pokemon                   = pb,
            player_move_idx              = a_move_idx,
            ai_move_idx                  = b_move_idx,
            player_switch                = a_switch,
            ai_switch                    = b_switch,
            player_new_idx               = a_new_idx,
            ai_new_idx                   = b_new_idx,
            player_force_switch_pokemon_idx = None,
            player_team                  = team_a,
            ai_team                      = team_b,
            player_active_idx            = ai_a,
            ai_active_idx                = ai_b,
            log_lines                    = log,
            player_hazards               = ha,
            ai_hazards                   = hb,
        )

        if a_switch and a_new_idx is not None:
            ai_a = a_new_idx
        if b_switch and b_new_idx is not None:
            ai_b = b_new_idx

        la2 = _alive(team_a)
        lb2 = _alive(team_b)
        if not la2 or not lb2:
            break
        if team_a[ai_a].fainted and la2:
            ai_a = la2[0]
        if team_b[ai_b].fainted and lb2:
            ai_b = lb2[0]

    la = _alive(team_a)
    lb = _alive(team_b)

    if   la and not lb: winner = "a"
    elif lb and not la: winner = "b"
    else:
        winner = "a" if _hp_frac(team_a) >= _hp_frac(team_b) else "b"

    return {
        "winner": winner,
        "turns":  turn + 1,
        "hp_a":   _hp_frac(team_a),
        "hp_b":   _hp_frac(team_b),
    }


def run_matches(ia_a, ia_b, n: int = 10, team_size: int = 6) -> dict:
    wins = 0; hp_sum = 0.0; turn_sum = 0

    for _ in range(n):
        ta = _random_team(team_size)
        tb = _random_team(team_size)

        r = simulate_battle(ia_a, ia_b, ta, tb)
        if r["winner"] == "a": wins += 1
        hp_sum   += r["hp_a"] - r["hp_b"]
        turn_sum += r["turns"]

        r2 = simulate_battle(ia_b, ia_a, tb, ta)
        if r2["winner"] == "b": wins += 1
        hp_sum   += r2["hp_b"] - r2["hp_a"]
        turn_sum += r2["turns"]

    total = n * 2
    return {
        "win_rate":  wins / total,
        "avg_hp":    hp_sum / total,
        "avg_turns": turn_sum / total,
    }