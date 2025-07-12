class ParametrosSimulacion:
    """Parámetros generales de la simulación."""

    def __init__(
        self,
        dias=21,
        max_autobuses=20,
        semilla=42,
        variacion_llegadas=0.05,
        prob_retraso=0.1,
        rango_retraso=(5 / 60, 15 / 60),
    ):
        # La duración se ingresa en días y se convierte a horas cuando es
        # necesario ejecutar la simulación.
        self.dias = dias
        self.max_autobuses = max_autobuses
        self.semilla = semilla
        # Variación aleatoria (+/- horas) aplicada a los intervalos base de
        # llegada de autobuses.
        self.variacion_llegadas = variacion_llegadas
        # Probabilidad de sufrir un retraso adicional en el intervalo.
        self.prob_retraso = prob_retraso
        # Rango de la demora extra cuando ocurre un retraso.
        self.rango_retraso = rango_retraso

    @property
    def duracion(self):
        """Duración de la simulación en horas."""
        return self.dias * 24

    def actualizar(
        self,
        dias=None,
        max_autobuses=None,
        semilla=None,
        variacion_llegadas=None,
        prob_retraso=None,
        rango_retraso=None,
    ):
        """Permite actualizar los parámetros de simulación."""
        if dias is not None:
            self.dias = dias
        if max_autobuses is not None:
            self.max_autobuses = max_autobuses
        if semilla is not None:
            self.semilla = semilla
        if variacion_llegadas is not None:
            self.variacion_llegadas = variacion_llegadas
        if prob_retraso is not None:
            self.prob_retraso = prob_retraso
        if rango_retraso is not None:
            self.rango_retraso = rango_retraso
