class ParametrosEconomicos:
    """Parámetros económicos y ambientales."""

    def __init__(
        self,
        costo_punta=0.28,
        costo_normal=0.238,
        costo_gas_m3=1.35,
        horas_punta=(18, 23),
        factor_co2_gas=2.09,
        factor_co2_elec=0.35,
    ):
        self.costo_punta = costo_punta
        self.costo_normal = costo_normal
        self.costo_gas_m3 = costo_gas_m3
        self.horas_punta = horas_punta
        self.factor_co2_gas = factor_co2_gas
        self.factor_co2_elec = factor_co2_elec

    def actualizar(
        self,
        punta=None,
        normal=None,
        gas_m3=None,
        horas=None,
        factor_gas=None,
        factor_elec=None,
    ):
        """Actualiza costos, horas o factores de emisión."""
        if punta is not None:
            self.costo_punta = punta
        if normal is not None:
            self.costo_normal = normal
        if gas_m3 is not None:
            self.costo_gas_m3 = gas_m3
        if horas is not None:
            self.horas_punta = horas
        if factor_gas is not None:
            self.factor_co2_gas = factor_gas
        if factor_elec is not None:
            self.factor_co2_elec = factor_elec
