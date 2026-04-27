import random

def rand(prob):
    """Retorna True con probabilidad prob (0-1)"""
    return random.random() < prob

def clamp(value, min_val, max_val):
    """Limita un valor entre min_val y max_val"""
    return max(min_val, min(max_val, value))

def get_stat_stage_mod(stage):
    """Calcula el multiplicador de estadísticas según el stage (-6 a +6)"""
    stages = [0.25, 0.28, 0.33, 0.4, 0.5, 0.66, 1, 1.5, 2, 2.5, 3, 3.5, 4]
    idx = max(0, min(12, stage + 6))
    return stages[idx]

def get_evasion_mod(stage):
    """Calcula el multiplicador de evasión"""
    stages = [0.33, 0.38, 0.43, 0.5, 0.6, 0.75, 1, 1.33, 1.66, 2, 2.5, 3, 3.5]
    idx = max(0, min(12, stage + 6))
    return stages[idx]