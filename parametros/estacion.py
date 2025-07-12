class ParametrosEstacion:
    """Parámetros de la estación de carga."""

    def __init__(self, capacidad_estacion=21, total_baterias=41, baterias_iniciales=20):
        self.capacidad_estacion = capacidad_estacion
        self.total_baterias = total_baterias
        self.baterias_iniciales = baterias_iniciales

    def actualizar(self, capacidad=None, total=None, iniciales=None):
        """Actualiza los parámetros de la estación."""
        if capacidad is not None:
            self.capacidad_estacion = capacidad
        if total is not None:
            self.total_baterias = total
        if iniciales is not None:
            self.baterias_iniciales = iniciales
