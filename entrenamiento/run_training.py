import sys, os, json, time, argparse, copy
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ia.config            import (load_config, save_config, DEFAULT,
                                   _DATA_PATH, GENOME_KEYS, genome_to_cfg)
from ia.ia_levels         import RandomAI, HeuristicAI, MinimaxAI
from datos.datos_pokemon  import POKEMON_DB
from models.clase_batalla  import BattlePokemon
from entrenamiento.genetic import run_ga
from entrenamiento.fitness  import evaluate
import random

LOG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "training_log.json"
)

GRN = "\033[92m"; YLW = "\033[93m"; RED = "\033[91m"
CYN = "\033[96m"; BLD = "\033[1m";  RST = "\033[0m"

def _bar(value, lo, hi, width=18) -> str:
    pct = (value - lo) / (hi - lo) if hi > lo else 0.5
    pct = max(0.0, min(1.0, pct))
    filled = int(pct * width)
    return f"[{'█'*filled}{'░'*(width-filled)}]"

def _make_rival_ias():
    pool = list(POKEMON_DB)
    def team():
        return [BattlePokemon(random.choice(pool))]
    t1, t2, t3 = team(), team(), team()
    return [
        RandomAI(t1, t1[0]),
        HeuristicAI(t2, t2[0]),
        MinimaxAI(t3, t3[0], enemy_team=t3),
    ]

def _print_header(args):
    print(f"\n{BLD}{'='*60}{RST}")
    print(f"{BLD}{CYN}  ENTRENAMIENTO IA NIVEL 4 — Algoritmo Genético{RST}")
    print(f"{BLD}{'='*60}{RST}")
    print(f"  Generaciones   : {BLD}{args.gen}{RST}")
    print(f"  Población      : {BLD}{args.pop}{RST}")
    print(f"  Batallas/rival : {BLD}{args.matches}{RST}  (x3 rivales)")
    print(f"  Mutación       : rate={BLD}{args.mut_rate}{RST}  fuerza={BLD}{args.mut_str}{RST}")
    print(f"  Torneo k       : {BLD}{args.tour_k}{RST}")
    print(f"  Warm start     : {BLD}{'No (desde cero)' if args.fresh else 'Sí (best_config.json)'}{RST}")
    print(f"  Guardando en   : {_DATA_PATH}")
    print(f"  Log en         : {LOG_PATH}")
    print(f"{BLD}{'='*60}{RST}\n")

def _print_gen_table_header():
    print(f"  {'Gen':>4}  {'Mejor':>8}  {'Prom':>8}  {'Peor':>8}  "
          f"{'Mejora':>7}  {'Tiempo':>7}")
    print(f"  {'----':>4}  {'--------':>8}  {'--------':>8}  {'--------':>8}  "
          f"{'-------':>7}  {'-------':>7}")

def _print_gen_row(gen, best, avg, worst, prev_best, elapsed):
    delta  = best - prev_best
    d_str  = f"{GRN}+{delta:.2f}{RST}" if delta > 0 else (
             f"{RED}{delta:.2f}{RST}"   if delta < 0 else
             f"  {delta:.2f}")
    t_str  = f"{elapsed:.1f}s"
    print(f"  {gen:>4}  {best:>8.2f}  {avg:>8.2f}  {worst:>8.2f}  "
          f"{d_str:>16}  {t_str:>7}")

def _print_best_genome(cfg: dict):
    print(f"\n{BLD}  Mejor individuo:{RST}")
    from ia.config import GENOME_BOUNDS
    rows = [
        ("depth",             "Profundidad árbol",   1,     5),
        ("w_hp_activo",       "Peso HP activo",       50,  400),
        ("w_hp_equipo",       "Peso HP equipo",       50,  300),
        ("w_vivos",           "Peso Pokémon vivos",   10,  150),
        ("w_tipo_atk",        "Ventaja tipo ofensiva", 5,  100),
        ("w_tipo_def",        "Penaliz. tipo defensiva",5, 100),
        ("w_mejor_dmg",       "Peso mejor daño",      20,  250),
        ("w_ko_bonus",        "Bonus amenaza KO",     10,  200),
        ("w_ko_done",         "Bonus KO logrado",     50,  300),
        ("w_velocidad",       "Bonus velocidad",       0,   50),
        ("w_ace_penalty",     "Penaliz. as en riesgo",20,  250),
        ("rival_agresividad", "Rival agresividad",    0.3,  1.0),
        ("rival_switch_bias", "Rival tendencia cambio",0.1, 0.9),
        ("rival_presion_ko",  "Rival presión KO",     0.3,  1.0),
        ("switch_hp_thresh",  "Umbral HP cambio",     0.1,  0.6),
    ]
    for key, label, lo, hi in rows:
        v   = cfg.get(key, 0)
        bar = _bar(v, lo, hi)
        print(f"    {label:<28} {bar} {v:>8.3f}")

def main():
    parser = argparse.ArgumentParser(description="Entrenamiento IA Nivel 4 (GA)")
    parser.add_argument("--gen",      type=int,   default=30)
    parser.add_argument("--pop",      type=int,   default=20)
    parser.add_argument("--matches",  type=int,   default=6)
    parser.add_argument("--mut-rate", type=float, default=0.15, dest="mut_rate")
    parser.add_argument("--mut-str",  type=float, default=0.12, dest="mut_str")
    parser.add_argument("--tour-k",   type=int,   default=3,    dest="tour_k")
    parser.add_argument("--fresh",    action="store_true")
    args = parser.parse_args()
    _print_header(args)
    seed_cfg   = None if args.fresh else load_config()
    if seed_cfg == DEFAULT:
        seed_cfg = None
    rival_ias  = _make_rival_ias()
    log        = []
    prev_best  = [None]  
    gen_times  = []

    def fitness_fn(genome):
        return evaluate(genome, rival_ias, matches_per_rival=args.matches)

    _print_gen_table_header()

    def on_generation(gen, best, avg, worst, best_genome, pop, scores):
        t_now = time.time()
        elapsed = t_now - on_generation._t0 if gen > 0 else 0.0
        on_generation._t0 = t_now

        if prev_best[0] is None:
            prev_best[0] = best

        _print_gen_row(gen, best, avg, worst, prev_best[0], elapsed)
        prev_best[0] = best
        gen_times.append(elapsed)

        log.append({
            "gen":   gen,
            "best":  round(best,  4),
            "avg":   round(avg,   4),
            "worst": round(worst, 4),
            "time_s": round(elapsed, 2),
            "best_cfg": genome_to_cfg(best_genome),
        })
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w") as f:
            json.dump(log, f, indent=2)
    on_generation._t0 = time.time()
    best_cfg = run_ga(
        fitness_fn        = fitness_fn,
        population_size   = args.pop,
        n_generations     = args.gen,
        mutation_rate     = args.mut_rate,
        mutation_strength = args.mut_str,
        tournament_k      = args.tour_k,
        seed_cfg          = seed_cfg,
        checkpoint_path   = _DATA_PATH,
        on_generation     = on_generation,
    )
    save_config(best_cfg, _DATA_PATH)
    total = sum(gen_times)
    print(f"\n{BLD}{'='*60}{RST}")
    print(f"{GRN}{BLD}  ✅ Entrenamiento completado{RST}")
    print(f"  Tiempo total   : {total:.1f}s  "
          f"({total/max(args.gen,1):.1f}s/gen)")
    print(f"  Config guardada: {_DATA_PATH}")
    print(f"  Log guardado   : {LOG_PATH}")
    _print_best_genome(best_cfg)
    print(f"{BLD}{'='*60}{RST}\n")

if __name__ == "__main__":
    main()