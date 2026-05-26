from ia.config     import genome_to_cfg
from entrenamiento.simulator import run_matches


def evaluate(genome: list, rival_ias: list,
             matches_per_rival: int = 6, team_size: int = 6) -> float:

    from ia.minimax_ai import MinimaxAI4

    cfg  = genome_to_cfg(genome)
    ia4  = MinimaxAI4([], None, cfg=cfg)

    total_score = 0.0
    #Peso Rival
    weights     = [0.2, 0.3, 0.5]  

    for rival, w in zip(rival_ias, weights):
        stats = run_matches(ia4, rival,
                            n=matches_per_rival,
                            team_size=team_size)
        score  = stats["win_rate"]  * 100.0
        score += stats["avg_hp"]    *  30.0
        score -= stats["avg_turns"] *   0.1  
        total_score += score * w

    return total_score
