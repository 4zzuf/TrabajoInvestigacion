import math
import random
from collections import defaultdict

import simpy

import trafico

from parametros import (
    ParametrosBateria,
    ParametrosEstacion,
    ParametrosOperacionBus,
    ParametrosEconomicos,
    ParametrosSimulacion,
)


param_bateria = ParametrosBateria()
param_estacion = ParametrosEstacion()
param_operacion = ParametrosOperacionBus()
param_economicos = ParametrosEconomicos()
param_simulacion = ParametrosSimulacion()

# Controla la verbosidad de la simulación
VERBOSE = True

# Umbral mínimo operativo de SoC antes de exigir recambio.
SOC_MIN_OPERATIVO = 20
SOC_INICIAL_DESCARGADAS = 30
TIEMPO_REEMPLAZO = 4 / 60  # 4 minutos expresados en horas


# Función para formatear horas decimales incluyendo el día de simulación
def formato_hora(horas_decimales):
    """Devuelve un string "Día DD hh:mm" para la hora dada."""
    dia = int(horas_decimales // 24) + 1
    horas_totales = horas_decimales % 24
    horas, minutos = divmod(horas_totales * 60, 60)
    return f"Día {dia:02} {int(horas):02}:{int(minutos):02}"


def es_fin_de_semana(tiempo):
    """Devuelve ``True`` si la hora indicada corresponde a fin de semana."""
    dia_semana = int(tiempo // 24) % 7
    return dia_semana >= 5


def factor_demanda(tiempo):
    """Factor de frecuencia de autobuses según el día de la semana."""
    dia_semana = int(tiempo // 24) % 7
    if dia_semana == 5:
        return 0.7  # Sábado
    if dia_semana == 6:
        return 0.5  # Domingo
    return 1.0


def es_hora_punta_bus(hora):
    """Indica si la hora corresponde a punta operacional de buses."""
    hora = hora % 24
    return 7 <= hora < 9 or 16 <= hora < 18


def es_hora_punta_electrica(hora):
    """Indica si la hora corresponde a punta tarifaria eléctrica."""
    hora = hora % 24
    inicio, fin = param_economicos.horas_punta
    if inicio <= fin:
        return inicio <= hora < fin
    return hora >= inicio or hora < fin


def tarifa_electrica(hora):
    """Devuelve la tarifa eléctrica aplicable para una hora absoluta."""
    if es_hora_punta_electrica(hora):
        return param_economicos.costo_punta
    return param_economicos.costo_normal


def ajuste_por_trafico(hora_actual):
    """Factor moderado de ajuste energético por tráfico."""
    factor = trafico.factor_trafico(hora_actual)
    return 1 + 0.2 * (factor - 1)


def duracion_y_consumo(distancia_km, hora_actual):
    """Devuelve la duración y consumo eléctrico para la distancia dada."""
    ajuste = ajuste_por_trafico(hora_actual)
    duracion = distancia_km / param_operacion.velocidad_promedio * ajuste
    consumo = random.uniform(*param_operacion.consumo_kwh_km) * distancia_km * ajuste
    return duracion, consumo


def soc_estimado_despues(soc_actual, distancia_km, hora_actual):
    """Calcula el SoC estimado tras la siguiente vuelta sin cambiar la batería."""
    ajuste = ajuste_por_trafico(hora_actual)
    consumo_promedio = sum(param_operacion.consumo_kwh_km) / 2
    consumo = consumo_promedio * distancia_km * ajuste
    return soc_actual - consumo / param_bateria.capacidad * 100


def consumo_gas_ruta(distancia_km, hora_actual, duracion_ruta):
    """Estima volumen, costo y energía equivalente de gas para la misma ruta."""
    ajuste = ajuste_por_trafico(hora_actual)
    volumen_gas = param_operacion.consumo_gas_100km * distancia_km / 100 * ajuste
    energia_gas = param_operacion.consumo_gas_hora * duracion_ruta * ajuste
    costo_gas = volumen_gas * param_economicos.costo_gas_m3
    return volumen_gas, energia_gas, costo_gas


def intervalo_base_salida(hora_actual):
    """Intervalo base entre salidas de buses en horas."""
    if es_hora_punta_bus(hora_actual):
        return 3.5 / 60
    return 10 / 60


def intervalo_salida(tiempo):
    """Intervalo aleatorio entre salidas considerando demanda y retrasos."""
    intervalo_base = intervalo_base_salida(tiempo % 24) / factor_demanda(tiempo)
    variacion = random.uniform(
        -param_simulacion.variacion_llegadas,
        param_simulacion.variacion_llegadas,
    )
    intervalo = max(0, intervalo_base + variacion)
    if random.random() < param_simulacion.prob_retraso:
        intervalo += random.uniform(*param_simulacion.rango_retraso)
    return intervalo


def inventario_suficiente_hasta_fin_punta(estacion, hora_actual):
    """Estima si el inventario cubre la demanda hasta terminar la punta eléctrica."""
    if not es_hora_punta_electrica(hora_actual):
        return True

    inicio, fin = param_economicos.horas_punta
    hora = hora_actual % 24
    if inicio <= fin:
        horas_restantes = fin - hora
    else:
        horas_restantes = (fin - hora) % 24
    if horas_restantes <= 0:
        return True

    distancia = getattr(estacion, "tiempo_ruta", 37.2)
    ajuste = ajuste_por_trafico(hora_actual)
    duracion_ruta = distancia / param_operacion.velocidad_promedio * ajuste
    consumo_promedio = sum(param_operacion.consumo_kwh_km) / 2 * distancia * ajuste
    consumo_pct = consumo_promedio / param_bateria.capacidad * 100
    margen_util = max(param_bateria.soc_objetivo - SOC_MIN_OPERATIVO, 1)
    rutas_por_bateria = max(1, math.floor(margen_util / max(consumo_pct, 1)))
    ciclo_horas = max(duracion_ruta * rutas_por_bateria, 1 / 60)
    demanda_esperada = math.ceil(
        param_simulacion.max_autobuses * horas_restantes / ciclo_horas
    )
    margen_seguridad = max(1, math.ceil(0.1 * param_simulacion.max_autobuses))
    disponibles = len(estacion.baterias_reserva.items) + estacion.baterias_cargando
    return disponibles >= demanda_esperada + margen_seguridad


class EstacionIntercambio:
    def __init__(self, env, capacidad_estacion, tiempo_ruta=37.2):
        self.env = env
        self.capacidad_estacion = capacidad_estacion
        self.tiempo_ruta = tiempo_ruta
        self.estaciones = simpy.Resource(env, capacity=capacidad_estacion)

        self.baterias_reserva = simpy.Store(env, capacity=param_estacion.total_baterias)
        self.baterias_descargadas = simpy.Store(env, capacity=param_estacion.total_baterias)

        # Las baterías disponibles se inicializan al SoC objetivo operativo, no
        # necesariamente a 100 %, para mantener consistencia con la política de carga.
        self.baterias_reserva.items = [
            param_bateria.soc_objetivo for _ in range(param_estacion.baterias_iniciales)
        ]
        self.baterias_descargadas.items = [
            SOC_INICIAL_DESCARGADAS
            for _ in range(param_estacion.total_baterias - param_estacion.baterias_iniciales)
        ]
        self._ingreso_reserva = [0.0 for _ in range(param_estacion.baterias_iniciales)]

        self.tiempos_espera_baterias = []
        self.esperas_autobuses = []
        self.soc_retorno = []
        self.eventos_soc_critico = 0
        self.rutas_no_factibles = 0
        self.baterias_cargando = 0
        self.tiempo_espera_total = 0
        self.energia_total_cargada = 0
        self.energia_operativa_cargada = 0
        self.energia_precarga_inicial = 0
        self.costo_total_electrico = 0
        self.costo_operativo_electrico = 0
        self.costo_precarga_inicial = 0
        self.costo_total_gas = 0
        self.energia_total_gas = 0
        self.volumen_total_gas = 0
        self.kilometros_totales = 0
        self.horas_ruta_totales = 0
        self.energia_punta_autobuses = 0
        self.energia_fuera_punta_autobuses = 0
        self.energia_punta_electrica = 0
        self.intercambios_realizados = 0
        self.intercambios_operativos = 0
        self.asignaciones_iniciales = 0
        self.registro_intercambios = []
        self.registro_cargas = []
        self.energia_cargada_por_hora = defaultdict(float)
        self.costo_carga_por_hora = defaultdict(float)
        self.potencia_por_hora = defaultdict(float)
        self.muestras_potencia_por_hora = defaultdict(int)

        self.registrar_precarga_inicial()

        for _ in range(self.capacidad_estacion):
            self.env.process(self.cargar_bateria())

    def registrar_precarga_inicial(self):
        """Registra por separado la energía inicial preparada antes de simular."""
        energia_por_bateria = param_bateria.soc_objetivo / 100 * param_bateria.capacidad
        costo_por_bateria = energia_por_bateria * tarifa_electrica(0)
        self.energia_precarga_inicial = energia_por_bateria * param_estacion.baterias_iniciales
        self.costo_precarga_inicial = costo_por_bateria * param_estacion.baterias_iniciales
        self.energia_total_cargada += self.energia_precarga_inicial
        self.costo_total_electrico += self.costo_precarga_inicial
        if es_hora_punta_electrica(0):
            self.energia_punta_electrica += self.energia_precarga_inicial

    def registrar_carga_segmento(self, inicio, duracion, energia, potencia, operativa=True):
        """Registra energía y costo segmentados por hora tarifaria."""
        restante = duracion
        cursor = inicio
        costo_total = 0.0
        energia_total = 0.0
        while restante > 1e-9:
            siguiente_hora = math.floor(cursor) + 1
            paso = min(restante, siguiente_hora - cursor)
            if paso <= 1e-9:
                paso = restante
            energia_paso = energia * paso / duracion if duracion > 0 else energia
            costo_paso = energia_paso * tarifa_electrica(cursor)
            hora_idx = int(cursor)
            self.energia_cargada_por_hora[hora_idx] += energia_paso
            self.costo_carga_por_hora[hora_idx] += costo_paso
            self.potencia_por_hora[hora_idx] += potencia
            self.muestras_potencia_por_hora[hora_idx] += 1
            if es_hora_punta_electrica(cursor):
                self.energia_punta_electrica += energia_paso
            costo_total += costo_paso
            energia_total += energia_paso
            cursor += paso
            restante -= paso
        self.energia_total_cargada += energia_total
        self.costo_total_electrico += costo_total
        if operativa:
            self.energia_operativa_cargada += energia_total
            self.costo_operativo_electrico += costo_total
        return costo_total

    def reemplazar_bateria(self, autobuses_id, soc_inicial, hora_actual):
        """Realiza el intercambio asumiendo que hay batería disponible."""
        yield from self._asignar_bateria(autobuses_id, soc_inicial, hora_actual, False)

    def _asignar_bateria(self, autobuses_id, soc_inicial, hora_actual, primera_salida):
        _ = yield self.baterias_reserva.get()
        ingreso = self._ingreso_reserva.pop(0)
        self.tiempos_espera_baterias.append(self.env.now - ingreso)

        capacidad_requerida = 0
        if primera_salida:
            self.asignaciones_iniciales += 1
        else:
            yield self.baterias_descargadas.put(soc_inicial)
            capacidad_requerida = max(
                0,
                (param_bateria.soc_objetivo - soc_inicial) / 100 * param_bateria.capacidad,
            )

        hora_final = self.env.now + TIEMPO_REEMPLAZO
        if VERBOSE:
            accion = "toma batería inicial" if primera_salida else "reemplaza su batería"
            print(
                f"Autobús {autobuses_id} {accion} en {formato_hora(self.env.now)} "
                f"(SoC inicial: {soc_inicial:.2f}%). Hora final: {formato_hora(hora_final)}"
            )
        yield self.env.timeout(TIEMPO_REEMPLAZO)

        self.intercambios_realizados += 1
        if not primera_salida:
            self.intercambios_operativos += 1
            dia_actual = int(self.env.now // 24)
            hora_registro = formato_hora(self.env.now)
            self.registro_intercambios.append((dia_actual, hora_registro, capacidad_requerida))
            if es_hora_punta_bus(hora_actual):
                self.energia_punta_autobuses += capacidad_requerida
            else:
                self.energia_fuera_punta_autobuses += capacidad_requerida

    def cargar_bateria(self):
        """Proceso individual de un cargador con costo integrado por segmento."""
        while True:
            if len(self.baterias_descargadas.items) == 0:
                yield self.env.timeout(1 / 60)
                continue

            hora_actual = self.env.now % 24
            if (
                es_hora_punta_electrica(hora_actual)
                and inventario_suficiente_hasta_fin_punta(self, hora_actual)
            ):
                _, fin = param_economicos.horas_punta
                espera = (fin - hora_actual) % 24
                if espera == 0:
                    espera = 1 / 60
                if VERBOSE:
                    print(f"Retrasando carga hasta {formato_hora(self.env.now + espera)}")
                yield self.env.timeout(espera)
                continue

            soc_actual = yield self.baterias_descargadas.get()
            self.baterias_cargando += 1
            inicio_carga = self.env.now
            energia_carga = 0.0
            costo_carga = 0.0
            soc = max(0, min(soc_actual, param_bateria.soc_objetivo))
            energia_por_pct = param_bateria.capacidad / 100

            if VERBOSE:
                tipo = "punta" if es_hora_punta_electrica(self.env.now) else "fuera de punta"
                print(f"Se está cargando una batería en hora {tipo} ({formato_hora(self.env.now)})")

            while soc < param_bateria.soc_objetivo:
                sig = min(soc + 1, param_bateria.soc_objetivo)
                potencia = param_bateria.potencia_carga(soc)
                energia = (sig - soc) * energia_por_pct
                duracion = energia / potencia
                costo_carga += self.registrar_carga_segmento(
                    self.env.now,
                    duracion,
                    energia,
                    potencia,
                    operativa=True,
                )
                energia_carga += energia
                yield self.env.timeout(duracion)
                soc = sig

            self.baterias_cargando -= 1
            yield self.baterias_reserva.put(param_bateria.soc_objetivo)
            self._ingreso_reserva.append(self.env.now)
            self.registro_cargas.append(
                (inicio_carga, self.env.now, soc_actual, param_bateria.soc_objetivo, energia_carga, costo_carga)
            )


def llegada_autobuses(env, estacion, max_autobuses, tiempo_ruta=37.2):
    """Genera la salida inicial de autobuses y crea procesos cíclicos."""
    yield env.timeout(5)  # Los autobuses comienzan a salir a las 5:00 AM
    for autobuses_id in range(1, max_autobuses + 1):
        yield env.timeout(intervalo_salida(env.now))
        if VERBOSE:
            print(f"Autobús {autobuses_id} sale de la estación en {formato_hora(env.now)}")
        env.process(
            proceso_autobus(
                env,
                estacion,
                autobuses_id,
                tiempo_ruta,
                primera_salida=True,
            )
        )


def proceso_autobus(env, estacion, autobuses_id, tiempo_ruta, primera_salida=False):
    """Simula un autobús realizando rutas cíclicas."""
    soc_actual = param_bateria.soc_objetivo
    while True:
        hora_actual = env.now % 24
        estimado = soc_estimado_despues(soc_actual, tiempo_ruta, hora_actual)
        es_inicial = primera_salida
        if primera_salida or estimado < SOC_MIN_OPERATIVO:
            llegada = env.now
            ultimo_aviso = env.now
            while len(estacion.baterias_reserva.items) <= 0:
                if VERBOSE and env.now - ultimo_aviso >= 10 / 60:
                    print(
                        f"Autobús {autobuses_id} espera batería desde {formato_hora(llegada)}"
                    )
                    ultimo_aviso = env.now
                yield env.timeout(1 / 60)

            with estacion.estaciones.request() as req:
                yield req
                tiempo_espera = env.now - llegada
                estacion.tiempo_espera_total += tiempo_espera
                estacion.esperas_autobuses.append(tiempo_espera)
                yield from estacion._asignar_bateria(
                    autobuses_id,
                    soc_actual,
                    hora_actual,
                    primera_salida,
                )
                soc_actual = param_bateria.soc_objetivo
                primera_salida = False

        if not es_inicial:
            yield env.timeout(intervalo_salida(env.now))
        else:
            primera_salida = False

        hora_inicio_ruta = env.now % 24
        duracion_ruta, consumo = duracion_y_consumo(tiempo_ruta, hora_inicio_ruta)
        consumo_pct = consumo / param_bateria.capacidad * 100
        if soc_actual - consumo_pct < 0:
            estacion.rutas_no_factibles += 1
            if VERBOSE:
                print(
                    f"ADVERTENCIA: Autobús {autobuses_id} no tiene SoC suficiente "
                    f"para completar la ruta iniciada en {formato_hora(env.now)}"
                )
        yield env.timeout(duracion_ruta)

        volumen_gas, energia_gas, costo_gas = consumo_gas_ruta(
            tiempo_ruta,
            hora_inicio_ruta,
            duracion_ruta,
        )
        estacion.energia_total_gas += energia_gas
        estacion.volumen_total_gas += volumen_gas
        estacion.costo_total_gas += costo_gas
        estacion.kilometros_totales += tiempo_ruta
        estacion.horas_ruta_totales += duracion_ruta

        soc_actual = max(0, soc_actual - consumo_pct)
        estacion.soc_retorno.append(soc_actual)
        if soc_actual < SOC_MIN_OPERATIVO:
            estacion.eventos_soc_critico += 1
        if VERBOSE:
            print(
                f"Autobús {autobuses_id} regresa a la estación en {formato_hora(env.now)} "
                f"con SoC {soc_actual:.2f}%"
            )


def ejecutar_simulacion(
    max_autobuses=None,
    duracion=None,
    tiempo_ruta=37.2,
    procesos_extra=None,
):
    """Ejecuta la simulación y devuelve la estación resultante."""
    if max_autobuses is None:
        max_autobuses = param_simulacion.max_autobuses
    if duracion is None:
        duracion = param_simulacion.duracion

    random.seed(param_simulacion.semilla)
    env = simpy.Environment()
    estacion = EstacionIntercambio(env, param_estacion.capacidad_estacion, tiempo_ruta)

    env.process(
        llegada_autobuses(
            env,
            estacion,
            max_autobuses=max_autobuses,
            tiempo_ruta=tiempo_ruta,
        )
    )
    if procesos_extra:
        for proc in procesos_extra:
            env.process(proc(env, estacion))
    env.run(until=duracion)
    return estacion


def _promedio(valores):
    return sum(valores) / len(valores) if valores else 0


def _percentil(valores, p):
    if not valores:
        return 0
    ordenados = sorted(valores)
    idx = min(len(ordenados) - 1, max(0, math.ceil(p / 100 * len(ordenados)) - 1))
    return ordenados[idx]


def formatear_resultados(estacion):
    """Devuelve una lista con los textos de los resultados."""
    dias = param_simulacion.dias
    emisiones_elec = estacion.energia_total_cargada * param_economicos.factor_co2_elec
    emisiones_gas = estacion.volumen_total_gas * param_economicos.factor_co2_gas
    ahorro = emisiones_gas - emisiones_elec
    espera_prom = _promedio(estacion.esperas_autobuses) * 60
    espera_p95 = _percentil(estacion.esperas_autobuses, 95) * 60
    soc_prom = _promedio(estacion.soc_retorno)
    soc_min = min(estacion.soc_retorno) if estacion.soc_retorno else 0
    costo_km_elec = estacion.costo_total_electrico / estacion.kilometros_totales if estacion.kilometros_totales else 0
    costo_km_gas = estacion.costo_total_gas / estacion.kilometros_totales if estacion.kilometros_totales else 0

    lines = [
        f"Resultados para {dias:.1f} días de operación",
        f"Kilómetros simulados: {estacion.kilometros_totales:.2f} km",
        f"Asignaciones iniciales de batería: {estacion.asignaciones_iniciales}",
        f"Intercambios operativos de batería: {estacion.intercambios_operativos}",
        f"Intercambios totales registrados: {estacion.intercambios_realizados}",
        f"Consumo operativo de energía cargada: {estacion.energia_operativa_cargada:.2f} kWh",
        f"Energía de precarga inicial: {estacion.energia_precarga_inicial:.2f} kWh",
        f"Consumo total de energía en hora punta de autobuses: {estacion.energia_punta_autobuses:.2f} kWh",
        f"Consumo total de energía fuera de hora punta de autobuses: {estacion.energia_fuera_punta_autobuses:.2f} kWh",
        f"Consumo total de energía en hora punta de electricidad: {estacion.energia_punta_electrica:.2f} kWh",
        f"Tiempo total de espera acumulado: {formato_hora(estacion.tiempo_espera_total)}",
        f"Espera promedio por atención: {espera_prom:.2f} min",
        f"Espera percentil 95: {espera_p95:.2f} min",
        f"SoC promedio al retorno: {soc_prom:.2f}%",
        f"SoC mínimo al retorno: {soc_min:.2f}%",
        f"Eventos bajo SoC mínimo ({SOC_MIN_OPERATIVO}%): {estacion.eventos_soc_critico}",
        f"Rutas no factibles energéticamente: {estacion.rutas_no_factibles}",
        f"Costo total de operación (eléctrico): S/. {estacion.costo_total_electrico:.2f}",
        f"Costo operativo eléctrico sin precarga: S/. {estacion.costo_operativo_electrico:.2f}",
        f"Costo total de operación (gas natural): S/. {estacion.costo_total_gas:.2f}",
        f"Costo eléctrico por km: S/. {costo_km_elec:.4f}/km",
        f"Costo gas natural por km: S/. {costo_km_gas:.4f}/km",
    ]

    if estacion.costo_total_electrico < estacion.costo_total_gas:
        lines.append("Es más barato operar con electricidad bajo los supuestos modelados.")
    else:
        lines.append("Es más barato operar con gas natural bajo los supuestos modelados.")

    lines.extend([
        f"Emisiones con electricidad: {emisiones_elec:.2f} kg CO2",
        f"Emisiones con gas natural: {emisiones_gas:.2f} kg CO2",
        f"Ahorro de CO2: {ahorro:.2f} kg",
    ])
    return lines


def imprimir_resultados(estacion):
    """Muestra por pantalla los resultados de la simulación."""
    for line in formatear_resultados(estacion):
        print(line)


if __name__ == "__main__":
    estacion = ejecutar_simulacion()
    imprimir_resultados(estacion)
