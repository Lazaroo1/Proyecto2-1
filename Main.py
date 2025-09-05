# crt_gui_pyqt.py
"""
Simulación de Tubo de Rayos Catódicos (CRT) - Interfaz con PyQt6

"""

import sys
import math
import numpy as np
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QSlider, QComboBox, QGroupBox, QRadioButton,
    QButtonGroup, QFrame, QSizePolicy, QSpinBox, QDoubleSpinBox
)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.animation as animation

# -----------------------------
# Clase que contiene la simulación (lógica original)
# -----------------------------
class CRTSimulationLogic:
    def __init__(self):
        # Constantes físicas del CRT (simplificadas para mejor visualización)
        self.ELECTRON_CHARGE = 1.602e-19  # Coulombs
        self.ELECTRON_MASS = 9.109e-31   # kg
        self.CRT_LENGTH = 0.4            # metros (no usado en visual)
        self.PLATE_LENGTH = 0.08         # metros
        self.PLATE_SEPARATION = 0.02     # metros
        self.SCREEN_SIZE = 0.2           # metros

        # Factor de escala para hacer visible la deflexión
        self.DEFLECTION_SCALE = 5000

        # Parámetros controlables
        self.acceleration_voltage = 2000  # V
        self.manual_vx = 0               # V
        self.manual_vy = 0               # V
        self.persistence = 100           # puntos
        self.mode = 'manual'             # 'manual' o 'sinusoidal'

        # Parámetros sinusoidales
        self.sine_params = {
            'amplitude_x': 50.0,    # V
            'frequency_x': 1.0,   # Hz
            'phase_x': 0.0,         # grados
            'amplitude_y': 50.0,    # V
            'frequency_y': 1.0,   # Hz
            'phase_y': 0.0,          # grados (para círculo inicial)
        }

        # Variables de simulación
        self.time = 0.0
        self.is_running = False
        self.trail_points_x = []
        self.trail_points_y = []
        self.current_position = {'x': 0.0, 'y': 0.0}
        self.voltage_history_x = []
        self.voltage_history_y = []
        self.time_history = []

        self.dt = 0.01            # tiempo por tick (s)
        self.delta_target_deg = 0.0  # δ objetivo (se actualiza con radio δ)
        self._lock_phase = False     # evita bucles cuando movemos sliders por código

        # t0 para anclar fases cuando se usan relaciones distintas de 1:1
        self.t0 = 0.0

    def calculate_initial_velocity(self):
        """Calcula la velocidad inicial del electrón"""
        kinetic_energy = self.ELECTRON_CHARGE * self.acceleration_voltage
        # protección numérica
        if kinetic_energy <= 0:
            return 0.0
        return np.sqrt(2.0 * kinetic_energy / self.ELECTRON_MASS)

    def calculate_deflection(self, voltage):
        """Calcula la deflexión del electrón (simplificada para visualización)"""
        if voltage == 0.0:
            return 0.0

        initial_velocity = self.calculate_initial_velocity()
        # Factor de deflexión proporcional al voltaje e inversamente proporcional a la aceleración
        deflection_factor = voltage / max(1.0, (self.acceleration_voltage / 1000.0))
        return deflection_factor * self.DEFLECTION_SCALE / 100000.0

    def get_voltages(self, t):
        """Obtiene los voltajes según el modo de operación"""
        if self.mode == 'manual':
            return {'vx': float(self.manual_vx), 'vy': float(self.manual_vy)}
        else:
            # aplicar t0 si existe
            tt = t - getattr(self, 't0', 0.0)
            vx = (self.sine_params['amplitude_x'] *
                  np.sin(2.0 * np.pi * float(self.sine_params['frequency_x']) * tt +
                         np.radians(float(self.sine_params['phase_x']))))
            vy = (self.sine_params['amplitude_y'] *
                  np.sin(2.0 * np.pi * float(self.sine_params['frequency_y']) * tt +
                         np.radians(float(self.sine_params['phase_y']))))
            return {'vx': vx, 'vy': vy}

    def calculate_position(self, t):
        """Calcula la posición del electrón en la pantalla"""
        voltages = self.get_voltages(t)
        deflection_x = self.calculate_deflection(voltages['vx'])
        deflection_y = self.calculate_deflection(voltages['vy'])

        # Escalar para pantalla (lineal)
        screen_x = deflection_x * 100.0
        screen_y = deflection_y * 100.0

        # Límite de pantalla
        screen_x = float(np.clip(screen_x, -100.0, 100.0))
        screen_y = float(np.clip(screen_y, -60.0, 60.0))
        return {'x': screen_x, 'y': screen_y}

    def step_time(self):
        """Avanza la simulación en dt y actualiza estados si está corriendo"""
        if self.is_running:
            self.time += self.dt
            # Calcular nueva posición
            self.current_position = self.calculate_position(self.time)

            # Actualizar trail
            self.trail_points_x.append(self.current_position['x'])
            self.trail_points_y.append(self.current_position['y'])
            # Mantener solo los últimos puntos según persistencia
            if len(self.trail_points_x) > self.persistence:
                self.trail_points_x = self.trail_points_x[-self.persistence:]
                self.trail_points_y = self.trail_points_y[-self.persistence:]

            # Actualizar historial de voltajes
            voltages = self.get_voltages(self.time)
            self.voltage_history_x.append(voltages['vx'])
            self.voltage_history_y.append(voltages['vy'])
            self.time_history.append(self.time)

            # Mantener ventana de tiempo de 5 segundos
            time_window = 5.0
            while len(self.time_history) > 1 and (self.time_history[-1] - self.time_history[0] > time_window):
                self.time_history.pop(0)
                self.voltage_history_x.pop(0)
                self.voltage_history_y.pop(0)

        else:
            # Incluso cuando no está corriendo, calcular posición actual
            self.current_position = self.calculate_position(self.time)

    # Métodos para manejo de fases / δ similar al original:

    def _apply_delta_target(self):
        """Ajusta φy para que δ = φy - φx sea exactamente self.delta_target_deg en el tiempo actual."""
        fx = float(self.sine_params['frequency_x'])
        fy = float(self.sine_params['frequency_y'])
        df = fy - fx
        phase_x_deg = float(self.sine_params['phase_x'])
        t = self.time

        # φy = φx + δ_target - 360*(fy - fx)*t   (todo en grados)
        phase_y_deg = (phase_x_deg + float(self.delta_target_deg) - 360.0 * df * t) % 360.0

        # Evitar loop externo (lock gestionado por la UI)
        self.sine_params['phase_y'] = phase_y_deg

        # Limpia rastro
        self.trail_points_x.clear()
        self.trail_points_y.clear()

    def _set_delta_by_time_origin(self, delta_deg):
        """
        Fija el origen de tiempo t0 (o φy en 1:1) para que la fase relativa efectiva
        δef sea exactamente delta_deg en el instante actual.
        """
        fx = float(self.sine_params['frequency_x'])
        fy = float(self.sine_params['frequency_y'])
        phix = np.deg2rad(float(self.sine_params['phase_x']))
        phiy = np.deg2rad(float(self.sine_params['phase_y']))
        delta_des = np.deg2rad(float(delta_deg))

        denom = 2.0 * np.pi * (fy - fx)
        if abs(denom) < 1e-12:
            # Caso 1:1 → δ no depende de t0. Ajustamos φy = φx + δ (mod 360).
            new_phiy_deg = (np.rad2deg((phix + delta_des)) % 360.0)
            self.sine_params['phase_y'] = new_phiy_deg
        else:
            # Elegimos t0 tal que: (phiy - phix) + 2π(fy - fx)(t - t0) = δ_des  → resolver t0
            t = self.time
            self.t0 = t - (delta_des - (phiy - phix)) / denom

        # Limpiamos rastro
        self.trail_points_x.clear()
        self.trail_points_y.clear()

    # control simple
    def start(self):
        self.is_running = True

    def stop(self):
        self.is_running = False

    def reset(self):
        self.is_running = False
        self.time = 0.0
        self.trail_points_x = []
        self.trail_points_y = []
        self.current_position = {'x': 0.0, 'y': 0.0}
        self.voltage_history_x = []
        self.voltage_history_y = []
        self.time_history = []
        self.t0 = 0.0

# -----------------------------
# Clase UI con PyQt6 + Matplotlib
# -----------------------------
class CRTGui(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simulación CRT")
        self.logic = CRTSimulationLogic()

        # Estilo general (tema oscuro moderno)
        self.setMinimumSize(1400, 820)
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                color: #e6e6e6;
                font-family: "DejaVu Sans", "Segoe UI", sans-serif;
            }
            QGroupBox {
                border: 1px solid rgba(255,255,255,0.07);
                border-radius: 10px;
                margin-top: 6px;
                padding: 6px;
                background-color: rgba(255,255,255,0.01);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
                color: #a8ffcf;
                font-weight: 600;
            }
            QLabel#titleLabel {
                font-size: 18px;
                font-weight: 700;
                color: #ffffff;
            }
            QLabel.infoLabel {
                font-family: monospace;
                color: #f5f5f5;
            }
            QPushButton {
                border-radius: 6px;
                padding: 6px;
            }
            QPushButton#startBtn { background-color: #21a179; color: white; }
            QPushButton#stopBtn { background-color: #d9534f; color: white; }
            QPushButton#resetBtn { background-color: #ff8c00; color: white; }
            QSlider {
                background: transparent;
            }
        """)

        self._build_ui()
        self._connect_signals()

        # Timer para la animación (reemplaza FuncAnimation loop)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(int(self.logic.dt * 1000))  # ms
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    # -------------------------
    # Construcción de UI
    # -------------------------
    def _build_ui(self):
        # Layout principal
        main_layout = QVBoxLayout()
        header = QLabel("Simulación de Tubo de Rayos Catódicos (CRT)")
        header.setObjectName("titleLabel")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(header)

        content_layout = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()

        # --- Panel principal de gráficos (en un groupbox) ---
        graph_group = QGroupBox("Visualizaciones")
        graph_layout = QGridLayout()
        graph_group.setLayout(graph_layout)

        # Crear 4 canvases: lateral, superior, pantalla, y panel de voltajes (dos subplots)
        # Lateral view
        self.fig_lateral = Figure(figsize=(4, 2.6), dpi=100, facecolor="#292828")
        self.canvas_lateral = FigureCanvas(self.fig_lateral)
        self.ax_lateral = self.fig_lateral.add_subplot(111)
        self._init_lateral_axes()

        # Superior view
        self.fig_superior = Figure(figsize=(4, 2.6), dpi=100, facecolor="#292828")
        self.canvas_superior = FigureCanvas(self.fig_superior)
        self.ax_superior = self.fig_superior.add_subplot(111)
        self._init_superior_axes()

        # Screen view
        self.fig_screen = Figure(figsize=(4, 4), dpi=100, facecolor="#292828")
        self.canvas_screen = FigureCanvas(self.fig_screen)
        self.ax_screen = self.fig_screen.add_subplot(111)
        self._init_screen_axes()

        # Voltages view: two subplots stacked
        self.fig_volt = Figure(figsize=(6, 2.4), dpi=100, facecolor="#292828")
        self.canvas_volt = FigureCanvas(self.fig_volt)
        self.ax_vx = self.fig_volt.add_subplot(211)
        self.ax_vy = self.fig_volt.add_subplot(212)
        self._init_voltage_axes()

        graph_layout.addWidget(self.canvas_lateral, 0, 0)
        graph_layout.addWidget(self.canvas_superior, 0, 1)
        graph_layout.addWidget(self.canvas_screen, 0, 2, 2, 1) 
        graph_layout.addWidget(self.canvas_volt, 1, 0, 1, 2)

        left_col.addWidget(graph_group)

        # --- Panel de controles (derecha arriba) ---
        controls_group = QGroupBox("Controles")
        controls_layout = QGridLayout()
        controls_group.setLayout(controls_layout)

        row = 0
        # Aceleración
        lbl_acc = QLabel("Voltaje Aceleración (V)")
        self.spin_acc = QSpinBox()
        self.spin_acc.setRange(500, 5000)
        self.spin_acc.setSingleStep(100)
        self.spin_acc.setValue(int(self.logic.acceleration_voltage))
        controls_layout.addWidget(lbl_acc, row, 0)
        controls_layout.addWidget(self.spin_acc, row, 1)
        row += 1

        # Persistencia
        lbl_pers = QLabel("Persistencia (puntos)")
        self.spin_pers = QSpinBox()
        self.spin_pers.setRange(10, 1000)
        self.spin_pers.setValue(int(self.logic.persistence))
        controls_layout.addWidget(lbl_pers, row, 0)
        controls_layout.addWidget(self.spin_pers, row, 1)
        row += 1

        # Mode group (Manual / Lissajous)
        lbl_mode = QLabel("Modo")
        self.radio_manual = QRadioButton("Manual")
        self.radio_liss = QRadioButton("Lissajous")
        self.radio_manual.setChecked(True)
        mode_box = QHBoxLayout()
        mode_box.addWidget(self.radio_manual)
        mode_box.addWidget(self.radio_liss)
        controls_layout.addWidget(lbl_mode, row, 0)
        controls_layout.addLayout(mode_box, row, 1)
        row += 1

        # Manual Vx / Vy
        lbl_vx = QLabel("Voltaje X Manual (V)")
        self.slider_vx = QSlider(Qt.Orientation.Horizontal)
        self.slider_vx.setRange(-100, 100)
        self.slider_vx.setValue(int(self.logic.manual_vx))
        controls_layout.addWidget(lbl_vx, row, 0)
        controls_layout.addWidget(self.slider_vx, row, 1)
        row += 1

        lbl_vy = QLabel("Voltaje Y Manual (V)")
        self.slider_vy = QSlider(Qt.Orientation.Horizontal)
        self.slider_vy.setRange(-100, 100)
        self.slider_vy.setValue(int(self.logic.manual_vy))
        controls_layout.addWidget(lbl_vy, row, 0)
        controls_layout.addWidget(self.slider_vy, row, 1)
        row += 1

        # Sinusoidales: amplitud / frecuencia / fase
        group_sin = QGroupBox("Señales sinusoidales (Lissajous)")
        sin_layout = QGridLayout()
        group_sin.setLayout(sin_layout)

        # Amplitudes
        sin_layout.addWidget(QLabel("Amplitud X (V)"), 0, 0)
        self.spin_amp_x = QSpinBox(); self.spin_amp_x.setRange(0, 200); self.spin_amp_x.setValue(int(self.logic.sine_params['amplitude_x']))
        sin_layout.addWidget(self.spin_amp_x, 0, 1)
        sin_layout.addWidget(QLabel("Amplitud Y (V)"), 1, 0)
        self.spin_amp_y = QSpinBox(); self.spin_amp_y.setRange(0, 200); self.spin_amp_y.setValue(int(self.logic.sine_params['amplitude_y']))
        sin_layout.addWidget(self.spin_amp_y, 1, 1)

        # Frequencies (double)
        sin_layout.addWidget(QLabel("Freq X (Hz)"), 2, 0)
        self.dspin_fx = QDoubleSpinBox(); self.dspin_fx.setRange(0.1, 100.0); self.dspin_fx.setSingleStep(0.1)
        self.dspin_fx.setValue(float(self.logic.sine_params['frequency_x']))
        sin_layout.addWidget(self.dspin_fx, 2, 1)

        sin_layout.addWidget(QLabel("Freq Y (Hz)"), 3, 0)
        self.dspin_fy = QDoubleSpinBox(); self.dspin_fy.setRange(0.1, 100.0); self.dspin_fy.setSingleStep(0.1)
        self.dspin_fy.setValue(float(self.logic.sine_params['frequency_y']))
        sin_layout.addWidget(self.dspin_fy, 3, 1)

        # Phases
        sin_layout.addWidget(QLabel("Fase X (°)"), 4, 0)
        self.dspin_phix = QDoubleSpinBox(); self.dspin_phix.setRange(0.0, 360.0); self.dspin_phix.setSingleStep(1.0)
        self.dspin_phix.setValue(float(self.logic.sine_params['phase_x']))
        sin_layout.addWidget(self.dspin_phix, 4, 1)

        sin_layout.addWidget(QLabel("Fase Y (°)"), 5, 0)
        self.dspin_phiy = QDoubleSpinBox(); self.dspin_phiy.setRange(0.0, 360.0); self.dspin_phiy.setSingleStep(1.0)
        self.dspin_phiy.setValue(float(self.logic.sine_params['phase_y']))
        sin_layout.addWidget(self.dspin_phiy, 5, 1)

        # Ratio and delta presets (radio buttons)
        ratio_box = QGroupBox("Relación de frecuencias")
        rb_layout = QVBoxLayout()
        self.rb_ratio_11 = QRadioButton("1:1"); self.rb_ratio_12 = QRadioButton("1:2")
        self.rb_ratio_13 = QRadioButton("1:3"); self.rb_ratio_23 = QRadioButton("2:3")
        self.rb_ratio_11.setChecked(True)
        rb_layout.addWidget(self.rb_ratio_11); rb_layout.addWidget(self.rb_ratio_12)
        rb_layout.addWidget(self.rb_ratio_13); rb_layout.addWidget(self.rb_ratio_23)
        ratio_box.setLayout(rb_layout)

        delta_box = QGroupBox("δ predefinidas")
        db_layout = QVBoxLayout()
        self.rb_d0 = QRadioButton("δ=0"); self.rb_d14 = QRadioButton("δ=π/4")
        self.rb_d12 = QRadioButton("δ=π/2"); self.rb_d34 = QRadioButton("δ=3π/4"); self.rb_d1 = QRadioButton("δ=π")
        self.rb_d0.setChecked(True)
        db_layout.addWidget(self.rb_d0); db_layout.addWidget(self.rb_d14)
        db_layout.addWidget(self.rb_d12); db_layout.addWidget(self.rb_d34); db_layout.addWidget(self.rb_d1)
        delta_box.setLayout(db_layout)

        # Botones de control: iniciar/parar/reset
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("INICIAR"); self.btn_start.setObjectName("startBtn")
        self.btn_stop = QPushButton("PARAR"); self.btn_stop.setObjectName("stopBtn")
        self.btn_reset = QPushButton("RESET"); self.btn_reset.setObjectName("resetBtn")
        btn_layout.addWidget(self.btn_start); btn_layout.addWidget(self.btn_stop); btn_layout.addWidget(self.btn_reset)

        # Panel de información (monoespaciado)
        info_group = QGroupBox("Información del Sistema")
        info_layout = QVBoxLayout()
        self.lbl_info = QLabel("", self)
        self.lbl_info.setObjectName("info")
        self.lbl_info.setStyleSheet("QLabel { font-family: 'Courier New', monospace; color: #fefefe; }")
        self.lbl_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        info_layout.addWidget(self.lbl_info)
        info_group.setLayout(info_layout)

        # Poner elementos en controls_layout
        controls_layout.addWidget(group_sin, row, 0, 1, 2)
        row += 1
        controls_layout.addWidget(ratio_box, row, 0)
        controls_layout.addWidget(delta_box, row, 1)
        row += 1
        controls_layout.addLayout(btn_layout, row, 0, 1, 2)
        row += 1
        controls_layout.addWidget(info_group, row, 0, 1, 2)

        right_col.addWidget(controls_group)

        # Añadir left_col (gráficos) y right_col (controles) al layout principal
        content_layout.addLayout(left_col, 2)
        content_layout.addLayout(right_col, 1)
        main_layout.addLayout(content_layout)

        # Footer pequeño: instrucciones
        footer = QLabel("Modo Manual: mueve Vx/Vy. Modo Lissajous: ajusta amplitud, frecuencia y fase.")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #bdbdbd; font-size: 11px;")
        main_layout.addWidget(footer)

        self.setLayout(main_layout)

        # Agrupar radios para manejo fácil
        self.ratio_group = QButtonGroup(self)
        self.ratio_group.addButton(self.rb_ratio_11)
        self.ratio_group.addButton(self.rb_ratio_12)
        self.ratio_group.addButton(self.rb_ratio_13)
        self.ratio_group.addButton(self.rb_ratio_23)

        self.delta_group = QButtonGroup(self)
        self.delta_group.addButton(self.rb_d0)
        self.delta_group.addButton(self.rb_d14)
        self.delta_group.addButton(self.rb_d12)
        self.delta_group.addButton(self.rb_d34)
        self.delta_group.addButton(self.rb_d1)

    # -------------------------
    # Inicialización detallada de los ejes (se mantiene look similar al original)
    # -------------------------
    def _init_lateral_axes(self):
        ax = self.ax_lateral
        ax.clear()
        ax.set_xlim(0, 300)
        ax.set_ylim(50, 150)
        ax.set_title("Vista Lateral (Deflexión Y)", color='#64ffda', fontsize=12, weight='bold')
        ax.set_facecolor('#0a0a0a')

        # Dibujar estructura del CRT
        cannon = ax.add_patch(plt_rect((20, 90), 30, 20, edgecolor='white', linewidth=2))
        ax.plot([120, 180], [75, 75], color='white', linewidth=3, alpha=0.85)
        ax.plot([120, 180], [125, 125], color='white', linewidth=3, alpha=0.85)
        ax.text(150, 70, 'Placa +', ha='center', va='top', color='red', fontsize=9)
        ax.text(150, 130, 'Placa -', ha='center', va='bottom', color='blue', fontsize=9)
        ax.plot([260, 260], [60, 140], color='white', linewidth=4)
        ax.text(265, 100, 'Pantalla', ha='left', va='center', color='white', fontsize=9)

        # beam & dot
        self.beam_lateral, = ax.plot([], [], color='#7CFC00', linewidth=3, alpha=0.9)
        self.dot_lateral, = ax.plot([], [], 'o', color='#ff5f5f', markersize=8, alpha=0.9)

        ax.grid(True, alpha=0.15)
        ax.set_xticks([]); ax.set_yticks([])

    def _init_superior_axes(self):
        ax = self.ax_superior
        ax.clear()
        ax.set_xlim(0, 300)
        ax.set_ylim(50, 150)
        ax.set_title("Vista Superior (Deflexión X)", color='#7CFC00', fontsize=12, weight='bold')
        ax.set_facecolor('#0a0a0a')

        cannon = ax.add_patch(plt_rect((20, 90), 30, 20, edgecolor='white', linewidth=2))
        ax.plot([120, 180], [75, 75], color='white', linewidth=3, alpha=0.85)
        ax.plot([120, 180], [125, 125], color='white', linewidth=3, alpha=0.85)
        ax.text(150, 70, 'Placa +', ha='center', va='top', color='red', fontsize=9)
        ax.text(150, 130, 'Placa -', ha='center', va='bottom', color='blue', fontsize=9)
        ax.plot([260, 260], [60, 140], color='white', linewidth=4)
        ax.text(265, 100, 'Pantalla', ha='left', va='center', color='white', fontsize=9)

        self.beam_superior, = ax.plot([], [], color='#7CFC00', linewidth=3, alpha=0.9)
        self.dot_superior, = ax.plot([], [], 'o', color='#ff5f5f', markersize=8, alpha=0.9)

        ax.grid(True, alpha=0.15)
        ax.set_xticks([]); ax.set_yticks([])

    def _init_screen_axes(self):
        ax = self.ax_screen
        ax.clear()
        ax.set_xlim(-110, 110)
        ax.set_ylim(-70, 70)
        ax.set_title("Pantalla del CRT", color='#FFD700', fontsize=14, weight='bold', pad=12)
        ax.set_facecolor('#0a0a0a')

        ax.grid(True, alpha=0.25, color='gray', linewidth=0.6)
        ax.axhline(y=0, color='gray', linewidth=1.2, alpha=0.6)
        ax.axvline(x=0, color='gray', linewidth=1.2, alpha=0.6)
        frame = ax.add_patch(plt_rect((-100, -60), 200, 120, edgecolor='white', linewidth=2, fill=False))

        # trail y punto actual
        self.trail_line, = ax.plot([], [], color='#00FF7F', linestyle='-', alpha=0.7, linewidth=2)
        self.current_dot, = ax.plot([], [], marker='o', markersize=12, markeredgecolor='red', markerfacecolor='yellow',
                                    markeredgewidth=2, alpha=0.95)
        ax.set_aspect('equal', 'box')
        ax.set_xlabel('Posición X', color='white')
        ax.set_ylabel('Posición Y', color='white')

    def _init_voltage_axes(self):
        ax1 = self.ax_vx
        ax2 = self.ax_vy
        ax1.clear(); ax2.clear()
        ax1.set_title("Voltaje Horizontal (X)", color='#7CFC00', fontsize=11)
        ax1.set_ylabel('Voltaje (V)', color='white')
        ax1.grid(True, alpha=0.2)
        ax1.set_facecolor('#111111')
        ax1.set_ylim(-110, 110)

        ax2.set_title("Voltaje Vertical (Y)", color='#00CED1', fontsize=11)
        ax2.set_ylabel('Voltaje (V)', color='white')
        ax2.set_xlabel('Tiempo (s)', color='white')
        ax2.grid(True, alpha=0.2)
        ax2.set_facecolor('#111111')
        ax2.set_ylim(-110, 110)

        self.voltage_x_line, = ax1.plot([], [], color='#7CFC00', linewidth=2.5)
        self.voltage_y_line, = ax2.plot([], [], color='#00CED1', linewidth=2.5)
        self.time_line_x = ax1.axvline(x=0.0, color='red', linewidth=1.6, alpha=0.9)
        self.time_line_y = ax2.axvline(x=0.0, color='red', linewidth=1.6, alpha=0.9)

    # -------------------------
    # Signals / eventos
    # -------------------------
    def _connect_signals(self):
        # Controls
        self.spin_acc.valueChanged.connect(self._on_acc_changed)
        self.spin_pers.valueChanged.connect(self._on_pers_changed)
        self.slider_vx.valueChanged.connect(self._on_vx_changed)
        self.slider_vy.valueChanged.connect(self._on_vy_changed)
        self.radio_manual.toggled.connect(self._on_mode_changed)
        self.radio_liss.toggled.connect(self._on_mode_changed)

        # Sinusoidal
        self.spin_amp_x.valueChanged.connect(self._on_ampx_changed)
        self.spin_amp_y.valueChanged.connect(self._on_ampy_changed)
        self.dspin_fx.valueChanged.connect(self._on_fx_changed)
        self.dspin_fy.valueChanged.connect(self._on_fy_changed)
        self.dspin_phix.valueChanged.connect(self._on_phix_changed)
        self.dspin_phiy.valueChanged.connect(self._on_phiy_changed)

        # Radios delta / ratios
        self.ratio_group.buttonClicked.connect(self._on_ratio_changed)
        self.delta_group.buttonClicked.connect(self._on_delta_preset_changed)

        # Botones
        self.btn_start.clicked.connect(self._on_start)
        self.btn_stop.clicked.connect(self._on_stop)
        self.btn_reset.clicked.connect(self._on_reset)

    # -------------------------
    # Eventos UI que actualizan la lógica
    # -------------------------
    def _on_acc_changed(self, val):
        self.logic.acceleration_voltage = int(val)
        # recalcular posición si está en pausa
        if not self.logic.is_running:
            self.logic.current_position = self.logic.calculate_position(self.logic.time)

    def _on_pers_changed(self, val):
        self.logic.persistence = int(val)
        # recortar rastro si hace falta
        if len(self.logic.trail_points_x) > self.logic.persistence:
            self.logic.trail_points_x = self.logic.trail_points_x[-self.logic.persistence:]
            self.logic.trail_points_y = self.logic.trail_points_y[-self.logic.persistence:]

    def _on_vx_changed(self, val):
        self.logic.manual_vx = float(val)
        if not self.logic.is_running and self.logic.mode == 'manual':
            self.logic.current_position = self.logic.calculate_position(self.logic.time)

    def _on_vy_changed(self, val):
        self.logic.manual_vy = float(val)
        if not self.logic.is_running and self.logic.mode == 'manual':
            self.logic.current_position = self.logic.calculate_position(self.logic.time)

    def _on_mode_changed(self, checked):
        # Cambia modo dependiente del radio seleccionado
        if self.radio_manual.isChecked():
            self.logic.mode = 'manual'
            # ajustar límites pantalla como en original
            self.ax_screen.set_xlim(-110, 110)
            self.ax_screen.set_ylim(-70, 70)
        else:
            self.logic.mode = 'sinusoidal'
            self.ax_screen.set_xlim(-100, 100)
            self.ax_screen.set_ylim(-100, 100)
        # limpiar rastro
        self.logic.trail_points_x.clear()
        self.logic.trail_points_y.clear()

    def _on_ampx_changed(self, val):
        self.logic.sine_params['amplitude_x'] = float(val)

    def _on_ampy_changed(self, val):
        self.logic.sine_params['amplitude_y'] = float(val)

    def _on_fx_changed(self, val):
        self.logic.sine_params['frequency_x'] = float(val)
        # ajustar t0 / delta coherente si es necesario
        self.logic._set_delta_by_time_origin(self.logic.delta_target_deg)

    def _on_fy_changed(self, val):
        self.logic.sine_params['frequency_y'] = float(val)
        self.logic._set_delta_by_time_origin(self.logic.delta_target_deg)

    def _on_phix_changed(self, val):
        self.logic.sine_params['phase_x'] = float(val)
        # si hay un delta target explícito, recalculamos phi_y
        # (evitar loops: manejado internamente)
        self.logic._apply_delta_target()

    def _on_phiy_changed(self, val):
        self.logic.sine_params['phase_y'] = float(val)

    def _on_ratio_changed(self, btn):
        label = btn.text()
        ratios = {'1:1': (1.0, 1.0), '1:2': (1.0, 2.0), '1:3': (1.0, 3.0), '2:3': (2.0, 3.0)}
        if label in ratios:
            fx, fy = ratios[label]
            self.dspin_fx.setValue(fx)
            self.dspin_fy.setValue(fy)
            self.logic.sine_params['frequency_x'] = fx
            self.logic.sine_params['frequency_y'] = fy
            self.logic.trail_points_x.clear(); self.logic.trail_points_y.clear()
            # fijar t0 para mantener delta relativo
            self.logic._set_delta_by_time_origin(self.logic.delta_target_deg)

    def _on_delta_preset_changed(self, btn):
        mapping = {'δ=0': 0.0, 'δ=π/4': 45.0, 'δ=π/2': 90.0, 'δ=3π/4': 135.0, 'δ=π': 180.0}
        label = btn.text()
        self.logic.delta_target_deg = mapping.get(label, 0.0)
        # Ajustar fases acorde
        if self.logic.sine_params['frequency_x'] == self.logic.sine_params['frequency_y']:
            # caso 1:1 => ajustar directamente phases
            new_phiy = (float(self.logic.sine_params['phase_x']) + self.logic.delta_target_deg) % 360.0
            self.dspin_phiy.setValue(new_phiy)
            self.logic.sine_params['phase_y'] = new_phiy
        else:
            # fijar t0 de forma que la delta sea la deseada en el instante actual
            self.logic._set_delta_by_time_origin(self.logic.delta_target_deg)

        # limpiar rastro
        self.logic.trail_points_x.clear(); self.logic.trail_points_y.clear()

    def _on_start(self):
        self.logic.start()

    def _on_stop(self):
        self.logic.stop()

    def _on_reset(self):
        self.logic.reset()
        # restablecer vistas
        self._redraw_all()

    # -------------------------
    # Tick del timer -> avanza simulación y actualiza plots
    # -------------------------
    def _on_tick(self):
        # Avanzar lógica
        self.logic.step_time()
        # Refrescar gráficos
        self._update_lateral()
        self._update_superior()
        self._update_screen()
        self._update_voltages()
        self._update_info()

        # Forzar redraw canvases
        self.canvas_lateral.draw_idle()
        self.canvas_superior.draw_idle()
        self.canvas_screen.draw_idle()
        self.canvas_volt.draw_idle()

    # -------------------------
    # Actualizaciones gráficas
    # -------------------------
    def _update_lateral(self):
        deflection_y = self.logic.current_position['y'] * 0.3  # Escalar para la vista
        beam_x = [50, 120, 180, 260]
        beam_y = [100, 100, 100 + deflection_y * 0.5, 100 + deflection_y]
        self.beam_lateral.set_data(beam_x, beam_y)
        self.dot_lateral.set_data([260], [100 + deflection_y])

    def _update_superior(self):
        deflection_x = self.logic.current_position['x'] * 0.3  # Escalar para la vista
        beam_x = [50, 120, 180, 260]
        beam_y = [100, 100, 100 + deflection_x * 0.5, 100 + deflection_x]
        self.beam_superior.set_data(beam_x, beam_y)
        self.dot_superior.set_data([260], [100 + deflection_x])

    def _update_screen(self):
        # Trail
        if len(self.logic.trail_points_x) > 1:
            self.trail_line.set_data(self.logic.trail_points_x, self.logic.trail_points_y)
        else:
            self.trail_line.set_data([], [])
        # Punto actual
        self.current_dot.set_data([self.logic.current_position['x']], [self.logic.current_position['y']])

    def _update_voltages(self):
        if len(self.logic.time_history) > 1:
            self.voltage_x_line.set_data(self.logic.time_history, self.logic.voltage_history_x)
            self.voltage_y_line.set_data(self.logic.time_history, self.logic.voltage_history_y)
            time_min = self.logic.time_history[0]
            time_max = self.logic.time_history[-1]
            self.ax_vx.set_xlim(time_min, max(time_max, time_min + 1.0))
            self.ax_vy.set_xlim(time_min, max(time_max, time_min + 1.0))
            if self.logic.is_running:
                self.time_line_x.set_xdata([self.logic.time, self.logic.time])
                self.time_line_y.set_xdata([self.logic.time, self.logic.time])
        else:
            current = self.logic.get_voltages(self.logic.time)
            self.voltage_x_line.set_data([self.logic.time], [current['vx']])
            self.voltage_y_line.set_data([self.logic.time], [current['vy']])
            self.ax_vx.set_xlim(self.logic.time - 0.5, self.logic.time + 0.5)
            self.ax_vy.set_xlim(self.logic.time - 0.5, self.logic.time + 0.5)

    def _update_info(self):
        vel = self.logic.calculate_initial_velocity()
        voltages = self.logic.get_voltages(self.logic.time)
        status = "EJECUTANDO" if self.logic.is_running else "PAUSADO"

        info_str = (
            f"   {status}\n\n"
            f"Tiempo: {self.logic.time:6.2f} s\n"
            f"Modo: {self.logic.mode.upper()}\n"
            f"Aceleración: {int(self.logic.acceleration_voltage):5d} V\n"
            f"Vel. Inicial: {vel/1e6:5.1f} Mm/s\n\n"
            f"VOLTAJES ACTUALES:\n"
            f"  X: {voltages['vx']:+7.1f} V\n"
            f"  Y: {voltages['vy']:+7.1f} V\n\n"
            f"POSICIÓN PANTALLA:\n"
            f"  X: {self.logic.current_position['x']:+7.1f}\n"
            f"  Y: {self.logic.current_position['y']:+7.1f}\n\n"
            f"Rastro: {len(self.logic.trail_points_x)} puntos"
        )
        self.lbl_info.setText(info_str)

    def _redraw_all(self):
        # limpezas de ejes y redraw completo
        self._init_lateral_axes()
        self._init_superior_axes()
        self._init_screen_axes()
        self._init_voltage_axes()
        self.canvas_lateral.draw_idle()
        self.canvas_superior.draw_idle()
        self.canvas_screen.draw_idle()
        self.canvas_volt.draw_idle()

# -----------------------------
# Utilidades gráficas: rectángulos con bordes redondeados
# -----------------------------
def plt_rect(xy, w, h, **kwargs):
    """
    Devuelve un FancyBboxPatch similar a Rectangle pero que se puede usar
    con matplotlib axes en el backend de PyQt.
    xy: (x,y) bottom-left
    """
    from matplotlib.patches import FancyBboxPatch
    x, y = xy
    boxstyle = "round,pad=0.02,rounding_size=6"
    return FancyBboxPatch((x, y), w, h, boxstyle=boxstyle, linewidth=kwargs.get('linewidth', 1.5),
                         edgecolor=kwargs.get('edgecolor', 'white'), facecolor=kwargs.get('facecolor', 'none'),
                         mutation_aspect=1.0)

# -----------------------------
# Main
# -----------------------------
def main():
    app = QApplication(sys.argv)
    gui = CRTGui()
    gui.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
