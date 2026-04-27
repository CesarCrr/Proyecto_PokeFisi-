from batalla.tabla_tipos import get_type_multiplier

def apply_hazards_on_switch(pokemon, hazards, is_player):

    damage = 0
    messages = []
    
    print(f"DEBUG apply_hazards: {pokemon.nombre} entra, is_player={is_player}")
    print(f"  hazards recibidos: stealth_rock={hazards['stealth_rock']}, spikes={hazards['spikes']}, toxic_spikes={hazards['toxic_spikes']}")
    
    # Trampa Rocas
    if hazards["stealth_rock"]:
        mult = get_type_multiplier("Roca", pokemon.tipo1, pokemon.tipo2)
        if mult > 0:
            rock_damage = int(pokemon.max_hp * (0.125 * mult))
            damage += rock_damage
            messages.append(f"🪨 ¡Trampa Rocas! {pokemon.nombre} recibe {rock_damage} de daño.")
            print(f"  TRAMPA ROCAS: daño {rock_damage}")
        else:
            messages.append(f"🪨 Trampa Rocas no afecta a {pokemon.nombre}.")
            print(f"  TRAMPA ROCAS: sin efecto (mult={mult})")
    
    # Púas
    if hazards["spikes"] > 0:
        spike_damage_percent = {1: 1/8, 2: 1/6, 3: 1/4}
        spike_damage = int(pokemon.max_hp * spike_damage_percent[hazards["spikes"]])
        if pokemon.tipo1 == "Volador" or pokemon.tipo2 == "Volador":
            messages.append(f"📌 {pokemon.nombre} es tipo Volador y evita las púas.")
        else:
            damage += spike_damage
            messages.append(f"📌 ¡Púas! {pokemon.nombre} recibe {spike_damage} de daño.")
            print(f"  PÚAS: daño {spike_damage} (nivel {hazards['spikes']})")
    
    # Púas Tóxicas
    if hazards["toxic_spikes"] > 0 and pokemon.status is None:
        if pokemon.tipo1 == "Veneno" or pokemon.tipo2 == "Veneno":
            messages.append(f"☠️ {pokemon.nombre} es tipo Veneno y absorbe las púas tóxicas.")
            hazards["toxic_spikes"] = 0
        elif pokemon.tipo1 == "Acero" or pokemon.tipo2 == "Acero":
            messages.append(f"🔩 {pokemon.nombre} es tipo Acero y es inmune a las púas tóxicas.")
        else:
            if hazards["toxic_spikes"] == 1:
                pokemon.status = "poison"
                pokemon.poison_counter = 1
                messages.append(f"☠️ ¡Púas tóxicas! {pokemon.nombre} fue envenenado.")
            else:
                pokemon.status = "toxic"
                pokemon.poison_counter = 1
                messages.append(f"☠️ ¡Púas tóxicas profundas! {pokemon.nombre} fue gravemente envenenado.")
            print(f"  PÚAS TÓXICAS: envenenado (nivel {hazards['toxic_spikes']})")
    
    if damage > 0:
        pokemon.apply_damage(damage, True)
        print(f"  Daño total aplicado: {damage}, HP restante: {pokemon.current_hp}/{pokemon.max_hp}")
        if pokemon.current_hp <= 0:
            messages.append(f"💀 ¡{pokemon.nombre} fue derrotado por las trampas!")
    
    return messages