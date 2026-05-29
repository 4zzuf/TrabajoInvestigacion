class ParametrosBateria:
    """Parámetros relacionados a la batería y curva de carga."""

    def __init__(self, capacidad=300, soc_objetivo=90):
        self.capacidad = capacidad
        self.soc_objetivo = soc_objetivo
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
        self.validar()

    def validar(self):
        """Valida rangos físicos básicos de la batería."""
        if self.capacidad <= 0:
            raise ValueError("La capacidad de la batería debe ser positiva")
        if not 0 < self.soc_objetivo <= 100:
            raise ValueError("El SoC objetivo debe estar entre 0 y 100")

    def actualizar(self, potencia=None, capacidad=None, soc_objetivo=None):
        """Actualiza los valores de la batería según se necesite."""
        anterior = (self.capacidad, self.soc_objetivo)
        if potencia is not None:
            # Mantenido por compatibilidad: no se utiliza directamente.
            pass
        if capacidad is not None:
            self.capacidad = capacidad
        if soc_objetivo is not None:
            self.soc_objetivo = soc_objetivo
        try:
            self.validar()
        except Exception:
            self.capacidad, self.soc_objetivo = anterior
            raise

    def potencia_carga(self, soc):
        """Devuelve la potencia de carga en kW para el SoC dado."""
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
        objetivo = self.soc_objetivo if soc_objetivo is None else min(soc_objetivo, 100)
        soc = max(0, min(soc_inicial, objetivo))
        energia_por_pct = self.capacidad / 100
        tiempo = 0.0
        while soc < objetivo:
            sig = min(soc + 1, objetivo)
            potencia = self.potencia_carga(soc)
            energia = (sig - soc) * energia_por_pct
            tiempo += energia / potencia
            soc = sig
        return tiempo
