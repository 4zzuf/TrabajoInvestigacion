class ParametrosBateria:
    """Parámetros relacionados a la batería y curva de carga."""

    def __init__(self, capacidad=300, soc_objetivo=90):
        self.capacidad = capacidad
        # El SoC objetivo se reduce a 90 % por defecto
        self.soc_objetivo = soc_objetivo
        # Coordenadas (SoC, potencia) que definen la curva de carga.  La potencia
        # para valores intermedios se obtiene por interpolación lineal entre los
        # puntos adyacentes. Los valores mantienen la forma general "subida –
        # meseta – caída" pero con algo más de irregularidad para reflejar una
        # curva menos idealizada.
        self.puntos_curva = [
            (0, 50),
            (10, 90),
            (20, 150),
            (40, 160),
            (55, 140),
            (65, 120),
            (72, 80),
            (80, 50),
            (100, 50),
        ]

    def actualizar(self, potencia=None, capacidad=None, soc_objetivo=None):
        """Actualiza los valores de la batería según se necesite."""
        if potencia is not None:
            # Mantenido por compatibilidad: no se utiliza directamente
            pass
        if capacidad is not None:
            self.capacidad = capacidad
        if soc_objetivo is not None:
            self.soc_objetivo = soc_objetivo

    def potencia_carga(self, soc):
        """Devuelve la potencia de carga en kW para el SoC dado.

        Los puntos de ``self.puntos_curva`` se ordenan por nivel de carga y se
        interpola linealmente en el intervalo que contenga ``soc``.
        """

        soc = max(0, min(soc, 100))
        puntos = sorted(self.puntos_curva, key=lambda p: p[0])

        if soc <= puntos[0][0]:
            return puntos[0][1]

        for (s0, p0), (s1, p1) in zip(puntos, puntos[1:]):
            if s0 <= soc <= s1:
                factor = (soc - s0) / (s1 - s0)
                return p0 + factor * (p1 - p0)

        return puntos[-1][1]

    def tiempo_carga(self, soc_inicial, soc_objetivo=None):
        """Tiempo necesario para cargar desde ``soc_inicial`` hasta el objetivo."""
        objetivo = self.soc_objetivo if soc_objetivo is None else soc_objetivo
        objetivo = min(objetivo, 100)
        soc = max(0, soc_inicial)
        energia_por_pct = self.capacidad / 100
        tiempo = 0.0
        while soc < objetivo:
            sig = min(soc + 1, objetivo)
            potencia = self.potencia_carga(soc)
            energia = (sig - soc) * energia_por_pct
            tiempo += energia / potencia
            soc = sig
        return tiempo
