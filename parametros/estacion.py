class ParametrosEstacion:
    """Parámetros de la estación de carga e intercambio."""

    def __init__(self, capacidad_estacion=21, total_baterias=41, baterias_iniciales=20):
        self.capacidad_estacion = capacidad_estacion
        self.total_baterias = total_baterias
        self.baterias_iniciales = baterias_iniciales
        self.validar()

    def validar(self):
        """Verifica consistencia mínima entre cargadores e inventario."""
        if self.capacidad_estacion < 1:
            raise ValueError("La capacidad de estación debe ser al menos 1")
        if self.total_baterias < 1:
            raise ValueError("El total de baterías debe ser al menos 1")
        if self.baterias_iniciales < 0:
            raise ValueError("Las baterías iniciales no pueden ser negativas")
        if self.baterias_iniciales > self.total_baterias:
            raise ValueError("Las baterías iniciales no pueden exceder el total")

    def actualizar(self, capacidad=None, total=None, iniciales=None):
        """Actualiza los parámetros de la estación."""
        anterior = (self.capacidad_estacion, self.total_baterias, self.baterias_iniciales)
        if capacidad is not None:
            self.capacidad_estacion = capacidad
        if total is not None:
            self.total_baterias = total
        if iniciales is not None:
            self.baterias_iniciales = iniciales
        try:
            self.validar()
        except Exception:
            self.capacidad_estacion, self.total_baterias, self.baterias_iniciales = anterior
            raise
