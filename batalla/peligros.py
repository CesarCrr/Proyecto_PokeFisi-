from batalla.tabla_tipos import get_type_multiplier

def apply_hazards_on_switch(pokemon, hazards, is_player):
    damage   = 0
    messages = []

    # Trampa Rocas
    if hazards["stealth_rock"]:
        mult = get_type_multiplier("Roca", pokemon.tipo1, pokemon.tipo2)
        if mult > 0:
            rock_damage = int(pokemon.max_hp * (0.125 * mult))
            damage += rock_damage
            messages.append(f" ¡Trampa Rocas! {pokemon.nombre} recibe {rock_damage} de daño.")
        else:
            messages.append(f" Trampa Rocas no afecta a {pokemon.nombre}.")

    # Púas
    if hazards["spikes"] > 0:
        if pokemon.tipo1 == "Volador" or pokemon.tipo2 == "Volador":
            messages.append(f" {pokemon.nombre} es tipo Volador y evita las púas.")
        else:
            pct = {1: 1/8, 2: 1/6, 3: 1/4}[min(hazards["spikes"], 3)]
            spike_damage = int(pokemon.max_hp * pct)
            damage += spike_damage
            messages.append(f" ¡Púas! {pokemon.nombre} recibe {spike_damage} de daño.")

    # Púas Tóxicas
    if hazards["toxic_spikes"] > 0 and pokemon.status is None:
        if pokemon.tipo1 == "Veneno" or pokemon.tipo2 == "Veneno":
            messages.append(f" {pokemon.nombre} absorbe las púas tóxicas.")
            hazards["toxic_spikes"] = 0
        elif pokemon.tipo1 == "Acero" or pokemon.tipo2 == "Acero":
            messages.append(f" {pokemon.nombre} es inmune a las púas tóxicas.")
        else:
            if hazards["toxic_spikes"] == 1:
                pokemon.status = "poison"
                pokemon.poison_counter = 1
                messages.append(f" ¡Púas tóxicas! {pokemon.nombre} fue envenenado.")
            else:
                pokemon.status = "toxic"
                pokemon.poison_counter = 1
                messages.append(f" ¡Púas tóxicas! {pokemon.nombre} fue gravemente envenenado.")

    if damage > 0:
        pokemon.apply_damage(damage, True)
        if pokemon.current_hp <= 0:
            pokemon.fainted = True
            messages.append(f" ¡{pokemon.nombre} fue derrotado por las trampas!")

    return messages
