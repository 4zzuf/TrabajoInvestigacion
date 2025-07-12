import simpy
import random

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


def duracion_y_consumo(distancia_km, hora_actual):
    """Devuelve la duración y consumo para la distancia dada."""
    factor = trafico.factor_trafico(hora_actual)
    ajuste = 1 + 0.2 * (factor - 1)
    duracion = distancia_km / param_operacion.velocidad_promedio * ajuste
    consumo = (
        random.uniform(*param_operacion.consumo_kwh_km)
        * distancia_km
        * ajuste
    )
    return duracion, consumo


def soc_estimado_despues(soc_actual, distancia_km, hora_actual):
    """Calcula el SoC estimado tras la siguiente vuelta sin cambiar la batería."""
    factor = trafico.factor_trafico(hora_actual)
    ajuste = 1 + 0.2 * (factor - 1)
    consumo_promedio = sum(param_operacion.consumo_kwh_km) / 2
    consumo = consumo_promedio * distancia_km * ajuste
    return soc_actual - consumo / param_bateria.capacidad * 100


def inventario_suficiente_hasta_fin_punta(estacion, hora_actual):
    """Devuelve ``True`` si no es necesario cargar de inmediato."""
    inicio, fin = param_economicos.horas_punta
    if hora_actual < inicio or hora_actual >= fin:
        return True
    return len(estacion.baterias_reserva.items) > param_simulacion.max_autobuses

class EstacionIntercambio:
    def __init__(self, env, capacidad_estacion):
        self.env = env
        # "estaciones" representa los puntos donde los autobuses realizan el
        # cambio de batería. Cada cargador se gestiona mediante un proceso
        # independiente, por lo que no se requiere un recurso adicional.
        self.estaciones = simpy.Resource(env, capacity=capacidad_estacion)

        # Inventario de baterías cargadas disponible para los autobuses.
        # Se almacenan como el porcentaje de SoC que tienen, 100% significa
        # una batería completamente cargada.
        self.baterias_reserva = simpy.Store(
            env,
            capacity=param_estacion.total_baterias,
        )

        # Baterías descargadas a la espera de ser cargadas nuevamente.
        self.baterias_descargadas = simpy.Store(
            env,
            capacity=param_estacion.total_baterias,
        )

        # Inicializar los inventarios.
        self.baterias_reserva.items = [100 for _ in range(param_estacion.baterias_iniciales)]
        self.baterias_descargadas.items = [30 for _ in range(param_estacion.total_baterias - param_estacion.baterias_iniciales)]
        # Registrar el momento en que cada batería entra en reserva para medir el
        # tiempo que permanece en espera hasta ser utilizada.
        self._ingreso_reserva = [0.0 for _ in range(param_estacion.baterias_iniciales)]
        self.tiempos_espera_baterias = []
        self.baterias_cargando = 0  # Cantidad de baterías actualmente en carga
        self.tiempo_espera_total = 0  # Tiempo total de espera acumulado
        self.energia_total_cargada = 0  # Energía total consumida para cargar baterías
        self.costo_total_electrico = 0  # Costo total de carga eléctrica
        self.costo_total_gas = 0  # Costo total si se usara gas natural
        self.energia_total_gas = 0  # Energía total consumida si se usara gas
        self.volumen_total_gas = 0  # Volumen total consumido de gas natural (m3)
        self.energia_punta_autobuses = 0  # Energía consumida en hora punta por autobuses
        self.energia_fuera_punta_autobuses = 0  # Energía consumida fuera de hora punta por autobuses
        self.energia_punta_electrica = 0  # Energía consumida en hora punta de electricidad
        self.intercambios_realizados = 0  # Cantidad de reemplazos efectuados
        # Historial de intercambios (día, hora, energía)
        self.registro_intercambios = []

        # Costo de cargar las baterías iniciales
        self.cargar_baterias_iniciales()

        # Inicia procesos de carga paralelos para cada cargador
        for _ in range(param_estacion.capacidad_estacion):
            self.env.process(self.cargar_bateria())

    def cargar_baterias_iniciales(self):
        for _ in range(param_estacion.baterias_iniciales):
            hora_actual = 0  # Asumimos que se cargaron antes del inicio de la simulación
            capacidad_carga = param_bateria.capacidad
            if param_economicos.horas_punta[0] <= hora_actual < param_economicos.horas_punta[1]:  # Hora punta eléctrica
                costo_carga = capacidad_carga * param_economicos.costo_punta
                self.energia_punta_electrica += capacidad_carga
            else:  # Hora fuera de punta
                costo_carga = capacidad_carga * param_economicos.costo_normal

            self.energia_total_cargada += capacidad_carga
            self.costo_total_electrico += costo_carga

    def reemplazar_bateria(self, autobuses_id, soc_inicial, hora_actual):
        """Realiza el intercambio asumiendo que hay batería disponible."""
        # Tomar una batería cargada de la reserva y depositar la usada
        # ``soc_inicial`` corresponde al nivel de carga de la batería usada
        # cuando el autobús llega a la estación.
        _ = yield self.baterias_reserva.get()
        ingreso = self._ingreso_reserva.pop(0)
        self.tiempos_espera_baterias.append(self.env.now - ingreso)
        yield self.baterias_descargadas.put(soc_inicial)
        capacidad_requerida = (param_bateria.soc_objetivo - soc_inicial) / 100 * param_bateria.capacidad
        tiempo_reemplazo = 4 / 60  # 4 minutos en horas
        hora_final = self.env.now + tiempo_reemplazo  # Hora después del intercambio
        if VERBOSE:
            print(
                f"Autobús {autobuses_id} reemplaza su batería en {formato_hora(self.env.now)} "
                f"(SoC inicial: {soc_inicial:.2f}%). Hora final: {formato_hora(hora_final)}"
            )
        yield self.env.timeout(tiempo_reemplazo)
        self.intercambios_realizados += 1
        dia_actual = int(self.env.now // 24)
        hora_registro = formato_hora(self.env.now)
        self.registro_intercambios.append((dia_actual, hora_registro, capacidad_requerida))

        # Clasificar consumo de energía según hora punta de autobuses
        if 7 <= hora_actual < 9 or 18 <= hora_actual < 20:
            self.energia_punta_autobuses += capacidad_requerida
        else:
            self.energia_fuera_punta_autobuses += capacidad_requerida

        # La clasificación por hora punta eléctrica se realiza al cargar la batería
        
        # La estimación de consumo de gas se calcula tras la ruta del autobús

    def cargar_bateria(self):
        """Proceso individual de un cargador."""
        while True:
            # Comprobar cada minuto si hay baterías por cargar
            if len(self.baterias_descargadas.items) == 0:
                yield self.env.timeout(1 / 60)
                continue

            hora_actual = self.env.now % 24
            if (
                param_economicos.horas_punta[0]
                <= hora_actual
                < param_economicos.horas_punta[1]
                and inventario_suficiente_hasta_fin_punta(self, hora_actual)
            ):
                espera = param_economicos.horas_punta[1] - hora_actual
                if espera < 0:
                    espera += 24
                if VERBOSE:
                    print(
                        f"Retrasando carga hasta {formato_hora(self.env.now + espera)}"
                    )
                yield self.env.timeout(espera)
                continue

            soc_actual = yield self.baterias_descargadas.get()
            self.baterias_cargando += 1

            hora_actual = int(self.env.now % 24)
            capacidad_carga = (
                (param_bateria.soc_objetivo - soc_actual) / 100
            ) * param_bateria.capacidad
            tiempo_carga = param_bateria.tiempo_carga(soc_actual)

            if param_economicos.horas_punta[0] <= hora_actual < param_economicos.horas_punta[1]:
                costo_carga = capacidad_carga * param_economicos.costo_punta
                self.energia_punta_electrica += capacidad_carga
                if VERBOSE:
                    print(
                        f"Se está cargando una batería en hora punta (Hora actual: {hora_actual})"
                    )
            else:
                costo_carga = capacidad_carga * param_economicos.costo_normal
                if VERBOSE:
                    print(
                        f"Se está cargando una batería fuera de hora punta (Hora actual: {hora_actual})"
                    )

            yield self.env.timeout(tiempo_carga)

            self.baterias_cargando -= 1
            yield self.baterias_reserva.put(param_bateria.soc_objetivo)
            self._ingreso_reserva.append(self.env.now)
            self.energia_total_cargada += capacidad_carga
            self.costo_total_electrico += costo_carga
# Procesos para simular la salida inicial de autobuses
def llegada_autobuses(env, estacion, max_autobuses, tiempo_ruta=37.2):
    """Genera la salida inicial de autobuses y crea procesos cíclicos.

    ``tiempo_ruta`` indica la distancia de la ruta en kilómetros.
    Durante horas pico (7:00-9:00 y 16:00-18:00) la frecuencia base de
    salida es de 3.5 minutos y en el resto del día de 10 minutos. Se
    introduce una variación aleatoria y posibles retrasos para reflejar la
    incertidumbre en la demanda de energía.
    """
    yield env.timeout(5)  # Los autobuses comienzan a salir a las 5:00 AM
    for autobuses_id in range(1, max_autobuses + 1):
        hora_actual = env.now % 24
        if 7 <= hora_actual < 9 or 16 <= hora_actual < 18:
            intervalo_base = 3.5 / 60  # 3.5 minutos
        else:
            intervalo_base = 10 / 60  # 10 minutos
        intervalo_base /= factor_demanda(env.now)
        variacion = random.uniform(
            -param_simulacion.variacion_llegadas,
            param_simulacion.variacion_llegadas,
        )
        intervalo = max(0, intervalo_base + variacion)
        if random.random() < param_simulacion.prob_retraso:
            intervalo += random.uniform(*param_simulacion.rango_retraso)

        yield env.timeout(intervalo)
        hora_actual = int(env.now % 24)
        if VERBOSE:
            print(
                f"Autobús {autobuses_id} sale de la estación en {formato_hora(env.now)}"
            )
        env.process(
            proceso_autobus(
                env,
                estacion,
                autobuses_id,
                tiempo_ruta,
                primera_salida=True,
            )
        )
# Proceso para simular el flujo del autobús
def proceso_autobus(env, estacion, autobuses_id, tiempo_ruta, primera_salida=False):
    """Simula un autobús realizando rutas cíclicas."""
    soc_actual = param_bateria.soc_objetivo
    while True:
        hora_actual = int(env.now % 24)
        estimado = soc_estimado_despues(soc_actual, tiempo_ruta, hora_actual)
        es_inicial = primera_salida
        if primera_salida or estimado < 20:
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
                if VERBOSE:
                    if primera_salida:
                        mensaje = "toma batería inicial"
                    else:
                        mensaje = "entra a la estación"
                    print(
                        f"Autobús {autobuses_id} {mensaje} en {formato_hora(env.now)} "
                        f"tras esperar {formato_hora(tiempo_espera)}"
                    )
                _ = yield estacion.baterias_reserva.get()
                ingreso = estacion._ingreso_reserva.pop(0)
                estacion.tiempos_espera_baterias.append(env.now - ingreso)
                if not primera_salida:
                    yield estacion.baterias_descargadas.put(soc_actual)
                    capacidad_requerida = (
                        param_bateria.soc_objetivo - soc_actual
                    ) / 100 * param_bateria.capacidad
                else:
                    capacidad_requerida = 0
                tiempo_reemplazo = 4 / 60
                hora_final = env.now + tiempo_reemplazo
                if VERBOSE and not primera_salida:
                    print(
                        f"(SoC inicial: {soc_actual:.2f}%). Hora final: {formato_hora(hora_final)}"
                    )
                yield env.timeout(tiempo_reemplazo)
                estacion.intercambios_realizados += 1
                if not primera_salida:
                    dia_actual = int(env.now // 24)
                    hora_registro = formato_hora(env.now)
                    estacion.registro_intercambios.append(
                        (dia_actual, hora_registro, capacidad_requerida)
                    )
                    if 7 <= hora_actual < 9 or 18 <= hora_actual < 20:
                        estacion.energia_punta_autobuses += capacidad_requerida
                    else:
                        estacion.energia_fuera_punta_autobuses += capacidad_requerida
                    # La clasificación por hora punta eléctrica se realiza al cargar la batería
                soc_actual = param_bateria.soc_objetivo
                primera_salida = False

        # Esperar el intervalo antes de la siguiente salida si no es la primera
        if not es_inicial:
            hora_actual = env.now % 24
            if 7 <= hora_actual < 9 or 16 <= hora_actual < 18:
                intervalo_base = 3.5 / 60
            else:
                intervalo_base = 10 / 60
            intervalo_base /= factor_demanda(env.now)
            variacion = random.uniform(
                -param_simulacion.variacion_llegadas,
                param_simulacion.variacion_llegadas,
            )
            intervalo = max(0, intervalo_base + variacion)
            if random.random() < param_simulacion.prob_retraso:
                intervalo += random.uniform(*param_simulacion.rango_retraso)
            yield env.timeout(intervalo)
        else:
            primera_salida = False

        # El autobús sale a su ruta
        hora_inicio_ruta = int(env.now % 24)
        duracion_ruta, consumo = duracion_y_consumo(tiempo_ruta, hora_inicio_ruta)
        yield env.timeout(duracion_ruta)
        energia_gas = (
            param_operacion.consumo_gas_hora
            * duracion_ruta
            * trafico.factor_trafico(hora_inicio_ruta)
        )
        estacion.energia_total_gas += energia_gas
        volumen_gas = param_operacion.consumo_gas_100km * tiempo_ruta / 100
        estacion.volumen_total_gas += volumen_gas
        estacion.costo_total_gas += volumen_gas * param_economicos.costo_gas_m3
        soc_actual = max(0, soc_actual - consumo / param_bateria.capacidad * 100)
        hora_actual = int(env.now % 24)
        if VERBOSE:
            print(
                f"Autobús {autobuses_id} regresa a la estación en {formato_hora(env.now)} "
                f"con SoC {soc_actual:.2f}%"
            )


# Configuración de la simulación
def ejecutar_simulacion(
    max_autobuses=None,
    duracion=None,
    tiempo_ruta=37.2,
    procesos_extra=None,
):
    """Ejecuta la simulación y devuelve la estación resultante.

    ``tiempo_ruta`` representa la distancia en kilómetros de la ruta de cada
    autobús antes de regresar a la estación. El tiempo real se calcula a partir
    de esta distancia y de la velocidad promedio ajustada por el tráfico.
    """
    if max_autobuses is None:
        max_autobuses = param_simulacion.max_autobuses
    if duracion is None:
        duracion = param_simulacion.duracion

    random.seed(param_simulacion.semilla)
    env = simpy.Environment()
    estacion = EstacionIntercambio(env, param_estacion.capacidad_estacion)

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


def formatear_resultados(estacion):
    """Devuelve una lista con los textos de los resultados."""
    dias = param_simulacion.dias
    lines = [
        f"Resultados para {dias:.1f} d\u00edas de operaci\u00f3n",
        f"Consumo total de energ\u00eda en hora punta de autobuses: {estacion.energia_punta_autobuses:.2f} kWh",
        f"Consumo total de energ\u00eda fuera de hora punta de autobuses: {estacion.energia_fuera_punta_autobuses:.2f} kWh",
        f"Consumo total de energ\u00eda en hora punta de electricidad: {estacion.energia_punta_electrica:.2f} kWh",
        f"Tiempo total de espera acumulado: {formato_hora(estacion.tiempo_espera_total)}",
        f"Costo total de operaci\u00f3n (el\u00e9ctrico): S/. {estacion.costo_total_electrico:.2f}",
        f"Costo total de operaci\u00f3n (gas natural): S/. {estacion.costo_total_gas:.2f}",
    ]

    if estacion.costo_total_electrico < estacion.costo_total_gas:
        lines.append("Es m\u00e1s barato operar con electricidad.")
    else:
        lines.append("Es m\u00e1s barato operar con gas natural.")

    emisiones_elec = estacion.energia_total_cargada * param_economicos.factor_co2_elec
    emisiones_gas = estacion.volumen_total_gas * param_economicos.factor_co2_gas
    ahorro = emisiones_gas - emisiones_elec
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


