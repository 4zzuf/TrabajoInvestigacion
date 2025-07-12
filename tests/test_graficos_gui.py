import sys
import types
simpy_stub = types.SimpleNamespace(Environment=type("Env", (), {}), Resource=type("Res", (), {}), Store=type("Store", (), {}))
sys.modules.setdefault("simpy", simpy_stub)

import trafico
import tiempos_intercambio

def _stub_pyplot(monkeypatch, calls):
    plt = types.SimpleNamespace(
        figure=lambda *a, **k: None,
        plot=lambda *a, **k: None,
        xlabel=lambda *a, **k: None,
        ylabel=lambda *a, **k: None,
        title=lambda *a, **k: None,
        grid=lambda *a, **k: None,
        tight_layout=lambda *a, **k: None,
        show=lambda *a, **k: calls.setdefault('block', k.get('block')),
        style=types.SimpleNamespace(use=lambda *a, **k: None),
    )
    matplotlib = types.SimpleNamespace(pyplot=plt)
    monkeypatch.setitem(sys.modules, 'matplotlib', matplotlib)
    monkeypatch.setitem(sys.modules, 'matplotlib.pyplot', plt)


def test_graficar_trafico_calls_show(monkeypatch):
    calls = {}
    _stub_pyplot(monkeypatch, calls)
    trafico.graficar_trafico(block=False)
    assert calls['block'] is False


def test_graficar_tiempos_intercambio_calls_show(monkeypatch):
    calls = {}
    _stub_pyplot(monkeypatch, calls)
    monkeypatch.setattr(tiempos_intercambio, 'tiempo_promedio_para_autobuses', lambda n: n)
    monkeypatch.setattr(tiempos_intercambio.param_simulacion, 'max_autobuses', 3, raising=False)
    tiempos_intercambio.graficar_tiempos_intercambio(block=False)
    assert calls['block'] is False


def test_graficar_espera_baterias_calls_show(monkeypatch):
    calls = {}
    _stub_pyplot(monkeypatch, calls)
    monkeypatch.setattr(tiempos_intercambio, 'tiempo_promedio_espera_baterias', lambda n: n)
    monkeypatch.setattr(tiempos_intercambio.param_simulacion, 'max_autobuses', 2, raising=False)
    tiempos_intercambio.graficar_espera_baterias(block=False)
    assert calls['block'] is False
