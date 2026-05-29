# Simulación de estación de intercambio de baterías para buses eléctricos

Este repositorio contiene un modelo preliminar de simulación de eventos discretos para evaluar la operación de una estación de intercambio de baterías orientada a una flota de buses eléctricos. El caso base está pensado como apoyo para una investigación de Ingeniería Eléctrica: dimensionamiento de baterías/cargadores, demanda eléctrica, costos operativos y emisiones frente a una referencia de gas natural.

## Objetivo del modelo

Evaluar, bajo supuestos configurables, si una estación de intercambio de baterías puede atender una flota de buses manteniendo niveles aceptables de servicio y cuantificando:

- energía eléctrica cargada por franja horaria;
- potencia y utilización de cargadores;
- inventario de baterías cargadas/descargadas;
- tiempos de espera de buses;
- SoC de retorno y eventos críticos;
- costos eléctricos y costos equivalentes con gas natural;
- emisiones de CO2 de ambos escenarios.

## Metodología resumida

El modelo usa simulación de eventos discretos con la librería SimPy. Cada bus realiza ciclos de ruta, consume energía según distancia, consumo específico y tráfico horario, y solicita intercambio de batería cuando el SoC estimado para la siguiente ruta queda por debajo del umbral operativo. Las baterías descargadas entran a una cola de carga, se cargan según una curva potencia-SoC y vuelven al inventario de reserva.

La política de carga evita, cuando el inventario esperado lo permite, cargar durante la hora punta eléctrica. El costo eléctrico ya no se asigna únicamente por la hora inicial de carga: cada carga se segmenta por hora para reflejar cruces entre tarifa punta y fuera de punta.

## Supuestos principales del caso base

Los valores por defecto son supuestos editables y deben validarse con datos reales, fichas técnicas o literatura antes de usarse como resultados finales de tesis.

| Parámetro | Valor base | Archivo |
| --- | ---: | --- |
| Capacidad de batería | 300 kWh | `parametros/bateria.py` |
| SoC objetivo | 90 % | `parametros/bateria.py` |
| Umbral mínimo operativo | 20 % | `modelo.py` |
| Consumo eléctrico | 0.9 a 1.2 kWh/km | `parametros/operacion_bus.py` |
| Velocidad promedio | 30 km/h | `parametros/operacion_bus.py` |
| Consumo gas natural | 70 m³/100 km | `parametros/operacion_bus.py` |
| Tarifa punta | S/. 0.28/kWh | `parametros/economicos.py` |
| Tarifa normal | S/. 0.238/kWh | `parametros/economicos.py` |
| Hora punta eléctrica | 18:00 a 23:00 | `parametros/economicos.py` |
| Flota base | 20 buses | `parametros/simulacion.py` |
| Duración base | 21 días | `parametros/simulacion.py` |

## Instalación

La simulación usa SimPy real y los gráficos/interfaz usan `matplotlib` y `PyQt5`. En una máquina con Python y acceso a internet:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si solo se quiere correr el modelo por consola, basta con instalar SimPy:

```bash
python -m pip install simpy
```

## Ejecución por consola

Para correr una prueba corta y silenciosa:

```bash
python cli.py --quiet --dias 1 --max-autobuses 2 --capacidad-estacion 3 --total-baterias 6 --baterias-iniciales 3 --tiempo-ruta 10
```

Para correr el caso base de 21 días:

```bash
python cli.py --quiet --dias 21 --max-autobuses 20 --capacidad-estacion 21 --total-baterias 41 --baterias-iniciales 20 --tiempo-ruta 37.2
```

## Interfaz gráfica

```bash
python gui.py
```

## Gráficos disponibles

```bash
python GraficosModelo.py carga
python GraficosModelo.py costos
python GraficosModelo.py diarios
python GraficosModelo.py emisiones
python GraficosModelo.py inventario
python GraficosModelo.py cola
python GraficosModelo.py costosdia
python GraficosModelo.py cargadores
python GraficosModelo.py demanda
python GraficosModelo.py soc
```

Los gráficos más recomendables para una tesis de Ingeniería Eléctrica son:

1. curva de carga de batería;
2. perfil horario de demanda eléctrica;
3. utilización de cargadores;
4. inventario de baterías;
5. distribución de SoC al retorno;
6. comparación de costos y emisiones.

## Mejoras aplicadas al modelo

- La energía de precarga inicial se separa de la energía operativa para evitar mezclar preparación inicial con operación simulada.
- Las baterías disponibles se inicializan al SoC objetivo, no a 100 %, para mantener consistencia con la política de carga.
- La capacidad real de estación usada por los procesos de carga proviene de la instancia de estación, no de un global externo.
- El costo eléctrico se integra por hora, permitiendo que una carga que cruza de tarifa normal a punta sea valorizada por segmentos.
- La política de evitar carga en punta considera inventario disponible, baterías cargándose, demanda esperada y margen de seguridad.
- Las asignaciones iniciales se separan de los intercambios operativos.
- Se registran esperas de buses, SoC de retorno, rutas no factibles y eventos bajo el SoC mínimo.
- La comparación con gas natural usa los mismos kilómetros y rutas simuladas para mantener coherencia con el escenario eléctrico.
- Los gráficos de costos se consolidan para evitar salidas redundantes.
- Se agregan gráficos de demanda eléctrica y distribución de SoC.
- Se declara SimPy real como dependencia del modelo, junto con dependencias de gráficos/GUI en `requirements.txt`.

## Limitaciones actuales

Para una tesis final aún se recomienda:

- validar los parámetros con datos de operador, fabricante, norma o literatura;
- agregar CAPEX de cargadores, baterías, transformador, obra civil e instalación;
- ejecutar análisis Monte Carlo con múltiples semillas;
- construir mapas de sensibilidad cargadores vs baterías;
- comparar políticas de carga alternativas;
- incorporar restricciones de potencia contratada, demanda máxima o transformador;
- exportar resultados a CSV para tablas reproducibles.
