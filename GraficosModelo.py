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
TIEMPO_REEMPLAZO = modelo.TIEMPO_REEMPLAZO


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


def _simular_silencioso(**kwargs):
    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion(**kwargs)
    modelo.VERBOSE = anterior
    return estacion


def _simular_con_registro():
    """Ejecuta la simulación registrando datos horarios."""
    datos = {
        "cargadas": [],
        "descargadas": [],
        "cargando": [],
        "espera": [],
        "potencia": [],
        "energia_hora": [],
    }

    def registrar(env, estacion):
        for h in range(int(param_simulacion.duracion) + 1):
            datos["cargadas"].append(len(estacion.baterias_reserva.items))
            datos["descargadas"].append(len(estacion.baterias_descargadas.items))
            datos["cargando"].append(estacion.baterias_cargando)
            datos["espera"].append(estacion.tiempo_espera_total)
            muestras = estacion.muestras_potencia_por_hora.get(h, 0)
            potencia = estacion.potencia_por_hora.get(h, 0) / muestras if muestras else 0
            datos["potencia"].append(potencia)
            datos["energia_hora"].append(estacion.energia_cargada_por_hora.get(h, 0))
            yield env.timeout(1)

    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion(procesos_extra=[registrar])
    modelo.VERBOSE = anterior
    return estacion, datos


def grafico_carga_bateria(block: bool = True):
    """Grafica la curva de potencia de carga según el SoC."""
    import matplotlib.pyplot as plt

    bateria = ParametrosBateria()
    soc_vals = list(range(0, bateria.soc_objetivo + 1))
    potencias = [bateria.potencia_carga(s) for s in soc_vals]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(8, 4))
    plt.plot(soc_vals, potencias, marker="o")
    plt.axvline(bateria.soc_objetivo, color="tab:red", linestyle="--", label="SoC objetivo")
    plt.xlabel("Estado de carga (%)")
    plt.ylabel("Potencia de carga (kW)")
    plt.title("Curva de carga de la batería")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


def _costos_para_autobuses(numero_autobuses):
    """Devuelve costos y consumos simulados para la cantidad dada de autobuses."""
    cap_ant = param_estacion.capacidad_estacion
    tot_ant = param_estacion.total_baterias
    ini_ant = param_estacion.baterias_iniciales
    max_ant = param_simulacion.max_autobuses
    try:
        param_simulacion.actualizar(max_autobuses=numero_autobuses)
        param_estacion.actualizar(
            capacidad=max(numero_autobuses, cap_ant),
            total=max(numero_autobuses * 2, tot_ant),
            iniciales=max(numero_autobuses, ini_ant),
        )
        estacion = _simular_silencioso(max_autobuses=numero_autobuses)
    finally:
        param_estacion.actualizar(capacidad=cap_ant, total=tot_ant, iniciales=ini_ant)
        param_simulacion.actualizar(max_autobuses=max_ant)

    energia_punta = estacion.energia_punta_electrica
    energia_fuera = estacion.energia_total_cargada - estacion.energia_punta_electrica
    return (
        estacion.costo_total_electrico,
        estacion.costo_total_gas,
        energia_punta,
        energia_fuera,
        estacion.tiempo_espera_total,
    )


def costo_gas_teorico(numero_autobuses, tiempo_ruta=37.2):
    """Calcula un costo gas simplificado; se conserva por compatibilidad."""
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
    """Genera gráficos comparativos de costos y consumo eléctrico."""
    import matplotlib.pyplot as plt

    max_autos = param_simulacion.max_autobuses
    valores = list(range(1, max_autos + 1))
    resultados = [_costos_para_autobuses(n) for n in valores]
    costos_elec, costos_gas, energias_punta, energias_fuera, esperas = zip(*resultados)

    plt.style.use(ESTILO_MEJOR)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8))

    axes[0, 0].plot(valores, costos_elec, marker="o", label="Electricidad")
    axes[0, 0].plot(valores, costos_gas, marker="s", label="Gas natural")
    axes[0, 0].set_xlabel("Número de autobuses")
    axes[0, 0].set_ylabel("Costo (S/.)")
    axes[0, 0].set_title("Comparación de costos de operación")
    axes[0, 0].legend()
    axes[0, 0].grid(True)

    axes[0, 1].plot(valores, energias_punta, marker="o", label="Hora punta eléctrica")
    axes[0, 1].plot(valores, energias_fuera, marker="s", label="Fuera de punta")
    axes[0, 1].set_xlabel("Número de autobuses")
    axes[0, 1].set_ylabel("Consumo eléctrico (kWh)")
    axes[0, 1].set_title("Energía por franja tarifaria")
    axes[0, 1].legend()
    axes[0, 1].grid(True)

    axes[1, 0].plot(valores, [e * 60 for e in esperas], marker="^", color="tab:red")
    axes[1, 0].set_xlabel("Número de autobuses")
    axes[1, 0].set_ylabel("Espera acumulada (min)")
    axes[1, 0].set_title("Nivel de servicio: espera acumulada")
    axes[1, 0].grid(True)

    ahorro = [g - e for e, g in zip(costos_elec, costos_gas)]
    axes[1, 1].bar(valores, ahorro, color="tab:green")
    axes[1, 1].axhline(0, color="black", linewidth=0.8)
    axes[1, 1].set_xlabel("Número de autobuses")
    axes[1, 1].set_ylabel("Ahorro vs gas (S/.)")
    axes[1, 1].set_title("Diferencia económica simulada")

    fig.tight_layout()
    plt.show(block=block)


def grafico_diarios(block: bool = True):
    """Grafica intercambios y consumo diarios."""
    import matplotlib.pyplot as plt

    estacion = _simular_silencioso()
    plt.style.use(ESTILO_MEJOR)

    dias = param_simulacion.dias
    intercambios = [0] * dias
    energia = [0.0] * dias
    for dia, _, energia_swap in estacion.registro_intercambios:
        if dia < dias:
            intercambios[dia] += 1
            energia[dia] += energia_swap

    fig, axes = plt.subplots(2, 1, figsize=(9, 7), sharex=True)
    axes[0].bar(range(1, dias + 1), intercambios, color="tab:blue")
    axes[0].set_ylabel("Intercambios")
    axes[0].set_title("Intercambios operativos diarios")
    axes[0].grid(True, axis="y")

    axes[1].bar(range(1, dias + 1), energia, color="tab:orange")
    axes[1].set_xlabel("Día de operación")
    axes[1].set_ylabel("Energía (kWh)")
    axes[1].set_title("Energía requerida por intercambios")
    axes[1].grid(True, axis="y")

    fig.tight_layout()
    plt.show(block=block)


def grafico_emisiones(block: bool = True):
    """Compara emisiones y muestra el ahorro como anotación, no como fuente."""
    import matplotlib.pyplot as plt

    estacion = _simular_silencioso()
    emis_elec = estacion.energia_total_cargada * param_economicos.factor_co2_elec / 1000
    emis_gas = estacion.volumen_total_gas * param_economicos.factor_co2_gas / 1000
    ahorro = emis_gas - emis_elec
    ahorro_pct = ahorro / emis_gas * 100 if emis_gas else 0

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(6, 4))
    etiquetas = ["Electricidad", "Gas natural"]
    valores = [emis_elec, emis_gas]
    plt.bar(etiquetas, valores, color=["tab:blue", "tab:orange"])
    plt.ylabel("Toneladas de CO2")
    plt.title("Emisiones de CO2 durante la simulación")
    plt.text(
        0.5,
        max(valores) * 0.9 if valores else 0,
        f"Ahorro: {ahorro:.2f} t CO2 ({ahorro_pct:.1f}%)",
        ha="center",
        bbox={"facecolor": "white", "alpha": 0.8},
    )
    plt.tight_layout()
    plt.show(block=block)


def grafico_inventario(block: bool = True):
    """Muestra el inventario de baterías a lo largo del tiempo."""
    import matplotlib.pyplot as plt

    _, datos = _simular_con_registro()
    horas = range(len(datos["cargadas"]))
    dias = [h / 24 for h in horas]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(9, 4))
    plt.plot(dias, datos["cargadas"], label="Cargadas", marker="o", linestyle="", alpha=0.25)
    plt.plot(dias, datos["descargadas"], label="Descargadas", marker="o", linestyle="", alpha=0.25)
    plt.plot(dias, _promedio_movil(datos["cargadas"]), label="Tendencia cargadas", color="tab:blue")
    plt.plot(dias, _promedio_movil(datos["descargadas"]), label="Tendencia descargadas", color="tab:orange")
    plt.axhline(param_simulacion.max_autobuses * 0.1, color="tab:red", linestyle="--", label="Inventario mínimo sugerido")
    plt.xlabel("Día de simulación")
    plt.ylabel("Número de baterías")
    plt.title("Inventario de baterías")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


def grafico_cola(block: bool = True):
    """Grafica la evolución de la cola de autobuses."""
    import matplotlib.pyplot as plt

    _, datos = _simular_con_registro()
    espera = datos["espera"]
    espera_h = [0.0]
    for i in range(1, len(espera)):
        espera_h.append((espera[i] - espera[i - 1]) * 60)
    horas = range(len(espera_h))
    dias = [h / 24 for h in horas]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(9, 4))
    plt.plot(dias, espera_h, marker="o", linestyle="", alpha=0.3)
    plt.plot(dias, _promedio_movil(espera_h), color="tab:red", label="Tendencia")
    plt.xlabel("Día de simulación")
    plt.ylabel("Minutos de espera nuevos")
    plt.title("Evolución de la espera de autobuses")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show(block=block)


def grafico_costos_dia(block: bool = True):
    """Grafica el costo eléctrico por día de operación usando registros de carga."""
    import matplotlib.pyplot as plt

    estacion = _simular_silencioso()
    dias = param_simulacion.dias
    costos = [0.0] * dias
    for hora, costo in estacion.costo_carga_por_hora.items():
        dia = int(hora // 24)
        if dia < dias:
            costos[dia] += costo

    colores = ["tab:orange" if modelo.es_fin_de_semana(d * 24) else "tab:blue" for d in range(dias)]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(9, 4))
    plt.bar(range(1, dias + 1), costos, color=colores)
    plt.xlabel("Día de operación")
    plt.ylabel("Costo diario (S/.)")
    plt.title("Costo eléctrico operativo por día")
    plt.tight_layout()
    plt.show(block=block)


def grafico_uso_cargadores(block: bool = True):
    """Muestra la utilización porcentual de los cargadores."""
    import matplotlib.pyplot as plt

    _, datos = _simular_con_registro()
    horas = range(len(datos["cargando"]))
    dias = [h / 24 for h in horas]
    uso = [c / param_estacion.capacidad_estacion * 100 for c in datos["cargando"]]

    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(9, 4))
    plt.plot(dias, uso, marker="o", linestyle="", alpha=0.3)
    plt.plot(dias, _promedio_movil(uso), color="tab:green", label="Tendencia")
    plt.xlabel("Día de simulación")
    plt.ylabel("Uso de cargadores (%)")
    plt.title("Utilización de cargadores")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.show(block=block)


def grafico_demanda_electrica(block: bool = True):
    """Grafica energía horaria y potencia media registrada en la estación."""
    import matplotlib.pyplot as plt

    estacion = _simular_silencioso()
    horas = list(range(int(param_simulacion.duracion)))
    dias = [h / 24 for h in horas]
    energia = [estacion.energia_cargada_por_hora.get(h, 0) for h in horas]
    potencia = []
    for h in horas:
        muestras = estacion.muestras_potencia_por_hora.get(h, 0)
        potencia.append(estacion.potencia_por_hora.get(h, 0) / muestras if muestras else 0)

    plt.style.use(ESTILO_MEJOR)
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(dias, energia, color="tab:blue")
    axes[0].set_ylabel("Energía (kWh/h)")
    axes[0].set_title("Perfil horario de energía de carga")
    axes[0].grid(True)

    axes[1].plot(dias, potencia, color="tab:green")
    axes[1].set_xlabel("Día de simulación")
    axes[1].set_ylabel("Potencia media (kW)")
    axes[1].set_title("Potencia media de carga por hora")
    axes[1].grid(True)

    fig.tight_layout()
    plt.show(block=block)


def grafico_soc_retorno(block: bool = True):
    """Muestra la distribución de SoC de retorno de los buses."""
    import matplotlib.pyplot as plt

    estacion = _simular_silencioso()
    plt.style.use(ESTILO_MEJOR)
    plt.figure(figsize=(8, 4))
    plt.hist(estacion.soc_retorno, bins=20, color="tab:purple", alpha=0.8)
    plt.axvline(modelo.SOC_MIN_OPERATIVO, color="tab:red", linestyle="--", label="SoC mínimo")
    plt.xlabel("SoC al retorno (%)")
    plt.ylabel("Frecuencia")
    plt.title("Distribución del SoC al retorno")
    plt.legend()
    plt.tight_layout()
    plt.show(block=block)


def main():
    parser = argparse.ArgumentParser(description="Genera distintos gráficos del modelo de simulación")
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
            "demanda",
            "soc",
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
    elif args.grafico == "demanda":
        grafico_demanda_electrica()
    elif args.grafico == "soc":
        grafico_soc_retorno()


if __name__ == "__main__":  # pragma: no cover - ejecución manual
    main()
