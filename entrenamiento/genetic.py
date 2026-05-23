import random, copy
from ia.config import GENOME_KEYS, GENOME_BOUNDS, cfg_to_genome


def random_genome() -> list:
    return [random.uniform(*GENOME_BOUNDS[k]) for k in GENOME_KEYS]


def clamp_genome(genome: list) -> list:
    return [max(GENOME_BOUNDS[k][0], min(GENOME_BOUNDS[k][1], genome[i]))
            for i, k in enumerate(GENOME_KEYS)]


def init_population(size: int, seed_cfg: dict = None) -> list:
    pop = []
    if seed_cfg:
        pop.append(clamp_genome(cfg_to_genome(seed_cfg)))
    while len(pop) < size:
        pop.append(random_genome())
    return pop


def tournament_select(pop: list, scores: list, k: int = 3) -> list:
    candidates = random.sample(range(len(pop)), k)
    return copy.copy(pop[max(candidates, key=lambda i: scores[i])])


def crossover(a: list, b: list) -> tuple:
    c1, c2 = [], []
    for ga, gb in zip(a, b):
        if random.random() < 0.5:
            c1.append(ga); c2.append(gb)
        else:
            c1.append(gb); c2.append(ga)
    return c1, c2


def mutate(genome: list, rate: float = 0.15, strength: float = 0.12) -> list:
    out = []
    for i, k in enumerate(GENOME_KEYS):
        lo, hi = GENOME_BOUNDS[k]
        v = genome[i]
        if random.random() < rate:
            v += random.gauss(0, (hi - lo) * strength)
            v  = max(lo, min(hi, v))
        out.append(v)
    return out


def run_ga(fitness_fn,
           population_size:   int   = 20,
           n_generations:     int   = 30,
           mutation_rate:     float = 0.15,
           mutation_strength: float = 0.12,
           tournament_k:      int   = 3,
           seed_cfg:          dict  = None,
           checkpoint_path:   str   = None,
           on_generation=None) -> dict:

    from ia.config import genome_to_cfg, save_config

    pop    = init_population(population_size, seed_cfg)
    scores = [fitness_fn(g) for g in pop]

    best_idx    = max(range(len(scores)), key=lambda i: scores[i])
    best_genome = copy.copy(pop[best_idx])
    best_score  = scores[best_idx]

    if on_generation:
        on_generation(0, best_score,
                      sum(scores)/len(scores),
                      min(scores),
                      best_genome, pop, scores)

    for gen in range(1, n_generations + 1):
        new_pop = [copy.copy(best_genome)]  # Elitismo

        while len(new_pop) < population_size:
            p1 = tournament_select(pop, scores, tournament_k)
            p2 = tournament_select(pop, scores, tournament_k)
            c1, c2 = crossover(p1, p2)
            c1 = clamp_genome(mutate(c1, mutation_rate, mutation_strength))
            c2 = clamp_genome(mutate(c2, mutation_rate, mutation_strength))
            new_pop.extend([c1, c2])

        pop    = new_pop[:population_size]
        scores = [fitness_fn(g) for g in pop]

        gen_best = max(range(len(scores)), key=lambda i: scores[i])
        if scores[gen_best] > best_score:
            best_score  = scores[gen_best]
            best_genome = copy.copy(pop[gen_best])

        if on_generation:
            on_generation(gen, best_score,
                          sum(scores)/len(scores),
                          min(scores),
                          best_genome, pop, scores)

        if checkpoint_path:
            save_config(genome_to_cfg(best_genome), checkpoint_path)

    return genome_to_cfg(best_genome)
