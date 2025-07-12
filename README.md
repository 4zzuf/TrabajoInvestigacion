# Trabajo de Investigación

Este repositorio contiene utilidades para simulación.

Las simulaciones por defecto abarcan 21 días de operación. Internamente esa
duración se convierte a horas cuando es necesario, pero la entrada y las
métricas se expresan en días para mayor claridad. Por defecto se consideran
hasta 20 autobuses en la estación.
## Instalación

Instala las dependencias con:

```bash

pip install -r requirements.txt
```


La estación cuenta con 21 cargadores y 41 baterías (20 de ellas cargadas al
inicio). Las rutas cubren una distancia aproximada de 37.2 km. El tiempo que
demora cada autobús depende de su velocidad promedio (30 km/h) y de un pequeño
ajuste por el tráfico, de modo que los valores ya no se fijan en cuatro u ocho
horas. Las horas de entrada y salida se registran en formato ``hh:mm``.

La frecuencia de salida de autobuses ahora incluye variaciones
aleatorias para reflejar la demanda real y posibles retrasos por
congestión o incidentes. Durante las horas punta los intervalos
promedio son de 3.5 minutos y el resto del día de 10 minutos, pero cada
salida puede adelantarse o retrasarse unos minutos. Los fines de semana
la frecuencia base disminuye: los sábados opera al 70 % y los domingos
al 50 % de lo habitual. Cada autobús toma una batería cargada de la
reserva al iniciar su primer recorrido. Desde entonces la reemplaza sólo
si se estima que al terminar la siguiente
vuelta quedará con menos de 20 % de carga.
Si la batería llega en plena hora punta eléctrica y hay suficientes
baterías cargadas para cubrir la demanda hasta que finalice la franja,
su recarga se pospone para ahorrar costos.

## Gráfico de eficiencia operativa

Ejecuta el script `tiempos_intercambio.py` para visualizar el tiempo de
intercambio promedio de la estación según el número de autobuses. Cada vehículo
cubre 37.2 km por ciclo y cambia la batería únicamente cuando se prevé que la
próxima vuelta terminará con menos del 20 % de carga. El valor mostrado incluye
la espera en cola y el reemplazo de
4 minutos, expresado en minutos:

```bash
python tiempos_intercambio.py
```
Se abrirá una ventana con la gráfica que relaciona el número de autobuses con
el tiempo promedio de cada intercambio.

Además, el mismo módulo incluye una función para graficar cuánto tiempo
permanecen las baterías cargadas en la estación antes de ser utilizadas. Para
mostrarla ejecuta:

```bash
python -c "import tiempos_intercambio as t; t.graficar_espera_baterias()"
```

## Gráficos de costos y consumos

El módulo `GraficosModelo.py` genera varias gráficas:

1. Costo de operación con electricidad según el número de autobuses.
2. Comparación de costos usando electricidad y gas natural.
3. Consumo eléctrico en hora punta y fuera de punta.
4. Costo de operación por hora para ambas tecnologías.

El último gráfico presenta dos barras con el costo promedio por hora al operar
con gas natural frente a electricidad.

Los valores corresponden al periodo de simulacion seleccionado.

Para que los costos crezcan de forma continua al aumentar la flota,
`GraficosModelo.py costos` amplía temporalmente la capacidad de carga de la estación
según la cantidad de autobuses evaluada. De esta manera no se genera la caída de
costos al pasar de cuatro a cinco vehículos ni la estabilización por encima de
diez.

El costo de operar con gas natural se calcula aparte a partir de la distancia
recorrida y no depende del consumo eléctrico. Cada autobús utiliza 70 m³ de gas
por cada 100 km y el precio de venta es de S/. 1.35 por metro cúbico. Para una
flota de veinte vehículos durante 21 días esto representa unos 26 000 m³ en
total.

Ejecuta:

```bash
python GraficosModelo.py costos
```

## Ahorro de emisiones

Ejecuta `GraficosModelo.py emisiones` para comparar las emisiones totales del
período con electricidad y gas natural. El gráfico incluye las emisiones de
cada tecnología y una barra adicional con el ahorro total de CO₂:

```bash
python GraficosModelo.py emisiones
```

## Otros gráficos

El módulo `GraficosModelo.py` incluye varias visualizaciones adicionales:

- `diarios`: intercambios y consumo de energía por día.
- `inventario`: baterías cargadas y descargadas disponibles cada hora.
- `cola`: minutos de espera acumulados cada hora.
- `costosdia`: costo eléctrico diario diferenciando laborables y fines de semana.
- `cargadores`: porcentaje de utilización de los cargadores a lo largo del tiempo.


Estas mismas opciones están disponibles en la interfaz gráfica seleccionando el tipo de gráfico en el menú desplegable.

Por ejemplo, para mostrar el inventario de baterías desde la terminal ejecuta:


```bash
python GraficosModelo.py inventario
```

## Simulación desde la línea de comandos

El módulo `cli.py` permite ejecutar la simulación ajustando los parámetros
básicos desde la terminal. Por ejemplo, para simular 30 días con 25 autobuses y
una estación de 30 cargadores:

```bash
python cli.py --dias 30 --max-autobuses 25 --capacidad-estacion 30
```

También es posible cambiar la cantidad total de baterías o la semilla
aleatoria:

```bash
python cli.py --total-baterias 60 --baterias-iniciales 50 --semilla 123
```

## Ejecutar las pruebas

Instala los requisitos y ejecuta las pruebas con:

```bash
pytest
```
