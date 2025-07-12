import argparse

import modelo


def main():
    parser = argparse.ArgumentParser(
        description="Ejecuta la simulación de intercambio de baterías"
    )
    parser.add_argument(
        "--dias", type=int, help="Duración de la simulación en días"
    )
    parser.add_argument(
        "--max-autobuses", type=int, help="Cantidad de autobuses en la flota"
    )
    parser.add_argument("--semilla", type=int, help="Semilla aleatoria")
    parser.add_argument(
        "--capacidad-estacion",
        type=int,
        help="Cantidad de cargadores disponibles en la estación",
    )
    parser.add_argument(
        "--total-baterias",
        type=int,
        help="Número total de baterías de la estación",
    )
    parser.add_argument(
        "--baterias-iniciales",
        type=int,
        help="Baterías con las que inicia la estación",
    )
    parser.add_argument(
        "--tiempo-ruta",
        type=float,
        default=37.2,
        help="Distancia de la ruta en kilómetros",
    )
    args = parser.parse_args()

    if any(v is not None for v in [args.dias, args.max_autobuses, args.semilla]):
        modelo.param_simulacion.actualizar(
            dias=args.dias, max_autobuses=args.max_autobuses, semilla=args.semilla
        )

    if any(
        v is not None
        for v in [args.capacidad_estacion, args.total_baterias, args.baterias_iniciales]
    ):
        modelo.param_estacion.actualizar(
            capacidad=args.capacidad_estacion,
            total=args.total_baterias,
            iniciales=args.baterias_iniciales,
        )

    estacion = modelo.ejecutar_simulacion(
        max_autobuses=modelo.param_simulacion.max_autobuses,
        duracion=modelo.param_simulacion.duracion,
        tiempo_ruta=args.tiempo_ruta,
    )
    modelo.imprimir_resultados(estacion)


if __name__ == "__main__":
    main()
