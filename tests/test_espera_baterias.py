import importlib
import types
import sys

import pytest


def setup_modelo(monkeypatch):
    class DummyEnv:
        def __init__(self):
            self.now = 0
        def timeout(self, dur):
            self.now += dur
            return None
        def process(self, gen):
            return gen
    class DummyResource:
        def __init__(self, env, capacity=1):
            pass
        def request(self):
            class Req:
                def __enter__(self_inner):
                    pass
                def __exit__(self_inner, exc_type, exc, tb):
                    pass
            return Req()
    class DummyStore:
        def __init__(self, env, capacity=0):
            self.items = []
        def put(self, item):
            self.items.append(item)
        def get(self):
            return self.items.pop(0)
    simpy_stub = types.SimpleNamespace(
        Environment=DummyEnv, Resource=DummyResource, Store=DummyStore
    )
    monkeypatch.setitem(sys.modules, "simpy", simpy_stub)
    import modelo
    importlib.reload(modelo)
    return modelo, DummyEnv


def test_tiempos_espera_desde_carga(monkeypatch):
    modelo, DummyEnv = setup_modelo(monkeypatch)
    # Reducir inventario para controlar el orden
    monkeypatch.setattr(modelo.param_estacion, "baterias_iniciales", 1, raising=False)
    monkeypatch.setattr(modelo.param_estacion, "total_baterias", 1, raising=False)
    monkeypatch.setattr(modelo.param_estacion, "capacidad_estacion", 1, raising=False)

    env = DummyEnv()
    estacion = modelo.EstacionIntercambio(env, 1)

    # Primera extracción
    env.now = 1
    estacion.baterias_reserva.get()
    ingreso = estacion._ingreso_reserva.pop(0)
    estacion.tiempos_espera_baterias.append(env.now - ingreso)

    # Batería cargada nuevamente
    env.now = 5
    estacion.baterias_reserva.put(100)
    estacion._ingreso_reserva.append(env.now)

    # Siguiente uso
    env.now = 8
    estacion.baterias_reserva.get()
    ingreso = estacion._ingreso_reserva.pop(0)
    estacion.tiempos_espera_baterias.append(env.now - ingreso)

    assert estacion.tiempos_espera_baterias == [1.0, 3]
    assert estacion._ingreso_reserva == []

