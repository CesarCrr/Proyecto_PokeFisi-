#Tabla de Tipos
TYPE_CHART = {
    "Normal": {"Roca":0.5, "Acero":0.5, "Fantasma":0},
    "Fuego": {"Fuego":0.5, "Agua":0.5, "Roca":0.5, "Dragon":0.5, "Planta":2, "Hielo":2, "Bicho":2, "Acero":2},
    "Agua": {"Agua":0.5, "Planta":0.5, "Dragon":0.5, "Fuego":2, "Tierra":2, "Roca":2},
    "Planta": {"Fuego":0.5, "Planta":0.5, "Veneno":0.5, "Volador":0.5, "Bicho":0.5, "Dragon":0.5, "Acero":0.5, "Agua":2, "Tierra":2, "Roca":2},
    "Electrico": {"Planta":0.5, "Electrico":0.5, "Dragon":0.5, "Tierra":0, "Agua":2, "Volador":2},
    "Hielo": {"Agua":0.5, "Planta":0.5, "Hielo":0.5, "Acero":0.5, "Fuego":0.5, "Dragon":2, "Volador":2, "Tierra":2, "Planta":2},
    "Lucha": {"Veneno":0.5, "Volador":0.5, "Psiquico":0.5, "Bicho":0.5, "Hada":0.5, "Fantasma":0, "Normal":2, "Hielo":2, "Roca":2, "Siniestro":2, "Acero":2},
    "Veneno": {"Veneno":0.5, "Tierra":0.5, "Roca":0.5, "Fantasma":0.5, "Acero":0, "Planta":2, "Hada":2},
    "Tierra": {"Planta":0.5, "Bicho":0.5, "Volador":0, "Electrico":2, "Fuego":2, "Veneno":2, "Roca":2, "Acero":2},
    "Volador": {"Electrico":0.5, "Roca":0.5, "Acero":0.5, "Planta":2, "Lucha":2, "Bicho":2},
    "Psiquico": {"Psiquico":0.5, "Acero":0.5, "Siniestro":0, "Lucha":2, "Veneno":2},
    "Bicho": {"Fuego":0.5, "Lucha":0.5, "Volador":0.5, "Fantasma":0.5, "Acero":0.5, "Hada":0.5, "Planta":2, "Psiquico":2, "Siniestro":2},
    "Roca": {"Lucha":0.5, "Tierra":0.5, "Acero":0.5, "Normal":2, "Fuego":2, "Volador":2, "Bicho":2, "Hielo":2},
    "Fantasma": {"Normal":0, "Psiquico":2, "Fantasma":2, "Siniestro":0.5},
    "Dragon": {"Acero":0.5, "Hada":0, "Dragon":2},
    "Siniestro": {"Lucha":0.5, "Siniestro":0.5, "Hada":0.5, "Psiquico":2, "Fantasma":2},
    "Acero": {"Fuego":0.5, "Agua":0.5, "Electrico":0.5, "Acero":0.5, "Roca":2, "Hielo":2, "Hada":2},
    "Hada": {"Fuego":0.5, "Veneno":0.5, "Acero":0.5, "Dragon":2, "Lucha":2, "Siniestro":2}
}

def get_type_multiplier(atk_tipo, def_tipo1, def_tipo2):
    mult = 1.0
    chart = TYPE_CHART.get(atk_tipo, {})
    if def_tipo1 and def_tipo1 != "None":
        mult *= chart.get(def_tipo1, 1.0)
    if def_tipo2 and def_tipo2 != "None":
        mult *= chart.get(def_tipo2, 1.0)
    return mult