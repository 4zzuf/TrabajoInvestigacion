import sys
import random

from PyQt5 import QtWidgets, QtCore

import GraficosModelo
import trafico
import tiempos_intercambio


import simpy
import modelo


class SimulacionWorker(QtCore.QObject):
    """Ejecuta la simulación en un hilo separado."""

    finished = QtCore.pyqtSignal(list)
    progress = QtCore.pyqtSignal(int)

    def __init__(self, max_autobuses, duracion, tiempo_ruta):
        super().__init__()
        self._max_autobuses = max_autobuses
        self._duracion = duracion
        self._tiempo_ruta = tiempo_ruta
        self._cancel_requested = False

    def cancel(self):
        self._cancel_requested = True

    @QtCore.pyqtSlot()
    def run(self):
        # Ejecutar la simulación paso a paso para poder emitir progreso y
        # permitir la cancelación segura desde la interfaz.
        random.seed(modelo.param_simulacion.semilla)
        env = simpy.Environment()
        estacion = modelo.EstacionIntercambio(
            env, modelo.param_estacion.capacidad_estacion
        )
        env.process(
            modelo.llegada_autobuses(
                env,
                estacion,
                max_autobuses=self._max_autobuses,
                tiempo_ruta=self._tiempo_ruta,
            )
        )

        last_percent = -1
        while env.peek() <= self._duracion:
            if self._cancel_requested:
                break
            env.step()
            porcentaje = int(env.now / self._duracion * 100)
            if porcentaje != last_percent:
                self.progress.emit(porcentaje)
                last_percent = porcentaje

        if not self._cancel_requested and last_percent < 100:
            self.progress.emit(100)

        r = modelo.formatear_resultados(estacion)
        self.finished.emit(r)


class SimulacionWindow(QtWidgets.QWidget):
    """Interfaz principal para ejecutar la simulaci\u00f3n."""

    def __init__(self):
        super().__init__()
        self._thread = None
        self._worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QtWidgets.QFormLayout()

        self.dias = QtWidgets.QSpinBox()
        self.dias.setRange(1, 365)
        self.dias.setValue(modelo.param_simulacion.dias)
        layout.addRow("Duraci\u00f3n (d\u00edas)", self.dias)

        self.autobuses = QtWidgets.QSpinBox()
        self.autobuses.setRange(1, 200)
        self.autobuses.setValue(modelo.param_simulacion.max_autobuses)
        layout.addRow("Max autobuses", self.autobuses)


        self.capacidad = QtWidgets.QSpinBox()
        self.capacidad.setRange(1, 200)
        self.capacidad.setValue(modelo.param_estacion.capacidad_estacion)
        layout.addRow("Capacidad estaci\u00f3n", self.capacidad)

        self.total_baterias = QtWidgets.QSpinBox()
        self.total_baterias.setRange(1, 500)
        self.total_baterias.setValue(modelo.param_estacion.total_baterias)
        layout.addRow("Total bater\u00edas", self.total_baterias)

        self.baterias_iniciales = QtWidgets.QSpinBox()
        self.baterias_iniciales.setRange(0, 500)
        self.baterias_iniciales.setValue(modelo.param_estacion.baterias_iniciales)
        layout.addRow("Bater\u00edas iniciales", self.baterias_iniciales)

        self.tiempo_ruta = QtWidgets.QDoubleSpinBox()
        self.tiempo_ruta.setRange(1.0, 100.0)
        self.tiempo_ruta.setSingleStep(1.0)
        self.tiempo_ruta.setValue(37.2)
        layout.addRow("Distancia ruta (km)", self.tiempo_ruta)

        self.progreso = QtWidgets.QProgressBar()
        self.progreso.setRange(0, 100)
        self.progreso.setValue(0)

        self.resultados = QtWidgets.QTextEdit()
        self.resultados.setReadOnly(True)

        self.boton = QtWidgets.QPushButton("Ejecutar simulaci\u00f3n")
        self.boton.clicked.connect(self.run_simulation)

        self.cancelar = QtWidgets.QPushButton("Cancelar")
        self.cancelar.setEnabled(False)
        self.cancelar.clicked.connect(self.cancelar_simulacion)


        self.combo_grafico = QtWidgets.QComboBox()
        self.combo_grafico.addItems([
            "Carga",
            "Costos",
            "Diarios",
            "Emisiones",
            "Inventario",
            "Cola",
            "Costos día",
            "Cargadores",
            "Tráfico",
            "Intercambio",
            "Espera baterías",

        ])
        self.boton_grafico = QtWidgets.QPushButton("Mostrar gr\u00e1fico")
        self.boton_grafico.clicked.connect(self.mostrar_grafico)

        layout.addRow(self.boton)
        layout.addRow(self.cancelar)
        layout.addRow(self.combo_grafico, self.boton_grafico)

        layout.addRow(self.progreso)
        layout.addRow(self.resultados)

        self.setLayout(layout)
        self.setWindowTitle("Simulaci\u00f3n de intercambio de bater\u00edas")

    def _update_params(self):
        modelo.param_simulacion.actualizar(
            dias=self.dias.value(),
            max_autobuses=self.autobuses.value(),
        )
        modelo.param_estacion.actualizar(
            capacidad=self.capacidad.value(),
            total=self.total_baterias.value(),
            iniciales=self.baterias_iniciales.value(),
        )

    def mostrar_grafico(self):
        self._update_params()
        opcion = self.combo_grafico.currentText()
        if opcion == "Carga":
            GraficosModelo.grafico_carga_bateria(block=False)
        elif opcion == "Costos":
            GraficosModelo.grafico_costos(block=False)
        elif opcion == "Diarios":
            GraficosModelo.grafico_diarios(block=False)
        elif opcion == "Emisiones":
            GraficosModelo.grafico_emisiones(block=False)
        elif opcion == "Inventario":
            GraficosModelo.grafico_inventario(block=False)
        elif opcion == "Cola":
            GraficosModelo.grafico_cola(block=False)
        elif opcion == "Costos día":
            GraficosModelo.grafico_costos_dia(block=False)
        elif opcion == "Cargadores":
            GraficosModelo.grafico_uso_cargadores(block=False)
        elif opcion == "Tráfico":
            trafico.graficar_trafico(block=False)
        elif opcion == "Intercambio":
            tiempos_intercambio.graficar_tiempos_intercambio(block=False)
        elif opcion == "Espera baterías":
            tiempos_intercambio.graficar_espera_baterias(block=False)


    def run_simulation(self):
        self._update_params()

        self.boton.setEnabled(False)
        self.cancelar.setEnabled(True)
        self.progreso.setValue(0)
        self.resultados.clear()

        self._thread = QtCore.QThread()
        self._worker = SimulacionWorker(
            modelo.param_simulacion.max_autobuses,
            modelo.param_simulacion.duracion,
            self.tiempo_ruta.value(),
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_simulation_finished)
        self._worker.progress.connect(self.progreso.setValue)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._on_thread_finished)
        self._thread.start()

    def _on_thread_finished(self):
        """Clean up the worker thread once it has fully stopped."""
        if self._thread is not None:
            self._thread.deleteLater()
            self._thread = None

    def cancelar_simulacion(self):
        if self._worker is not None:
            self._worker.cancel()

    def _on_simulation_finished(self, lines):
        self.resultados.setPlainText("\n".join(lines))
        self.boton.setEnabled(True)
        self.cancelar.setEnabled(False)
        # Mantener la barra de progreso en 100 % para indicar que la
        # simulación finalizó correctamente.
        self.progreso.setValue(100)
        self._worker.deleteLater()
        self._worker = None

        # Mostrar automáticamente el gráfico seleccionado una vez
        # finalizada la simulación. De esta manera los parámetros
        # ajustados por el usuario se reflejan en la visualización
        # sin cerrar la ventana.
        self.mostrar_grafico()


        # Asegurar que la ventana principal permanezca visible.
        self.show()



_window = None


def main():
    """Run the GUI keeping a reference to the main window."""
    global _window
    app = QtWidgets.QApplication(sys.argv)

    _window = SimulacionWindow()
    _window.show()

    # Ejecutar la aplicación y mantenerla abierta hasta que el usuario la cierre
    return app.exec_()


if __name__ == "__main__":  # pragma: no cover - ejecuci\u00f3n manual
    sys.exit(main())
