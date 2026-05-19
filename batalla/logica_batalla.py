import random
from utiles.funciones_auxiliares import rand, clamp
from batalla.tabla_tipos import get_type_multiplier
from batalla.efectos import apply_move_effects

def calculate_damage(attacker, defender, move):
    if move["poder"] <= 0:
        return 0, 1.0
    if move["categoria"] == "Fisico":
        atk = attacker.get_effective_stat("atk")
        defense = defender.get_effective_stat("def")
    else:
        atk = attacker.get_effective_stat("atk")
        defense = defender.get_effective_stat("def")
    type_mult = get_type_multiplier(move["tipo"], defender.tipo1, defender.tipo2)
    base_damage = (atk / defense) * move["poder"]
    damage = max(1, int(base_damage * type_mult))
    if attacker.status == "burn" and move["categoria"] == "Fisico":
        damage = int(damage * 0.5)
    return damage, type_mult

def calculate_special_damage(attacker, defender, move):
    if move["nombre"] == "Plancha Corporal":
        atk_stat = attacker.get_effective_stat("def")
        def_stat = defender.get_effective_stat("def")
        power = move["poder"]
    elif move["nombre"] == "Cuerpo Pesado":
        power = move["poder"]
        if attacker.get_effective_stat("def") > defender.get_effective_stat("def") + 15:
            power = 120
        else:
            power = 60
        atk_stat = attacker.get_effective_stat("atk")
        def_stat = defender.get_effective_stat("def")
    else:
        return None
    type_mult = get_type_multiplier(move["tipo"], defender.tipo1, defender.tipo2)
    base_damage = (atk_stat / def_stat) * power
    damage = max(1, int(base_damage * type_mult))
    if attacker.status == "burn" and move["categoria"] == "Fisico":
        damage = int(damage * 0.5)
    return damage, type_mult

def get_priority(move_idx, pokemon):
    if move_idx is None:
        return 0
    move = pokemon.movimientos[move_idx]
    effect = move["efecto"].lower()
    if effect == "proteccion":
        return 5
    if move["nombre"] in ["Vuelo", "Bote", "Super Puño", "Puño Bala", "Sombra Vil"]:
        return 2
    if "prioridad +2" in effect:
        return 3
    if "prioridad +1" in effect:
        return 2
    return 0

def is_flying(pokemon):
    return pokemon.flying_turns in [1, 2]

def can_be_hit(attacker, defender, move):
    if defender.flying_turns in [1, 2]:
        if move["tipo"] == "Electrico":
            return True
        return False
    return True

def resolve_turn(player_pokemon, ai_pokemon, player_move_idx, ai_move_idx,
                 player_switch, ai_switch, player_new_idx, ai_new_idx,
                 player_force_switch_pokemon_idx, player_team, ai_team,
                 player_active_idx, ai_active_idx, log_lines,
                 player_hazards, ai_hazards):
    
    if player_switch:
        log_lines.append(f"🔄 Cambiaste a {player_pokemon.nombre}")
        return None
    if ai_switch:
        log_lines.append(f"🔄 La IA cambió a {ai_pokemon.nombre}")
        return None

    # Forzar Enfado
    if player_pokemon.outrage_locked:
        for i, m in enumerate(player_pokemon.movimientos):
            if m["nombre"] == "Enfado":
                player_move_idx = i
                break
    
    if ai_pokemon.outrage_locked:
        for i, m in enumerate(ai_pokemon.movimientos):
            if m["nombre"] == "Enfado":
                ai_move_idx = i
                break
    
    # Si está volando en turno de carga (2), no puede atacar
    if player_pokemon.flying_turns == 2:
        player_move_idx = None
    if ai_pokemon.flying_turns == 2:
        ai_move_idx = None

    # Bostezo
    if hasattr(player_pokemon, 'sleep_next') and player_pokemon.sleep_next:
        player_pokemon.status = "sleep"
        player_pokemon.status_turns = random.randint(2, 3)
        player_pokemon.sleep_next = False
        log_lines.append(f"😴 ¡{player_pokemon.nombre} se durmió por Bostezo!")
    if hasattr(ai_pokemon, 'sleep_next') and ai_pokemon.sleep_next:
        ai_pokemon.status = "sleep"
        ai_pokemon.status_turns = random.randint(2, 3)
        ai_pokemon.sleep_next = False
        log_lines.append(f"😴 ¡{ai_pokemon.nombre} se durmió por Bostezo!")

    # Vuelo/Bote — turno 2 (aterrizaje y golpe)
    # El turno de carga (flying_turns==2) solo prepara el vuelo; el rival SÍ actúa.
    # El turno de golpe  (flying_turns==1) se resuelve aquí antes del bucle de velocidad,
    # y el pokemon que aterriza no vuelve a actuar en el bucle normal (move_idx=None).
    # Durante el turno de carga el pokemon es invulnerable (excepto a Eléctrico).
    def _ejecutar_aterrizaje(atacante, defensor, log):
        move_name = atacante.flying_move
        move = next((m for m in atacante.movimientos if m["nombre"] == move_name), None)
        atacante.flying_turns = 0
        atacante.flying_move = None
        atacante.flying_active = False
        if not move:
            return False
        if move["pp"] > 0:
            move["pp"] -= 1
        log.append(f"🕊️ {atacante.nombre} usó {move['nombre']}!")
        special = calculate_special_damage(atacante, defensor, move)
        damage, type_mult = special if special else calculate_damage(atacante, defensor, move)
        if type_mult == 0:
            log.append(f"¡No afecta a {defensor.nombre}!")
            return False
        if rand(0.0625):
            damage = int(damage * 1.5)
            log.append("💥 ¡Golpe crítico!")
        defensor.apply_damage(damage)
        if type_mult >= 2:
            log.append(f"¡Es muy efectivo! (x{type_mult})")
        elif type_mult < 1:
            log.append(f"No es muy efectivo... (x{type_mult})")
        log.append(f"💢 {defensor.nombre} recibió {damage} de daño.")
        if move["nombre"] in ["Gigadrenado", "Puño Drenaje"]:
            drain = int(damage * 0.5)
            atacante.heal(drain)
            log.append(f"💚 {atacante.nombre} absorbió {drain} HP!")
        if move["nombre"] == "Pajaro Osado":
            recoil = int(damage / 3)
            atacante.apply_damage(recoil, True)
            log.append(f"⚠️ {atacante.nombre} recibió {recoil} de retroceso!")
        if defensor.current_hp <= 0:
            defensor.fainted = True
            log.append(f"💀 ¡{defensor.nombre} fue derrotado!")
            return True
        return False

    if player_pokemon.flying_turns == 1:
        _ejecutar_aterrizaje(player_pokemon, ai_pokemon, log_lines)
        player_move_idx = None   # no actúa de nuevo en el bucle normal

    if ai_pokemon.flying_turns == 1:
        _ejecutar_aterrizaje(ai_pokemon, player_pokemon, log_lines)
        ai_move_idx = None       # no actúa de nuevo en el bucle normal

    # Enfado
    if player_pokemon.outrage_active:
        player_pokemon.outrage_turns -= 1
        if player_pokemon.outrage_turns <= 0:
            player_pokemon.outrage_active = False
            player_pokemon.outrage_locked = False
            player_pokemon.confused = True
            player_pokemon.confused_turns = random.randint(2, 5)
            log_lines.append(f"😵 ¡{player_pokemon.nombre} ya no está enfurecido! ¡{player_pokemon.nombre} está confundido!")
        else:
            enfado_idx = next((i for i, m in enumerate(player_pokemon.movimientos) if m["nombre"] == "Enfado"), player_move_idx)
            player_move_idx = enfado_idx
            log_lines.append(f"😤 {player_pokemon.nombre} está enfurecido! (Quedan {player_pokemon.outrage_turns} turnos)")

    if ai_pokemon.outrage_active:
        ai_pokemon.outrage_turns -= 1
        if ai_pokemon.outrage_turns <= 0:
            ai_pokemon.outrage_active = False
            ai_pokemon.outrage_locked = False
            ai_pokemon.confused = True
            ai_pokemon.confused_turns = random.randint(2, 5)
            log_lines.append(f"😵 ¡{ai_pokemon.nombre} ya no está enfurecido! ¡{ai_pokemon.nombre} está confundido!")
        else:
            enfado_idx = next((i for i, m in enumerate(ai_pokemon.movimientos) if m["nombre"] == "Enfado"), ai_move_idx)
            ai_move_idx = enfado_idx
            log_lines.append(f"😤 {ai_pokemon.nombre} está enfurecido! (Quedan {ai_pokemon.outrage_turns} turnos)")

    def check_confusion(pokemon, log):
        if pokemon.confused:
            pokemon.confused_turns -= 1
            if rand(0.5):
                confusion_damage = max(1, int((pokemon.get_effective_stat("atk") / pokemon.get_effective_stat("def")) * 40))
                log.append(f"😵 ¡{pokemon.nombre} está confundido y se golpeó a sí mismo!")
                pokemon.apply_damage(confusion_damage, True)
                if pokemon.current_hp <= 0:
                    log.append(f"💀 ¡{pokemon.nombre} se derrotó a sí mismo!")
                if pokemon.confused_turns <= 0:
                    pokemon.confused = False
                    log.append(f"😵 {pokemon.nombre} ya no está confundido.")
                return False
            else:
                if pokemon.confused_turns <= 0:
                    pokemon.confused = False
                    log.append(f"😵 {pokemon.nombre} ya no está confundido.")
        return True

    def check_status(pokemon, log):
        if pokemon.status == "sleep":
            pokemon.status_turns -= 1
            if pokemon.status_turns <= 0:
                pokemon.status = None
                log.append(f"😴 ¡{pokemon.nombre} se despertó!")
            else:
                log.append(f"😴 {pokemon.nombre} no puede atacar porque está dormido!")
                return False
        if pokemon.status == "freeze":
            if hasattr(pokemon, 'freeze_turns'):
                pokemon.freeze_turns -= 1
                if pokemon.freeze_turns <= 0:
                    pokemon.status = None
                    log.append(f"❄️ ¡{pokemon.nombre} se descongeló!")
                    return True
                else:
                    log.append(f"❄️ {pokemon.nombre} no puede atacar porque está congelado!")
                    return False
            if rand(0.2):
                pokemon.status = None
                log.append(f"❄️ ¡{pokemon.nombre} se descongeló!")
            else:
                log.append(f"❄️ {pokemon.nombre} no puede atacar porque está congelado!")
                return False
        if pokemon.status == "paralyze":
            if hasattr(pokemon, 'paralyze_turns'):
                pokemon.paralyze_turns -= 1
                if pokemon.paralyze_turns <= 0:
                    pokemon.status = None
                    log.append(f"⚡ ¡{pokemon.nombre} ya no está paralizado!")
                    return True
            if rand(0.25):
                log.append(f"⚡ {pokemon.nombre} está paralizado y no puede moverse!")
                return False
        return True

    player_speed = player_pokemon.get_effective_stat("spe")
    ai_speed = ai_pokemon.get_effective_stat("spe")
    if player_pokemon.status == "paralyze":
        player_speed = int(player_speed * 0.5)
    if ai_pokemon.status == "paralyze":
        ai_speed = int(ai_speed * 0.5)

    player_priority = get_priority(player_move_idx, player_pokemon)
    ai_priority = get_priority(ai_move_idx, ai_pokemon)
    
    if player_priority > ai_priority:
        first_player = "player"
    elif ai_priority > player_priority:
        first_player = "ai"
    else:
        first_player = "player" if player_speed >= ai_speed else "ai"

    for turn_order in (["player", "ai"] if first_player == "player" else ["ai", "player"]):
        if turn_order == "player":
            if player_pokemon.fainted or ai_pokemon.fainted:
                continue
            if hasattr(player_pokemon, 'taunted') and player_pokemon.taunted:
                if player_move_idx is not None:
                    move = player_pokemon.movimientos[player_move_idx]
                    if move["poder"] == 0:
                        log_lines.append(f"😤 ¡{player_pokemon.nombre} está provocado y no puede usar {move['nombre']}!")
                        continue
            if hasattr(ai_pokemon, 'is_protected') and ai_pokemon.is_protected:
                if player_move_idx is not None:
                    move = player_pokemon.movimientos[player_move_idx]
                    if move["poder"] > 0:
                        log_lines.append(f"🛡️ ¡{ai_pokemon.nombre} se protegió del ataque de {player_pokemon.nombre}!")
                        ai_pokemon.is_protected = False
                        continue
            if not check_status(player_pokemon, log_lines):
                continue
            if not check_confusion(player_pokemon, log_lines):
                continue
            if player_move_idx is None:
                continue
            
            move = player_pokemon.movimientos[player_move_idx]
            
            # Vuelo/Bote: primer turno de carga (solo sube, sin daño)
            # El rival SÍ actúa este turno; el jugador queda invulnerable.
            if move["nombre"] in ["Vuelo", "Bote"]:
                if player_pokemon.flying_turns == 0 and not player_pokemon.flying_active:
                    log_lines.append(f"🔵 {player_pokemon.nombre} usó {move['nombre']}!")
                    apply_move_effects(player_pokemon, ai_pokemon, move, log_lines, True, player_hazards, ai_hazards)
                    continue  # El jugador no hace más este turno; la IA sí actúa
            
            # Log del movimiento
            log_lines.append(f"🔵 {player_pokemon.nombre} usó {move['nombre']}!")
            
            # Verificar PP
            if move["pp"] <= 0:
                log_lines.append("¡Sin PP! El movimiento falló.")
                continue
            
            # Consumir PP (solo si no es Vuelo/Bote, ya retornamos antes para esos)
            if move["nombre"] not in ["Vuelo", "Bote"]:
                move["pp"] -= 1
            
            # Verificar si el objetivo puede ser golpeado
            if not can_be_hit(player_pokemon, ai_pokemon, move):
                log_lines.append(f"🕊️ ¡{ai_pokemon.nombre} está volando y {player_pokemon.nombre} no puede alcanzarlo!")
                continue
                
            # Precisión
            accuracy = move["precision"]
            if move["nombre"] not in ["Proteccion", "Vuelo", "Bote", "Ida y Vuelta", "Voltio Cambio", "Onda Trueno", "Fuego Fatuo", "Deseo", "Danza Espada", "Malicioso", "Mofa", "Doble Equipo", "Defensa Ferréa", "Foco Energía", "Agilidad", "Impulso", "Danza Aleteo", "Paz Mental", "Calma Mental", "Amnesia", "Campana Cura", "Descanso", "Bostezo", "Síntesis", "Polvo Veneno", "Despejar", "Trampa Rocas", "Puas", "Puas Toxicas", "Destello"]:
                evasion_mod = ai_pokemon.get_effective_stat("evasion")  # evasión del defensor
                final_accuracy = accuracy * (1.0 / evasion_mod) if evasion_mod > 0 else accuracy
                if not rand(final_accuracy):
                    log_lines.append(f"¡{player_pokemon.nombre} falló el ataque!")
                    continue
            
            # Daño
            if move["poder"] > 0:
                special = calculate_special_damage(player_pokemon, ai_pokemon, move)
                if special:
                    damage, type_mult = special
                else:
                    damage, type_mult = calculate_damage(player_pokemon, ai_pokemon, move)
                hits = 2 if "golpea 2 veces" in move["efecto"].lower() else 1
                for _ in range(hits):
                    if rand(0.0625):
                        damage = int(damage * 1.5)
                        log_lines.append(f"💥 ¡Golpe crítico!")
                    ai_pokemon.apply_damage(damage)
                    if type_mult >= 2:
                        log_lines.append(f"¡Es muy efectivo! (x{type_mult})")
                    elif type_mult == 0:
                        log_lines.append(f"¡No afecta a {ai_pokemon.nombre}!")
                        ai_pokemon.apply_damage(-damage, True)
                        break
                    elif type_mult < 1:
                        log_lines.append(f"No es muy efectivo... (x{type_mult})")
                    log_lines.append(f"💢 {ai_pokemon.nombre} recibió {damage} de daño.")
                    if move["nombre"] in ["Gigadrenado", "Puño Drenaje"]:
                        drain = int(damage * 0.5)
                        player_pokemon.heal(drain)
                        log_lines.append(f"💚 {player_pokemon.nombre} absorbió {drain} HP!")
                    if move["nombre"] == "Pajaro Osado":
                        recoil = int(damage / 3)
                        player_pokemon.apply_damage(recoil, True)
                        log_lines.append(f"⚠️ {player_pokemon.nombre} recibió {recoil} de retroceso!")
                apply_move_effects(player_pokemon, ai_pokemon, move, log_lines, True, player_hazards, ai_hazards)
            else:
                apply_move_effects(player_pokemon, ai_pokemon, move, log_lines, True, player_hazards, ai_hazards)
            
            if move["nombre"] in ["Ida y Vuelta", "Voltio Cambio"] and not player_pokemon.fainted:
                if ai_pokemon.current_hp <= 0:
                    ai_pokemon.fainted = True
                    log_lines.append(f"💀 ¡{ai_pokemon.nombre} fue derrotado!")
                return (move["nombre"].lower().replace(" ", "_"), player_pokemon)
                
            if ai_pokemon.current_hp <= 0:
                ai_pokemon.fainted = True
                log_lines.append(f"💀 ¡{ai_pokemon.nombre} fue derrotado!")
        
        else:  # turn_order == "ai"
            if ai_pokemon.fainted or player_pokemon.fainted:
                continue
            if hasattr(ai_pokemon, 'taunted') and ai_pokemon.taunted:
                if ai_move_idx is not None:
                    move = ai_pokemon.movimientos[ai_move_idx]
                    if move["poder"] == 0:
                        log_lines.append(f"😤 ¡{ai_pokemon.nombre} está provocado y no puede usar {move['nombre']}!")
                        continue
            if hasattr(player_pokemon, 'is_protected') and player_pokemon.is_protected:
                if ai_move_idx is not None:
                    move = ai_pokemon.movimientos[ai_move_idx]
                    if move["poder"] > 0:
                        log_lines.append(f"🛡️ ¡{player_pokemon.nombre} se protegió del ataque de {ai_pokemon.nombre}!")
                        player_pokemon.is_protected = False
                        continue
            if not check_status(ai_pokemon, log_lines):
                continue
            if not check_confusion(ai_pokemon, log_lines):
                continue
            if ai_move_idx is None:
                continue
            
            move = ai_pokemon.movimientos[ai_move_idx]
            
            # Vuelo/Bote para IA: primer turno de carga (solo sube, sin daño)
            if move["nombre"] in ["Vuelo", "Bote"]:
                if ai_pokemon.flying_turns == 0 and not ai_pokemon.flying_active:
                    log_lines.append(f"🔴 {ai_pokemon.nombre} usó {move['nombre']}!")
                    apply_move_effects(ai_pokemon, player_pokemon, move, log_lines, False, player_hazards, ai_hazards)
                    continue  # La IA no hace más este turno; el jugador sí actúa
            
            log_lines.append(f"🔴 {ai_pokemon.nombre} usó {move['nombre']}!")
            
            if move["pp"] <= 0:
                log_lines.append("¡Sin PP! El movimiento falló.")
                continue
            
            if move["nombre"] not in ["Vuelo", "Bote"]:
                move["pp"] -= 1
            
            if not can_be_hit(ai_pokemon, player_pokemon, move):
                log_lines.append(f"🕊️ ¡{player_pokemon.nombre} está volando y {ai_pokemon.nombre} no puede alcanzarlo!")
                continue
                
            accuracy = move["precision"]
            if move["nombre"] not in ["Proteccion", "Vuelo", "Bote", "Ida y Vuelta", "Voltio Cambio", "Onda Trueno", "Fuego Fatuo", "Deseo", "Danza Espada", "Malicioso", "Mofa", "Doble Equipo", "Defensa Ferréa", "Foco Energía", "Agilidad", "Impulso", "Danza Aleteo", "Paz Mental", "Calma Mental", "Amnesia", "Campana Cura", "Descanso", "Bostezo", "Síntesis", "Polvo Veneno", "Despejar", "Trampa Rocas", "Puas", "Puas Toxicas", "Destello"]:
                evasion_mod = player_pokemon.get_effective_stat("evasion")  # evasión del defensor
                final_accuracy = accuracy * (1.0 / evasion_mod) if evasion_mod > 0 else accuracy
                if not rand(final_accuracy):
                    log_lines.append(f"¡{ai_pokemon.nombre} falló el ataque!")
                    continue
            
            if move["poder"] > 0:
                special = calculate_special_damage(ai_pokemon, player_pokemon, move)
                if special:
                    damage, type_mult = special
                else:
                    damage, type_mult = calculate_damage(ai_pokemon, player_pokemon, move)
                hits = 2 if "golpea 2 veces" in move["efecto"].lower() else 1
                for _ in range(hits):
                    if rand(0.0625):
                        damage = int(damage * 1.5)
                        log_lines.append(f"💥 ¡Golpe crítico!")
                    player_pokemon.apply_damage(damage)
                    if type_mult >= 2:
                        log_lines.append(f"¡Es muy efectivo! (x{type_mult})")
                    elif type_mult == 0:
                        log_lines.append(f"¡No afecta a {player_pokemon.nombre}!")
                        player_pokemon.apply_damage(-damage, True)
                        break
                    elif type_mult < 1:
                        log_lines.append(f"No es muy efectivo... (x{type_mult})")
                    log_lines.append(f"💢 {player_pokemon.nombre} recibió {damage} de daño.")
                    if move["nombre"] in ["Gigadrenado", "Puño Drenaje"]:
                        drain = int(damage * 0.5)
                        ai_pokemon.heal(drain)
                        log_lines.append(f"💚 {ai_pokemon.nombre} absorbió {drain} HP!")
                    if move["nombre"] == "Pajaro Osado":
                        recoil = int(damage / 3)
                        ai_pokemon.apply_damage(recoil, True)
                        log_lines.append(f"⚠️ {ai_pokemon.nombre} recibió {recoil} de retroceso!")
                apply_move_effects(ai_pokemon, player_pokemon, move, log_lines, False, player_hazards, ai_hazards)
            else:
                apply_move_effects(ai_pokemon, player_pokemon, move, log_lines, False, player_hazards, ai_hazards)
            
            if player_pokemon.current_hp <= 0:
                player_pokemon.fainted = True
                log_lines.append(f"💀 ¡{player_pokemon.nombre} fue derrotado!")

    # Daño por estado al final del turno
    for pokemon in [player_pokemon, ai_pokemon]:
        if pokemon.fainted:
            continue
        if pokemon.status == "burn":
            damage = int(pokemon.max_hp / 16)
            pokemon.apply_damage(damage, True)
            if hasattr(pokemon, 'burn_turns'):
                pokemon.burn_turns -= 1
                if pokemon.burn_turns <= 0:
                    pokemon.status = None
                    log_lines.append(f"🔥 ¡La quemadura de {pokemon.nombre} terminó!")
            log_lines.append(f"🔥 {pokemon.nombre} sufre daño por quemadura ({damage} HP).")
        if pokemon.status == "poison":
            damage = int(pokemon.max_hp / 16 * pokemon.poison_counter)
            pokemon.poison_counter += 1
            pokemon.apply_damage(damage, True)
            log_lines.append(f"☠️ {pokemon.nombre} sufre daño por veneno ({damage} HP).")
        if pokemon.status == "toxic":
            damage = int(pokemon.max_hp / 16 * pokemon.poison_counter)
            pokemon.poison_counter += 1
            pokemon.apply_damage(damage, True)
            log_lines.append(f"☠️ {pokemon.nombre} sufre daño por veneno grave ({damage} HP).")
        
        if pokemon.status == "infectado":
            damage = int(pokemon.max_hp / 8)
            pokemon.apply_damage(damage, True)
            if hasattr(pokemon, 'leech_seed_from') and pokemon.leech_seed_from and not pokemon.leech_seed_from.fainted:
                pokemon.leech_seed_from.heal(damage)
                log_lines.append(f"🌱 {pokemon.nombre} pierde {damage} HP por estar infectado y {pokemon.leech_seed_from.nombre} recupera {damage} HP.")
            else:
                log_lines.append(f"🌱 {pokemon.nombre} pierde {damage} HP por estar infectado.")
            if pokemon.current_hp <= 0:
                pokemon.fainted = True
                log_lines.append(f"💀 ¡{pokemon.nombre} fue derrotado!")
        
        if pokemon.current_hp <= 0:
            pokemon.fainted = True
            log_lines.append(f"💀 ¡{pokemon.nombre} fue derrotado!")

    # Deseo
    if player_pokemon.wish_heal > 0:
        player_pokemon.heal(player_pokemon.wish_heal)
        log_lines.append(f"✨ ¡El Deseo de {player_pokemon.nombre} se cumple! Recupera {player_pokemon.wish_heal} HP.")
        player_pokemon.wish_heal = 0
    if ai_pokemon.wish_heal > 0:
        ai_pokemon.heal(ai_pokemon.wish_heal)
        log_lines.append(f"✨ ¡El Deseo de {ai_pokemon.nombre} se cumple! Recupera {ai_pokemon.wish_heal} HP.")
        ai_pokemon.wish_heal = 0

    # Mofa
    if hasattr(player_pokemon, 'taunted') and player_pokemon.taunted:
        player_pokemon.taunted_turns -= 1
        if player_pokemon.taunted_turns <= 0:
            player_pokemon.taunted = False
            log_lines.append(f"😤 {player_pokemon.nombre} ya no está provocado.")
    if hasattr(ai_pokemon, 'taunted') and ai_pokemon.taunted:
        ai_pokemon.taunted_turns -= 1
        if ai_pokemon.taunted_turns <= 0:
            ai_pokemon.taunted = False
            log_lines.append(f"😤 {ai_pokemon.nombre} ya no está provocado.")

    # Resetear protección
    if hasattr(player_pokemon, 'is_protected'):
        player_pokemon.is_protected = False
    if hasattr(ai_pokemon, 'is_protected'):
        ai_pokemon.is_protected = False

    return None