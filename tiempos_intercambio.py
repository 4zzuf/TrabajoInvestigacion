import modelo
from modelo import param_simulacion

ESTILO_MEJOR = "seaborn-v0_8"

TIEMPO_REEMPLAZO = 4 / 60  # Tiempo fijo del intercambio en horas

def tiempo_promedio_para_autobuses(numero_autobuses):
    """Calcula el tiempo promedio de intercambio por autobús en minutos."""
    # Desactivar la verbosidad durante las simulaciones
    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion(max_autobuses=numero_autobuses)
    modelo.VERBOSE = anterior
    if estacion.intercambios_realizados == 0:
        return 0
    tiempo_total = (
        estacion.tiempo_espera_total
        + estacion.intercambios_realizados * TIEMPO_REEMPLAZO
    )
    return (tiempo_total / estacion.intercambios_realizados) * 60

def graficar_tiempos_intercambio(block=True):
    """Grafica el tiempo promedio de intercambio por número de autobuses.

    Parameters
    ----------
    block : bool, optional
        Indica si ``plt.show`` debe ser bloqueante. La interfaz pasa
        ``False`` para no congelar la ventana principal.
    """
    # Importar matplotlib solo cuando se ejecuta directamente para evitar
    # dependencias innecesarias al utilizar este módulo durante las pruebas.

    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return
    plt.style.use(ESTILO_MEJOR)


    max_autos = param_simulacion.max_autobuses
    valores = list(range(1, max_autos + 1))
    tiempos = [tiempo_promedio_para_autobuses(n) for n in valores]

    plt.figure(figsize=(8, 4))
    plt.plot(valores, tiempos, marker="o")
    plt.xlabel("Número de autobuses")
    plt.ylabel("Tiempo promedio de intercambio (minutos)")
    plt.title("Tiempo promedio de intercambio por número de autobuses")

    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


def tiempo_promedio_espera_baterias(numero_autobuses):
    """Devuelve el tiempo promedio que una batería cargada espera para ser usada."""
    anterior = modelo.VERBOSE
    modelo.VERBOSE = False
    estacion = modelo.ejecutar_simulacion(max_autobuses=numero_autobuses)
    modelo.VERBOSE = anterior
    if not estacion.tiempos_espera_baterias:
        return 0
    return (sum(estacion.tiempos_espera_baterias) / len(estacion.tiempos_espera_baterias)) * 60


def graficar_espera_baterias(block=True):
    """Grafica el tiempo promedio que las baterías esperan cargadas."""
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return
    plt.style.use(ESTILO_MEJOR)

    max_autos = param_simulacion.max_autobuses
    valores = list(range(1, max_autos + 1))
    tiempos = [tiempo_promedio_espera_baterias(n) for n in valores]

    plt.figure(figsize=(8, 4))
    plt.plot(valores, tiempos, marker="o")
    plt.xlabel("Número de autobuses")
    plt.ylabel("Tiempo en reserva (minutos)")
    plt.title("Espera promedio de baterías cargadas")

    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


def main():
    graficar_tiempos_intercambio()

if __name__ == '__main__':
    main()
