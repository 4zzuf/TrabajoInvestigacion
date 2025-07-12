import pytest

from managers import InventoryManager, CostManager


def test_inventory_manager_replacement_after_useful_life():
    manager = InventoryManager()
    # Simulate usage equal to vida util minus one cycle
    for _ in range(manager.vida_util_bateria - 1):
        replaced = manager.uso_bateria()
        assert replaced is False
    # Next usage should replace the battery
    replaced = manager.uso_bateria()
    assert replaced is True
    assert manager.baterias_reemplazadas == 1
    assert manager.ciclos_actuales == 0


def test_cost_manager_peak_and_off_peak_charges():
    manager = CostManager()
    capacidad = 100
    # Peak hour
    costo_punta = manager.calcular_costo_carga(19, capacidad)
    assert costo_punta == pytest.approx(capacidad * manager.costo_punta)
    # Off peak hour
    costo_normal = manager.calcular_costo_carga(10, capacidad)
    assert costo_normal == pytest.approx(capacidad * manager.costo_normal)
