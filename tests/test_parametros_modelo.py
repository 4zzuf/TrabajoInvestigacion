import types
import sys
import pytest

from parametros import ParametrosBateria

# Crear un stub de simpy para permitir importar ``modelo`` sin la dependencia
simpy_stub = types.SimpleNamespace(
    Environment=type("Env", (), {}),
    Resource=type("Res", (), {}),
    Store=type("Store", (), {}),
)
sys.modules.setdefault("simpy", simpy_stub)

import modelo


def test_tiempo_carga_default_section():
    bateria = ParametrosBateria()
    tiempo = bateria.tiempo_carga(80)
    assert tiempo == pytest.approx(0.6)


def test_tiempo_carga_custom_range():
    bateria = ParametrosBateria(capacidad=100)
    tiempo = bateria.tiempo_carga(0, 20)
    expected = 0.0
    for soc in range(0, 20):
        expected += 1 / bateria.potencia_carga(soc)
    assert tiempo == pytest.approx(expected)


def test_ejecutar_simulacion_basic_flow(monkeypatch):
    events = {}

    class DummyEnv:
        def process(self, proc):
            events['process'] = True
            return proc

        def run(self, until=None):
            events['run_until'] = until

    monkeypatch.setattr(modelo, 'simpy', types.SimpleNamespace(Environment=DummyEnv))

    class DummyEstacion:
        def __init__(self, env, capacidad):
            self.env = env
            self.capacidad = capacidad

    monkeypatch.setattr(modelo, 'EstacionIntercambio', DummyEstacion)

    def dummy_llegada(env, estacion, max_autobuses, tiempo_ruta):
        events['llegada'] = (max_autobuses, tiempo_ruta)
        return "dummy"

    monkeypatch.setattr(modelo, 'llegada_autobuses', dummy_llegada)

    estacion = modelo.ejecutar_simulacion(max_autobuses=2, duracion=5, tiempo_ruta=1)

    assert isinstance(estacion, DummyEstacion)
    assert events['process'] is True
    assert events['run_until'] == 5
    assert events['llegada'] == (2, 1)


def test_inventario_suficiente_hasta_fin_punta(monkeypatch):
    estacion = types.SimpleNamespace(baterias_reserva=types.SimpleNamespace(items=[0]*25))
    assert modelo.inventario_suficiente_hasta_fin_punta(estacion, 19) is True
    estacion.baterias_reserva.items = [0]*10
    assert modelo.inventario_suficiente_hasta_fin_punta(estacion, 19) is False
    # Fuera de hora punta siempre es True
    assert modelo.inventario_suficiente_hasta_fin_punta(estacion, 12) is True
