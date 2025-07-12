"""Perfil horario de tráfico para Lima.

Esta función devuelve un factor que representa la intensidad del tráfico a lo
largo del día. Se puede emplear para ajustar el consumo de los autobuses
según la hora en que circulan.
"""

# Factores horarios de tráfico para la ciudad de Lima.
# Un valor de 1.0 indica tráfico normal. Valores mayores
# representan congestión y pueden usarse como multiplicadores
# del consumo energético.
FACTORES_LIMA = {
    0: 0.6,
    1: 0.6,
    2: 0.5,
    3: 0.5,
    4: 0.5,
    5: 0.7,
    6: 1.0,
    7: 1.3,
    8: 1.3,
    9: 1.1,
    10: 1.0,
    11: 1.0,
    12: 1.1,
    13: 1.1,
    14: 1.1,
    15: 1.2,
    16: 1.3,
    17: 1.4,
    18: 1.4,
    19: 1.3,
    20: 1.1,
    21: 1.0,
    22: 0.8,
    23: 0.7,
}

ESTILO_MEJOR = "seaborn-v0_8"


def factor_trafico(hora, factores=FACTORES_LIMA):
    """Devuelve el factor de tráfico para la hora indicada (0-23)."""
    hora_int = int(hora) % 24
    return factores.get(hora_int, 1.0)

def graficar_trafico(factores=FACTORES_LIMA, block=True):
    """Muestra un gráfico con la evolución diaria del tráfico.

    Parameters
    ----------
    factores : dict, optional
        Mapeo hora-factor de tráfico a graficar.
    block : bool, optional
        Si ``True`` la ventana del gráfico es bloqueante.  Se pasa como
        argumento desde la interfaz para evitar congelar la aplicación.
    """
    try:
        import matplotlib.pyplot as plt
        plt.style.use(ESTILO_MEJOR)
    except Exception:
        print("Falta matplotlib. Ejecuta 'pip install -r requirements.txt'")
        return

    horas = list(range(24))
    valores = [factores.get(h, 1.0) for h in horas]

    plt.figure(figsize=(8, 4))
    plt.plot(horas, valores, marker="o")
    plt.xlabel("Hora del día")
    plt.ylabel("Factor de tráfico")
    plt.title("Perfil de tráfico para Lima")
    plt.grid(True)
    plt.tight_layout()
    plt.show(block=block)


if __name__ == "__main__":  # pragma: no cover
    graficar_trafico()
