import random
from utiles.funciones_auxiliares import rand, clamp

def apply_move_effects(attacker, defender, move, log_lines, is_player_attacking, player_hazards, ai_hazards):
    effect = move["efecto"].lower()
    move_name = move["nombre"]
    
    # Pokémon volando (Vuelo/Bote turno de carga) es inmune a estados y efectos de campo
    defender_flying = getattr(defender, 'flying_active', False) and getattr(defender, 'flying_turns', 0) == 2
    attacker_flying = getattr(attacker, 'flying_active', False) and getattr(attacker, 'flying_turns', 0) == 2
    
    # 1. Estados
    
    if move_name == "Fuego Fatuo" and defender.status is None:
        if defender_flying:
            log_lines.append(f"🕊️ ¡{defender.nombre} está volando y es inmune al estado!")
            return
        if rand(0.85):
            defender.status = "burn"
            defender.burn_turns = random.randint(2, 5)
            log_lines.append(f"🔥 ¡{defender.nombre} fue quemado por Fuego Fatuo!")
        else:
            log_lines.append(f"🔥 El Fuego Fatuo de {attacker.nombre} falló.")
        return
    
    if move_name == "Onda Trueno" and defender.status is None:
        if defender_flying:
            log_lines.append(f"🕊️ ¡{defender.nombre} está volando y es inmune al estado!")
            return
        if rand(0.9):
            defender.status = "paralyze"
            defender.paralyze_turns = random.randint(3, 5)
            log_lines.append(f"⚡ ¡{defender.nombre} fue paralizado por Onda Trueno!")
        else:
            log_lines.append(f"⚡ La Onda Trueno de {attacker.nombre} falló.")
        return
    
    if "paralizar" in effect and defender.status is None and not defender_flying and rand(0.1):
        defender.status = "paralyze"
        defender.paralyze_turns = random.randint(3, 5)
        log_lines.append(f"⚡ ¡{defender.nombre} fue paralizado!")
    
    if "congelar" in effect and defender.status is None and not defender_flying and rand(0.1):
        defender.status = "freeze"
        defender.freeze_turns = random.randint(2, 5)
        log_lines.append(f"❄️ ¡{defender.nombre} fue congelado!")
    
    if move_name == "Polvo Veneno" and defender.status is None:
        if defender_flying:
            log_lines.append(f"🕊️ ¡{defender.nombre} está volando y es inmune al estado!")
            return
        defender.status = "poison"
        defender.poison_counter = 1
        log_lines.append(f"☠️ ¡{defender.nombre} fue envenenado por Polvo Veneno!")
        return

    if ("envenenar" in effect or effect == "envenena") and defender.status is None and not defender_flying and rand(0.3):
        defender.status = "poison"
        defender.poison_counter = 1
        log_lines.append(f"☠️ ¡{defender.nombre} fue envenenado!")
    
    if "veneno grave" in effect and defender.status is None:
        if defender_flying:
            log_lines.append(f"🕊️ ¡{defender.nombre} está volando y es inmune al estado!")
            return
        defender.status = "toxic"
        defender.poison_counter = 1
        log_lines.append(f"☠️ ¡{defender.nombre} fue gravemente envenenado!")
        return
    
    # 2. Movimientos De Estado
    
    if move_name == "Drenadoras" and defender.status is None and defender.status != "infectado":
        if defender_flying:
            log_lines.append(f"🕊️ ¡{defender.nombre} está volando y es inmune a Drenadoras!")
            return
        defender.status = "infectado"
        defender.leech_seed_from = attacker
        log_lines.append(f"🌱 ¡{defender.nombre} fue infectado por Drenadoras! Perderá HP cada turno.")
        return
    
    if move_name == "Sustituto":
        if not attacker.substitute:
            attacker.substitute = True
            attacker.sub_hp = max(1, attacker.max_hp // 4)
            log_lines.append(f"🎭 ¡{attacker.nombre} creó un sustituto con {attacker.sub_hp} HP!")
        else:
            log_lines.append(f"❌ {attacker.nombre} ya tiene un sustituto.")
        return
    
    if move_name == "Danza Espada":
        attacker.mods["atk"] = clamp(attacker.mods["atk"] + 2, -6, 6)
        log_lines.append(f"📈 ¡El Ataque de {attacker.nombre} subió mucho!")
        return
    
    if move_name == "Doble Equipo":
        attacker.mods["evasion"] = clamp(attacker.mods["evasion"] + 1, -6, 6)
        evasion_percent = {0: 100, 1: 133, 2: 166, 3: 200, 4: 250, 5: 300, 6: 350}
        current = evasion_percent.get(attacker.mods["evasion"], 100)
        log_lines.append(f"🌀 ¡La Evasión de {attacker.nombre} aumentó! ({current}%)")
        return
    
    if move_name == "Amnesia":
        attacker.mods["def"] = clamp(attacker.mods["def"] + 2, -6, 6)
        log_lines.append(f"🛡️ ¡La Defensa de {attacker.nombre} subió mucho!")
        return
    
    if move_name == "Destello" and move["poder"] == 0:
        defender.mods["evasion"] = clamp(defender.mods["evasion"] + 1, -6, 6)
        evasion_percent = {0: 100, 1: 133, 2: 166, 3: 200, 4: 250, 5: 300, 6: 350}
        current = evasion_percent.get(defender.mods["evasion"], 100)
        log_lines.append(f"✨ ¡La Precisión de {defender.nombre} bajó! (Evasión rival: {current}%)")
        return
    
    if move_name == "Bostezo" and defender.status is None:
        if defender_flying:
            log_lines.append(f"🕊️ ¡{defender.nombre} está volando y es inmune al Bostezo!")
            return
        defender.sleep_next = True
        log_lines.append(f"😴 ¡{defender.nombre} siente sueño! Se dormirá al siguiente turno.")
        return
    
    if move_name == "Canto" and defender.status is None:
        if defender_flying:
            log_lines.append(f"🕊️ ¡{defender.nombre} está volando y es inmune al Canto!")
            return
        defender.status = "sleep"
        defender.status_turns = random.randint(2, 3)
        log_lines.append(f"🎵 ¡{defender.nombre} fue dormido por el Canto!")
        return
    
    if move_name == "Deseo":
        attacker.wish_heal = int(attacker.max_hp * 0.5)
        log_lines.append(f"✨ {attacker.nombre} tiene un Deseo. ¡Curará {attacker.wish_heal} HP al siguiente turno!")
        return
    
    if move_name == "Campana Cura":
        attacker.status = None
        if hasattr(attacker, 'team'):
            for p in attacker.team:
                p.status = None
        log_lines.append(f"🔔 ¡Campana Cura! Todos los problemas de estado del equipo fueron curados.")
        return
    
    if move_name == "Proteccion":
        success_prob = [1.0, 0.5, 0.25, 0.125]
        prob = success_prob[min(attacker.protect_fail_count, 3)]
        if rand(prob):
            log_lines.append(f"🛡️ {attacker.nombre} se protegió!")
            attacker.protect_success = True
            attacker.protect_fail_count += 1
            attacker.is_protected = True
        else:
            log_lines.append(f"❌ ¡{attacker.nombre} falló al usar Protección!")
            attacker.protect_success = False
            attacker.protect_fail_count = 0
            attacker.is_protected = False
        return
    
    # Vuelo/Bote: Primer turno (solo carga, sin daño)
    # El PP se consume aquí (turno 1)
    if move_name in ["Vuelo", "Bote"] and attacker.flying_turns == 0 and not getattr(attacker, 'flying_active', False):
        attacker.flying_turns = 2
        attacker.flying_move = move["nombre"]
        attacker.flying_active = True
        # Consumir PP aquí (turno 1)
        if move["pp"] > 0:
            move["pp"] -= 1
        log_lines.append(f"🕊️ {attacker.nombre} comenzó a volar (turno 1). Atacará automáticamente el próximo turno.")
        return
    
    if move_name == "Descanso":
        attacker.status = "sleep"
        attacker.status_turns = 3
        attacker.current_hp = attacker.max_hp
        log_lines.append(f"💤 {attacker.nombre} usó Descanso y recuperó toda su vida, pero se durmió por 2 turnos!")
        return
    
    if move_name == "Mofa":
        defender.taunted = True
        defender.taunted_turns = 3
        log_lines.append(f"😤 ¡{defender.nombre} ha sido provocado! Solo podrá usar movimientos de daño.")
        return
    
    if "2-3 turnos luego confunde" in move["efecto"].lower():
        if not attacker.outrage_active and not attacker.outrage_locked:
            attacker.outrage_active = True
            attacker.outrage_turns = random.randint(2, 3)
            attacker.outrage_locked = True
            log_lines.append(f"😤 ¡{attacker.nombre} se enfureció por {attacker.outrage_turns} turnos! Solo podrá usar Enfado y no podrá cambiar.")
        return
    
    # 3. Peligros
    
    if move_name == "Trampa Rocas":
        if is_player_attacking:
            ai_hazards["stealth_rock"] = True
            log_lines.append(f"🪨 ¡{attacker.nombre} colocó Trampa Rocas en el campo rival!")
        else:
            player_hazards["stealth_rock"] = True
            log_lines.append(f"🪨 ¡{attacker.nombre} colocó Trampa Rocas en tu campo!")
        return
    
    if move_name == "Puas":
        if is_player_attacking:
            # El jugador ataca, coloca púas en el campo de la IA (rival)
            if ai_hazards["spikes"] < 3:
                ai_hazards["spikes"] += 1
                log_lines.append(f"📌 ¡{attacker.nombre} colocó una capa de púas en el campo rival! (Nivel {ai_hazards['spikes']}/3)")
        else:
            # La IA ataca, coloca púas en el campo del jugador
            if player_hazards["spikes"] < 3:
                player_hazards["spikes"] += 1
                log_lines.append(f"📌 ¡{attacker.nombre} colocó una capa de púas en tu campo! (Nivel {player_hazards['spikes']}/3)")
        return
    
    if move_name == "Puas Toxicas":
        if is_player_attacking:
            if ai_hazards["toxic_spikes"] < 2:
                ai_hazards["toxic_spikes"] += 1
                log_lines.append(f"☠️ ¡{attacker.nombre} colocó una capa de púas tóxicas! (Nivel {ai_hazards['toxic_spikes']}/2)")
        else:
            if player_hazards["toxic_spikes"] < 2:
                player_hazards["toxic_spikes"] += 1
                log_lines.append(f"☠️ ¡{attacker.nombre} colocó una capa de púas tóxicas en tu campo! (Nivel {player_hazards['toxic_spikes']}/2)")
        return
    
    if move_name == "Despejar":
        if is_player_attacking:
            ai_hazards["stealth_rock"] = False
            ai_hazards["spikes"] = 0
            ai_hazards["toxic_spikes"] = 0
            log_lines.append(f"🧹 ¡{attacker.nombre} eliminó todas las trampas del campo rival!")
        else:
            player_hazards["stealth_rock"] = False
            player_hazards["spikes"] = 0
            player_hazards["toxic_spikes"] = 0
            log_lines.append(f"🧹 ¡{attacker.nombre} eliminó todas las trampas de tu campo!")
        return
    
    # 4. Movimientos Especiales
    
    if move_name in ["Gigadrenado", "Puño Drenaje"]:
        return
    
    if "recupera 50%" in effect or move_name in ["Recuperacion", "Respiro"]:
        heal = int(attacker.max_hp * 0.5)
        attacker.heal(heal)
        log_lines.append(f"💊 {attacker.nombre} recuperó {heal} HP!")
        return
    
    if move_name == "Síntesis":
        heal = int(attacker.max_hp * 0.25)
        attacker.heal(heal)
        log_lines.append(f"🌿 {attacker.nombre} recuperó {heal} HP con Síntesis!")
        return
    
    if move_name == "Agilidad":
        attacker.mods["spe"] = clamp(attacker.mods["spe"] + 2, -6, 6)
        log_lines.append(f"⚡ ¡La Velocidad de {attacker.nombre} aumentó mucho!")
        return
    
    if move_name == "Impulso":
        attacker.mods["spe"] = clamp(attacker.mods["spe"] + 1, -6, 6)
        log_lines.append(f"⚡ ¡La Velocidad de {attacker.nombre} aumentó!")
        return
    
    if move_name == "Danza Dragon":
        attacker.mods["atk"] = clamp(attacker.mods["atk"] + 1, -6, 6)
        attacker.mods["spe"] = clamp(attacker.mods["spe"] + 1, -6, 6)
        log_lines.append(f"📈 ¡El Ataque y Velocidad de {attacker.nombre} subieron!")
        return
    
    if move_name == "Danza Aleteo":
        attacker.mods["atk"] = clamp(attacker.mods["atk"] + 1, -6, 6)
        attacker.mods["def"] = clamp(attacker.mods["def"] + 1, -6, 6)
        attacker.mods["spe"] = clamp(attacker.mods["spe"] + 1, -6, 6)
        log_lines.append(f"🦋 ¡El Ataque, Defensa y Velocidad de {attacker.nombre} subieron!")
        return
    
    if move_name == "Paz Mental":
        attacker.mods["atk"] = clamp(attacker.mods["atk"] + 2, -6, 6)
        log_lines.append(f"📈 ¡El Ataque Especial de {attacker.nombre} subió mucho!")
        return
    
    if move_name == "Calma Mental":
        attacker.mods["atk"] = clamp(attacker.mods["atk"] + 2, -6, 6)
        log_lines.append(f"📈 ¡El Ataque Especial de {attacker.nombre} subió mucho!")
        return
    
    if move_name == "Foco Energía":
        log_lines.append(f"✨ ¡{attacker.nombre} concentró su energía! Mayor probabilidad de golpe crítico.")
        return
    
    if move_name == "Malicioso":
        defender.mods["def"] = clamp(defender.mods["def"] - 1, -6, 6)
        log_lines.append(f"📉 ¡La Defensa de {defender.nombre} bajó!")
        return
    
    if move_name == "Cascada" and rand(0.2):
        log_lines.append(f"💫 ¡{defender.nombre} retrocedió por la fuerza de Cascada!")
        return
    
    if move_name == "Avalancha" and rand(0.3):
        log_lines.append(f"💫 ¡{defender.nombre} retrocedió por la fuerza de Avalancha!")
        return
    
    if move_name == "Pulso Umbrío" and rand(0.2):
        log_lines.append(f"💫 ¡{defender.nombre} retrocedió por Pulso Umbrío!")
        return