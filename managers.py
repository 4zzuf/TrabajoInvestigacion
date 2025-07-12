class InventoryManager:
    """Gestiona las baterías disponibles y su vida útil."""

    def __init__(self, vida_util_bateria=1000):
        self.vida_util_bateria = vida_util_bateria
        self.ciclos_actuales = 0
        self.baterias_reemplazadas = 0

    def actualizar_vida_util(self, nueva_vida):
        """Permite modificar la vida útil de la batería."""
        self.vida_util_bateria = nueva_vida

    def uso_bateria(self, ciclos=1):
        """Registra el uso de la batería."""
        self.ciclos_actuales += ciclos
        if self.ciclos_actuales >= self.vida_util_bateria:
            self.baterias_reemplazadas += 1
            self.ciclos_actuales = 0
            return True
        return False

    def reiniciar(self):
        """Restablece los contadores del inventario."""
        self.ciclos_actuales = 0
        self.baterias_reemplazadas = 0


class CostManager:
    """Calcula el costo de carga según la franja horaria."""

    def __init__(self, costo_punta=0.28, costo_normal=0.238, horas_punta=(18, 23)):
        self.costo_punta = costo_punta
        self.costo_normal = costo_normal
        self.horas_punta = horas_punta

    def actualizar_costos(self, punta=None, normal=None):
        """Permite actualizar los costos de energía."""
        if punta is not None:
            self.costo_punta = punta
        if normal is not None:
            self.costo_normal = normal

    def actualizar_horas_punta(self, horas):
        """Permite cambiar la franja horaria considerada punta."""
        self.horas_punta = horas

    def calcular_costo_carga(self, hora_actual, capacidad_carga):
        """Calcula el costo de carga para la capacidad dada."""
        if self.horas_punta[0] <= hora_actual < self.horas_punta[1]:
            return capacidad_carga * self.costo_punta
        return capacidad_carga * self.costo_normal
