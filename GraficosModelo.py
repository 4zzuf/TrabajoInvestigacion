import argparse
import modelo
from modelo import (
    param_simulacion,
    param_economicos,
    param_estacion,
    param_operacion,
)
from parametros import ParametrosBateria

ESTILO_MEJOR = "seaborn-v0_8"

TIEMPO_REEMPLAZO = 4 / 60  # Tiempo de intercambio de la batería en horas


def _promedio_movil(valores, ventana=24):
    """Devuelve una lista con el promedio móvil de ``valores``."""
    promedios = []
    acumulado = 0.0
    for i, val in enumerate(valores):
        acumulado += val
        if i >= ventana:
            acumulado -= valores[i - ventana]
            promedios.append(acumulado / ventana)
        else:
            promedios.append(acumulado / (i + 1))
    return promedios


def _simular_con_registro():
    """Ejecuta la simulación registrando datos horarios."""
    datos = {
        "cargadas": [],
        "descargadas": [],
        "cargando": [],
        "espera": [],
    }

    def registrar(env, estacion):
        for _ in range(int(param_simulacion.duracion) + 1):
            datos["cargadas"].append(len(estacion.baterias_reserva.items))
            datos["descargadas"].append(len(estacion.baterias_descargadas.items))
            datos["cargando"].append(estacion.baterias_cargando)
            datos["espera"].append(estacion.tiempo_espera_total)
            yield env.timeout(1)

    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion(procesos_extra=[registrar])
    modelo.VERBOSE = anterior
    return estacion, datos


def grafico_carga_bateria(block: bool = True):
    """Grafica la curva de potencia de carga según el SoC."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return

    bateria = ParametrosBateria()
    soc_vals = list(range(0, 91))
    potencias = [bateria.potencia_carga(s) for s in soc_vals]

    plt.style.use(ESTILO_MEJOR)

    plt.figure(figsize=(8, 4))
    plt.plot(soc_vals, potencias, marker="o")
    plt.xlabel("Estado de carga (%)")
    plt.ylabel("Potencia de carga (kW)")
    plt.title("Curva de carga de la batería")
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


def _costos_para_autobuses(numero_autobuses, tiempo_ruta=37.2):
    """Devuelve costos y consumos para la cantidad dada de autobuses."""
    anterior = modelo.VERBOSE
    modelo.VERBOSE = False

    cap_ant = param_estacion.capacidad_estacion
    tot_ant = param_estacion.total_baterias
    ini_ant = param_estacion.baterias_iniciales
    param_estacion.actualizar(
        capacidad=max(numero_autobuses, cap_ant),
        total=max(numero_autobuses * 2, tot_ant),
        iniciales=max(numero_autobuses, ini_ant),
    )
    estacion = modelo.ejecutar_simulacion(max_autobuses=numero_autobuses)
    param_estacion.actualizar(capacidad=cap_ant, total=tot_ant, iniciales=ini_ant)

    modelo.VERBOSE = anterior

    # Los costos se calculan para la duración exacta de la simulación. Ya no se
    # escalan a un mes de 30 días.
    costo_electrico = estacion.costo_total_electrico
    costo_gas = costo_gas_teorico(numero_autobuses, tiempo_ruta)
    energia_punta = estacion.energia_punta_electrica
    energia_fuera = estacion.energia_total_cargada - estacion.energia_punta_electrica
    return costo_electrico, costo_gas, energia_punta, energia_fuera


def costo_gas_teorico(numero_autobuses, tiempo_ruta=37.2):
    """Calcula el costo de operar los autobuses con gas natural."""
    duracion = tiempo_ruta / param_operacion.velocidad_promedio
    ciclos = param_simulacion.duracion / duracion
    volumen_total = (
        numero_autobuses
        * param_operacion.consumo_gas_100km
        * tiempo_ruta
        / 100
        * ciclos
    )
    return volumen_total * param_economicos.costo_gas_m3


def grafico_costos(block: bool = True):
    """Genera los gráficos de costos y consumo eléctrico."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return

    max_autos = param_simulacion.max_autobuses
    valores = list(range(1, max_autos + 1))
    resultados = [_costos_para_autobuses(n) for n in valores]
    costos_elec, costos_gas, energias_punta, energias_fuera = zip(*resultados)

    plt.style.use(ESTILO_MEJOR)

    plt.figure(figsize=(8, 4))
    plt.plot(valores, costos_elec, marker="o")
    plt.xlabel("Número de autobuses")
    plt.ylabel("Costo eléctrico (S/.)")
    plt.title("Costo de operación con electricidad")
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)

    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion()
    modelo.VERBOSE = anterior

    plt.style.use(ESTILO_MEJOR)
    costo_e_hora = estacion.costo_total_electrico / param_simulacion.duracion
    costo_g_hora = estacion.costo_total_gas / param_simulacion.duracion

    plt.figure(figsize=(6, 4))
    etiquetas = ["Electricidad/hora", "Gas natural/hora"]
    valores_bar = [costo_e_hora, costo_g_hora]
    plt.bar(etiquetas, valores_bar, color=["tab:blue", "tab:orange"])
    plt.ylabel("Costo (S/./h)")
    plt.title("Costo promedio por hora de operación")
    plt.tight_layout()
    plt.show(block=block)

    plt.figure(figsize=(8, 4))
    plt.plot(valores, costos_elec, marker="o", label="Electricidad")
    plt.plot(valores, costos_gas, marker="s", label="Gas natural")
    plt.xlabel("Número de autobuses")
    plt.ylabel("Costo (S/.)")
    plt.title("Comparación de costos de operación")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)

    plt.figure(figsize=(8, 4))
    plt.plot(valores, energias_punta, marker="o", label="Hora punta")
    plt.plot(valores, energias_fuera, marker="s", label="Fuera de punta")
    plt.xlabel("Número de autobuses")
    plt.ylabel("Consumo eléctrico (kWh)")
    plt.title("Consumo en hora punta y fuera de punta")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


def grafico_diarios(block: bool = True):
    """Grafica intercambios y consumo diarios."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return
    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion()
    modelo.VERBOSE = anterior

    plt.style.use(ESTILO_MEJOR)

    dias = param_simulacion.dias
    intercambios = [0] * (dias + 1)
    energia = [0.0] * (dias + 1)
    for dia, _, energia_swap in estacion.registro_intercambios:
        if dia <= dias:
            intercambios[dia] += 1
            energia[dia] += energia_swap

    plt.figure(figsize=(8, 4))
    plt.plot(range(dias + 1), intercambios, marker="o")
    plt.xlabel("Día de operación")
    plt.ylabel("Intercambios de batería")
    plt.title("Intercambios diarios")
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)

    plt.figure(figsize=(8, 4))
    plt.plot(range(dias + 1), energia, marker="s", color="tab:orange")
    plt.xlabel("Día de operación")
    plt.ylabel("Energía cargada (kWh)")
    plt.title("Consumo diario de energía")
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


def grafico_emisiones(block: bool = True):
    """Muestra un gráfico comparando emisiones y el ahorro total de CO2."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return
    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion()
    modelo.VERBOSE = anterior

    emis_elec = (
        estacion.energia_total_cargada
        * param_economicos.factor_co2_elec
        / 1000
    )
    emis_gas = (
        estacion.volumen_total_gas
        * param_economicos.factor_co2_gas
        / 1000
    )
    ahorro = emis_gas - emis_elec

    plt.figure(figsize=(6, 4))
    etiquetas = ["Electricidad", "Gas natural", "Ahorro de CO2"]
    valores = [emis_elec, emis_gas, ahorro]
    plt.bar(etiquetas, valores, color=["tab:blue", "tab:orange", "tab:green"])
    plt.ylabel("Toneladas de CO2")
    plt.title("Emisiones de CO2 durante la simulación")

    plt.tight_layout()
    plt.show(block=block)


def grafico_inventario(block: bool = True):
    """Muestra el inventario de baterías a lo largo del tiempo."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return
    _, datos = _simular_con_registro()
    horas = range(len(datos["cargadas"]))
    dias = [h / 24 for h in horas]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(8, 4))
    plt.plot(dias, datos["cargadas"], label="Cargadas", marker="o", linestyle="", alpha=0.3)
    plt.plot(dias, datos["descargadas"], label="Descargadas", marker="o", linestyle="", alpha=0.3)
    cargadas_trend = _promedio_movil(datos["cargadas"]) 
    descargadas_trend = _promedio_movil(datos["descargadas"]) 
    plt.plot(dias, cargadas_trend, label="Tendencia cargadas", color="tab:blue")
    plt.plot(dias, descargadas_trend, label="Tendencia descargadas", color="tab:orange")
    plt.xlabel("Día de simulación")
    plt.ylabel("Número de baterías")
    plt.title("Inventario de baterías")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


def grafico_cola(block: bool = True):
    """Grafica la evolución de la cola de autobuses."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return
    _, datos = _simular_con_registro()
    espera = datos["espera"]
    espera_h = [0.0]
    for i in range(1, len(espera)):
        espera_h.append((espera[i] - espera[i - 1]) * 60)
    horas = range(len(espera_h))
    dias = [h / 24 for h in horas]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(8, 4))
    plt.plot(dias, espera_h, marker="o", linestyle="", alpha=0.3)
    trend = _promedio_movil(espera_h)
    plt.plot(dias, trend, color="tab:red", label="Tendencia")
    plt.xlabel("Día de simulación")
    plt.ylabel("Minutos de espera nuevos")
    plt.title("Evolución de la cola de autobuses")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show(block=block)


def grafico_costos_dia(block: bool = True):
    """Grafica el costo eléctrico por día de operación."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return
    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion()
    modelo.VERBOSE = anterior

    dias = param_simulacion.dias
    costos = [0.0] * dias
    for dia, hora_str, energia in estacion.registro_intercambios:
        if dia < dias:
            hora = int(hora_str.split()[2].split(":" )[0])
            if param_economicos.horas_punta[0] <= hora < param_economicos.horas_punta[1]:
                costo = energia * param_economicos.costo_punta
            else:
                costo = energia * param_economicos.costo_normal
            costos[dia] += costo

    colores = [
        "tab:orange" if modelo.es_fin_de_semana(d * 24) else "tab:blue"
        for d in range(dias)
    ]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(8, 4))
    plt.bar(range(dias), costos, color=colores)
    plt.xlabel("Día de operación")
    plt.ylabel("Costo diario (S/.)")
    plt.title("Costo eléctrico por día")
    plt.tight_layout()
    plt.show(block=block)


def grafico_uso_cargadores(block: bool = True):
    """Muestra la utilización porcentual de los cargadores."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return
    _, datos = _simular_con_registro()
    horas = range(len(datos["cargando"]))
    dias = [h / 24 for h in horas]
    uso = [
        c / param_estacion.capacidad_estacion * 100 for c in datos["cargando"]
    ]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(8, 4))
    plt.plot(dias, uso, marker="o", linestyle="", alpha=0.3)
    trend = _promedio_movil(uso)
    plt.plot(dias, trend, color="tab:green", label="Tendencia")
    plt.xlabel("Día de simulación")
    plt.ylabel("Uso de cargadores (%)")
    plt.title("Utilización de cargadores")
    plt.grid(True)

    plt.legend()

    plt.tight_layout()
    plt.show(block=block)


def main():
    parser = argparse.ArgumentParser(
        description="Genera distintos gráficos del modelo de simulación"
    )
    parser.add_argument(
        "grafico",
        choices=[
            "carga",
            "costos",
            "diarios",
            "emisiones",
            "inventario",
            "cola",
            "costosdia",
            "cargadores",
        ],
        help="Tipo de gráfico a mostrar",
    )
    args = parser.parse_args()

    if args.grafico == "carga":
        grafico_carga_bateria()
    elif args.grafico == "costos":
        grafico_costos()
    elif args.grafico == "diarios":
        grafico_diarios()
    elif args.grafico == "emisiones":
        grafico_emisiones()
    elif args.grafico == "inventario":
        grafico_inventario()
    elif args.grafico == "cola":
        grafico_cola()
    elif args.grafico == "costosdia":
        grafico_costos_dia()
    elif args.grafico == "cargadores":
        grafico_uso_cargadores()


if __name__ == "__main__":  # pragma: no cover - ejecución manual
    main()
