import math


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
    """Calcula costos de carga integrando cruces entre franjas horarias."""

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

    def es_punta(self, hora_actual):
        """Indica si una hora absoluta está dentro de la franja punta."""
        hora = hora_actual % 24
        inicio, fin = self.horas_punta
        if inicio <= fin:
            return inicio <= hora < fin
        return hora >= inicio or hora < fin

    def tarifa(self, hora_actual):
        """Devuelve la tarifa aplicable en la hora indicada."""
        return self.costo_punta if self.es_punta(hora_actual) else self.costo_normal

    def calcular_costo_carga(self, hora_actual, capacidad_carga, duracion=0):
        """Calcula el costo de carga para energía y duración dadas.

        Si ``duracion`` es cero se aplica la tarifa de la hora inicial, manteniendo
        compatibilidad con usos antiguos. Si se indica duración, la energía se
        distribuye uniformemente y se integra por hora para no sobrerrepresentar
        cargas que cruzan de punta a fuera de punta o viceversa.
        """
        if duracion <= 0:
            return capacidad_carga * self.tarifa(hora_actual)

        restante = duracion
        cursor = hora_actual
        costo_total = 0.0
        while restante > 1e-9:
            siguiente_hora = math.floor(cursor) + 1
            paso = min(restante, siguiente_hora - cursor)
            if paso <= 1e-9:
                paso = restante
            energia_paso = capacidad_carga * paso / duracion
            costo_total += energia_paso * self.tarifa(cursor)
            cursor += paso
            restante -= paso
        return costo_total
