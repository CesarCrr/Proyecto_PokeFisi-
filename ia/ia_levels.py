import random
from batalla.tabla_tipos import get_type_multiplier


class RandomAI:
    #IA Nivel 1 - Comportamiento aleatorio
    #   - 70% probabilidad de atacar (movimiento aleatorio con PP)
    #   - 30% probabilidad de cambiar (Pokémon aleatorio vivo)
    
    def __init__(self, team, enemy_pokemon):
        self.team = team
        self.active_idx = 0
        self.enemy = enemy_pokemon

    def get_action(self):
        # 70% atacar, 30% cambiar
        if random.random() < 0.7:
            moves_with_pp = [i for i, m in enumerate(self.team[self.active_idx].movimientos) if m["pp"] > 0]
            if moves_with_pp:
                return ("move", random.choice(moves_with_pp))
        
        # Si no hay movimientos con PP o salió cambiar, intentar cambiar
        alive_indices = [i for i, p in enumerate(self.team) if not p.fainted and i != self.active_idx]
        if alive_indices:
            return ("switch", random.choice(alive_indices))
        
        # Si no puede cambiar, atacar con cualquier movimiento (incluso sin PP)
        moves_with_pp = [i for i, m in enumerate(self.team[self.active_idx].movimientos) if m["pp"] > 0]
        if moves_with_pp:
            return ("move", random.choice(moves_with_pp))
        
        # Último recurso: usar el primer movimiento (fallará por falta de PP)
        return ("move", 0)


class HeuristicAI:
    #IA Nivel 2 - Heurística inteligente
    #   - Evalúa si cambiar basado en HP, estado y ventaja de tipos
    #   - Selecciona el movimiento más efectivo basado en:
    #     * Efectividad de tipo contra el rival
    #     * Poder del movimiento
    #     * Movimientos de estado estratégicos
    
    def __init__(self, team, enemy_pokemon):
        self.team = team
        self.active_idx = 0
        self.enemy = enemy_pokemon

    def _get_hp_percent(self, pokemon):
        """Retorna el porcentaje de HP actual"""
        return (pokemon.current_hp / pokemon.max_hp) * 100

    def _should_switch(self, current, enemy):
        """Determina si la IA debería cambiar de Pokémon
        Retorna: (should_switch, best_index) o (False, None)
        """
        hp_percent = self._get_hp_percent(current)
        
        # Condiciones para cambiar:
        # 1. HP muy bajo (<25%)
        if hp_percent < 25:
            # Buscar un Pokémon con mejor matchup
            alive_indices = [i for i, p in enumerate(self.team) if not p.fainted and i != self.active_idx]
            if alive_indices:
                best_switch = None
                best_advantage = -999
                for idx in alive_indices:
                    candidate = self.team[idx]
                    # Calcular ventaja de tipo contra el enemigo
                    mult = 1.0
                    mult *= get_type_multiplier(candidate.tipo1, enemy.tipo1, enemy.tipo2)
                    if candidate.tipo2:
                        mult *= get_type_multiplier(candidate.tipo2, enemy.tipo1, enemy.tipo2)
                    # Bonus si el candidato tiene buen HP
                    hp_bonus = self._get_hp_percent(candidate) / 50
                    score = mult + hp_bonus
                    if score > best_advantage:
                        best_advantage = score
                        best_switch = idx
                if best_switch is not None and best_advantage > 0.8:
                    return (True, best_switch)
        
        # 2. El enemigo es muy efectivo contra mí (2x o 4x)
        mult_against_me = get_type_multiplier(enemy.tipo1, current.tipo1, current.tipo2)
        if current.tipo2:
            mult_against_me *= get_type_multiplier(enemy.tipo1, current.tipo2, None)
        
        if mult_against_me >= 2 and hp_percent < 50:
            alive_indices = [i for i, p in enumerate(self.team) if not p.fainted and i != self.active_idx]
            if alive_indices:
                # Buscar Pokémon que sea resistente o tenga ventaja
                best_switch = None
                best_defense = 999
                for idx in alive_indices:
                    candidate = self.team[idx]
                    # Medir qué tan resistente es contra el enemigo
                    defense_mult = get_type_multiplier(enemy.tipo1, candidate.tipo1, candidate.tipo2)
                    if candidate.tipo2:
                        defense_mult *= get_type_multiplier(enemy.tipo1, candidate.tipo2, None)
                    if defense_mult < best_defense:
                        best_defense = defense_mult
                        best_switch = idx
                if best_switch is not None and best_defense < 1:
                    return (True, best_switch)
        
        # 3. El Pokémon actual está paralizado o quemado y con HP bajo
        if current.status in ["paralyze", "burn"] and hp_percent < 40:
            alive_indices = [i for i, p in enumerate(self.team) if not p.fainted and i != self.active_idx]
            if alive_indices:
                return (True, random.choice(alive_indices))
        
        return (False, None)

    def _score_move(self, move, attacker, defender):
        """Evalúa un movimiento y le asigna una puntuación (más alto = mejor)"""
        score = 0
        
        # 1. Factor de tipo (lo más importante)
        type_mult = get_type_multiplier(move["tipo"], defender.tipo1, defender.tipo2)
        if defender.tipo2:
            type_mult *= get_type_multiplier(move["tipo"], defender.tipo2, None)
        
        if type_mult >= 2:
            score += 100  # Muy efectivo
        elif type_mult == 0:
            score -= 500  # No afecta - horrible
        elif type_mult < 1:
            score += 10   # Poco efectivo, pero mejor que nada
        else:
            score += 40   # Neutral
        
        # 2. Poder del movimiento
        power = move["poder"] if move["poder"] else 0
        score += power
        
        # 3. Movimientos de estado tienen prioridad estratégica
        if move["poder"] == 0:
            # Movimientos de estado
            effect = move["efecto"].lower()
            if "recupera" in effect or move["nombre"] in ["Recuperacion", "Respiro", "Síntesis"]:
                # Curarse si HP bajo
                hp_pct = self._get_hp_percent(attacker)
                if hp_pct < 50:
                    score += 80
                else:
                    score -= 20
            elif "danza" in move["nombre"].lower() or "paz mental" in effect or "calma mental" in effect:
                # Movimientos de mejora de estadísticas
                score += 45
            elif "mofa" in move["nombre"].lower():
                score += 35
            elif "proteccion" in move["nombre"].lower():
                score += 20
            elif "drenadoras" in move["nombre"].lower() and defender.status != "infectado":
                score += 50
            elif "fuego fatuo" in move["nombre"].lower() and defender.status is None:
                score += 40
            elif "onda trueno" in move["nombre"].lower() and defender.status is None:
                score += 35
            elif "tox" in effect.lower() and defender.status is None:
                score += 45
            else:
                score += 15  # Otros movimientos de estado
        
        # 4. Penalización por PP bajo (para no quedarse sin PP)
        if move["pp"] <= max(1, move["pp_max"] // 4):
            score -= 15
        
        # 5. Bonus por movimientos que el rival ya tiene estado (no repetir)
        if "quema" in move["efecto"].lower() and defender.status == "burn":
            score -= 40
        if "paraliza" in move["efecto"].lower() and defender.status == "paralyze":
            score -= 40
        if "envenena" in move["efecto"].lower() and defender.status in ["poison", "toxic"]:
            score -= 40
        if "duerme" in move["efecto"].lower() and defender.status == "sleep":
            score -= 40
        
        # 6. Bonus por efectividad de tipo adicional (contra segundo tipo)
        if defender.tipo2:
            mult2 = get_type_multiplier(move["tipo"], defender.tipo2, None)
            if mult2 >= 2:
                score += 30
        
        return score

    def _get_best_move(self, current, enemy):
        """Selecciona el mejor movimiento según la puntuación"""
        moves = current.movimientos
        best_score = -999
        best_move_idx = 0
        
        for i, move in enumerate(moves):
            if move["pp"] <= 0:
                continue  # Sin PP no puede usarse
            
            score = self._score_move(move, current, enemy)
            
            # Bonus si es el único movimiento con PP (evitar quedarse sin opciones)
            moves_with_pp = [m for m in moves if m["pp"] > 0]
            if len(moves_with_pp) == 1:
                score += 50
            
            if score > best_score:
                best_score = score
                best_move_idx = i
        
        # Si todos los movimientos tienen PP 0, usar el que tenga más PP (aunque sea 0)
        if best_score == -999:
            max_pp = -1
            for i, move in enumerate(moves):
                if move["pp"] > max_pp:
                    max_pp = move["pp"]
                    best_move_idx = i
        
        return best_move_idx

    def get_action(self):
        """Obtiene la acción de la IA (movimiento o cambio)"""
        current = self.team[self.active_idx]
        enemy = self.enemy
        
        # Actualizar referencia al enemigo (puede haber cambiado)
        self.enemy = enemy
        
        # Verificar si el Pokémon actual está vivo
        if current.fainted:
            # Debería estar muerto, buscar uno vivo
            alive_indices = [i for i, p in enumerate(self.team) if not p.fainted]
            if alive_indices:
                return ("switch", random.choice(alive_indices))
            return ("move", 0)
        
        # 1. Verificar si debe cambiar
        should_switch, switch_idx = self._should_switch(current, enemy)
        if should_switch and switch_idx is not None:
            return ("switch", switch_idx)
        
        # 2. Si no cambia, seleccionar el mejor movimiento
        best_move_idx = self._get_best_move(current, enemy)
        return ("move", best_move_idx)