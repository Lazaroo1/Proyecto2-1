import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.widgets import Slider, RadioButtons, Button
from matplotlib.gridspec import GridSpec

class CRTSimulation:
    def __init__(self):
        # Constantes físicas del CRT (simplificadas para mejor visualización)
        self.ELECTRON_CHARGE = 1.602e-19  # Coulombs
        self.ELECTRON_MASS = 9.109e-31   # kg
        self.CRT_LENGTH = 0.4            # metros
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
            'amplitude_x': 50,    # V
            'frequency_x': 1.0,   # Hz
            'phase_x': 0,         # grados
            'amplitude_y': 50,    # V
            'frequency_y': 1.0,   # Hz
            'phase_y': 90         # grados (para círculo inicial)
        }
        
        # Variables de simulación
        self.time = 0
        self.is_running = False
        self.trail_points_x = []
        self.trail_points_y = []
        self.current_position = {'x': 0, 'y': 0}
        self.voltage_history_x = []
        self.voltage_history_y = []
        self.time_history = []
        
        # Configurar la interfaz
        self.setup_interface()
    
    def calculate_initial_velocity(self):
        """Calcula la velocidad inicial del electrón"""
        kinetic_energy = self.ELECTRON_CHARGE * self.acceleration_voltage
        return np.sqrt(2 * kinetic_energy / self.ELECTRON_MASS)
    
    def calculate_deflection(self, voltage):
        """Calcula la deflexión del electrón (simplificada para visualización)"""
        if voltage == 0:
            return 0
        
        # Fórmula simplificada con factor de escala para visualización
        # En un CRT real sería mucho más compleja
        initial_velocity = self.calculate_initial_velocity()
        
        # Factor de deflexión proporcional al voltaje e inversamente proporcional a la aceleración
        deflection_factor = voltage / (self.acceleration_voltage / 1000)
        
        return deflection_factor * self.DEFLECTION_SCALE / 100000
    
    def get_voltages(self, t):
        """Obtiene los voltajes según el modo de operación"""
        if self.mode == 'manual':
            return {'vx': self.manual_vx, 'vy': self.manual_vy}
        else:
            vx = (self.sine_params['amplitude_x'] * 
                  np.sin(2 * np.pi * self.sine_params['frequency_x'] * t + 
                         np.radians(self.sine_params['phase_x'])))
            vy = (self.sine_params['amplitude_y'] * 
                  np.sin(2 * np.pi * self.sine_params['frequency_y'] * t + 
                         np.radians(self.sine_params['phase_y'])))
            return {'vx': vx, 'vy': vy}
    
    def calculate_position(self, t):
        """Calcula la posición del electrón en la pantalla"""
        voltages = self.get_voltages(t)
        
        deflection_x = self.calculate_deflection(voltages['vx'])
        deflection_y = self.calculate_deflection(voltages['vy'])
        
        # Escalar para coordenadas de pantalla visibles
        screen_x = deflection_x * 100  # Amplificar para visualización
        screen_y = deflection_y * 100
        
        # Limitar a los bordes de la pantalla
        screen_x = np.clip(screen_x, -100, 100)
        screen_y = np.clip(screen_y, -60, 60)
        
        return {'x': screen_x, 'y': screen_y}
    
    def setup_interface(self):
        """Configura la interfaz gráfica"""
        plt.style.use('dark_background')
        
        # Crear figura principal
        self.fig = plt.figure(figsize=(16, 10))
        self.fig.suptitle('Simulación de Tubo de Rayos Catódicos (CRT)', 
                         fontsize=16, color='white', y=0.95)
        
        # Crear layout con GridSpec
        gs = GridSpec(4, 6, figure=self.fig, hspace=0.5, wspace=0.4)
        
        # Vista lateral (deflexión Y)
        self.ax_lateral = self.fig.add_subplot(gs[0, 0:2])
        self.setup_lateral_view()
        
        # Vista superior (deflexión X)
        self.ax_superior = self.fig.add_subplot(gs[0, 2:4])
        self.setup_superior_view()
        
        # Pantalla principal
        self.ax_screen = self.fig.add_subplot(gs[0:2, 4:6])
        self.setup_screen_view()
        
        # Gráficas de voltajes
        self.ax_voltage_x = self.fig.add_subplot(gs[1, 0:2])
        self.ax_voltage_y = self.fig.add_subplot(gs[1, 2:4])
        self.setup_voltage_plots()
        
        # Panel de información
        self.ax_info = self.fig.add_subplot(gs[2, 4:6])
        self.setup_info_panel()
        
        # Configurar controles
        self.setup_controls(gs)
        
        # Configurar animación
        self.ani = animation.FuncAnimation(
            self.fig, self.animate, interval=50, blit=False, cache_frame_data=False
        )
        
        # Ajustar layout
        plt.subplots_adjust(bottom=0.2, top=0.90)
    
    def setup_lateral_view(self):
        """Configura la vista lateral del CRT"""
        self.ax_lateral.set_xlim(0, 300)
        self.ax_lateral.set_ylim(50, 150)
        self.ax_lateral.set_title('Vista Lateral (Deflexión Y)', color='cyan', fontsize=12)
        self.ax_lateral.set_facecolor('#0a0a0a')
        
        # Dibujar estructura del CRT
        # Cañón de electrones
        cannon = plt.Rectangle((20, 90), 30, 20, fill=False, 
                              edgecolor='white', linewidth=2)
        self.ax_lateral.add_patch(cannon)
        
        # Placas de deflexión vertical
        self.ax_lateral.plot([120, 180], [75, 75], 'white', linewidth=3, alpha=0.8)
        self.ax_lateral.plot([120, 180], [125, 125], 'white', linewidth=3, alpha=0.8)
        
        # Etiquetas de placas
        self.ax_lateral.text(150, 70, 'Placa +', ha='center', va='top', color='red', fontsize=8)
        self.ax_lateral.text(150, 130, 'Placa -', ha='center', va='bottom', color='blue', fontsize=8)
        
        # Pantalla
        self.ax_lateral.plot([260, 260], [60, 140], 'white', linewidth=4)
        self.ax_lateral.text(265, 100, 'Pantalla', ha='left', va='center', color='white', fontsize=8)
        
        # Líneas del haz (se actualizarán en animate)
        self.beam_lateral, = self.ax_lateral.plot([], [], 'lime', linewidth=3, alpha=0.9)
        self.dot_lateral, = self.ax_lateral.plot([], [], 'ro', markersize=10, alpha=0.9)
        
        self.ax_lateral.grid(True, alpha=0.2)
        self.ax_lateral.set_xticks([])
        self.ax_lateral.set_yticks([])
    
    def setup_superior_view(self):
        """Configura la vista superior del CRT"""
        self.ax_superior.set_xlim(0, 300)
        self.ax_superior.set_ylim(50, 150)
        self.ax_superior.set_title('Vista Superior (Deflexión X)', color='lime', fontsize=12)
        self.ax_superior.set_facecolor('#0a0a0a')
        
        # Dibujar estructura del CRT
        # Cañón de electrones
        cannon = plt.Rectangle((20, 90), 30, 20, fill=False, 
                              edgecolor='white', linewidth=2)
        self.ax_superior.add_patch(cannon)
        
        # Placas de deflexión horizontal
        self.ax_superior.plot([120, 180], [75, 75], 'white', linewidth=3, alpha=0.8)
        self.ax_superior.plot([120, 180], [125, 125], 'white', linewidth=3, alpha=0.8)
        
        # Etiquetas de placas
        self.ax_superior.text(150, 70, 'Placa +', ha='center', va='top', color='red', fontsize=8)
        self.ax_superior.text(150, 130, 'Placa -', ha='center', va='bottom', color='blue', fontsize=8)
        
        # Pantalla
        self.ax_superior.plot([260, 260], [60, 140], 'white', linewidth=4)
        self.ax_superior.text(265, 100, 'Pantalla', ha='left', va='center', color='white', fontsize=8)
        
        # Líneas del haz (se actualizarán en animate)
        self.beam_superior, = self.ax_superior.plot([], [], 'lime', linewidth=3, alpha=0.9)
        self.dot_superior, = self.ax_superior.plot([], [], 'ro', markersize=10, alpha=0.9)
        
        self.ax_superior.grid(True, alpha=0.2)
        self.ax_superior.set_xticks([])
        self.ax_superior.set_yticks([])
    
    def setup_screen_view(self):
        """Configura la vista de la pantalla"""
        self.ax_screen.set_xlim(-110, 110)
        self.ax_screen.set_ylim(-70, 70)
        self.ax_screen.set_title('Pantalla del CRT', color='yellow', fontsize=14, pad=20)
        self.ax_screen.set_facecolor('#0a0a0a')
        
        # Retícula
        self.ax_screen.grid(True, alpha=0.3, color='gray', linewidth=0.5)
        self.ax_screen.axhline(y=0, color='gray', linewidth=1.5, alpha=0.6)
        self.ax_screen.axvline(x=0, color='gray', linewidth=1.5, alpha=0.6)
        
        # Marco de la pantalla
        frame = plt.Rectangle((-100, -60), 200, 120, fill=False, 
                             edgecolor='white', linewidth=3)
        self.ax_screen.add_patch(frame)
        
        # Trail y punto actual
        self.trail_line, = self.ax_screen.plot([], [], 'g-', alpha=0.7, linewidth=2)
        self.current_dot, = self.ax_screen.plot([], [], 'yo', markersize=15, 
                                               markeredgecolor='red', markeredgewidth=2,
                                               alpha=0.9)
        
        self.ax_screen.set_aspect('equal')
        self.ax_screen.set_xlabel('Posición X', color='white')
        self.ax_screen.set_ylabel('Posición Y', color='white')
    
    def setup_voltage_plots(self):
        """Configura las gráficas de voltajes"""
        self.ax_voltage_x.set_title('Voltaje Horizontal (X)', color='lime', fontsize=12)
        self.ax_voltage_x.set_ylabel('Voltaje (V)', color='white')
        self.ax_voltage_x.grid(True, alpha=0.3)
        self.ax_voltage_x.set_facecolor('#1a1a1a')
        self.ax_voltage_x.set_ylim(-110, 110)
        
        self.ax_voltage_y.set_title('Voltaje Vertical (Y)', color='cyan', fontsize=12)
        self.ax_voltage_y.set_ylabel('Voltaje (V)', color='white')
        self.ax_voltage_y.set_xlabel('Tiempo (s)', color='white')
        self.ax_voltage_y.grid(True, alpha=0.3)
        self.ax_voltage_y.set_facecolor('#1a1a1a')
        self.ax_voltage_y.set_ylim(-110, 110)
        
        # Líneas de voltaje
        self.voltage_x_line, = self.ax_voltage_x.plot([], [], 'lime', linewidth=3)
        self.voltage_y_line, = self.ax_voltage_y.plot([], [], 'cyan', linewidth=3)
        
        # Línea de tiempo actual
        self.time_line_x = self.ax_voltage_x.axvline(x=0, color='red', linewidth=2, alpha=0.8)
        self.time_line_y = self.ax_voltage_y.axvline(x=0, color='red', linewidth=2, alpha=0.8)
    
    def setup_info_panel(self):
        """Configura el panel de información"""
        self.ax_info.set_xlim(0, 1)
        self.ax_info.set_ylim(0, 1)
        self.ax_info.axis('off')
        self.ax_info.set_title('Información del Sistema', color='orange', fontsize=12)
        
        # Texto de información (se actualizará en animate)
        self.info_text = self.ax_info.text(0.05, 0.95, '', transform=self.ax_info.transAxes,
                                          fontsize=11, color='white', verticalalignment='top',
                                          fontfamily='monospace')
    
    def setup_controls(self, gs):
        """Configura los controles deslizantes"""
        # Sliders principales - Fila 2
        ax_accel = self.fig.add_subplot(gs[2, 0])
        ax_accel.set_title('Voltaje Aceleración', fontsize=10, color='white')
        self.slider_acceleration = Slider(ax_accel, '', 500, 5000, 
                                         valinit=self.acceleration_voltage, valfmt='%d V',
                                         facecolor='lightblue', alpha=0.8)
        
        ax_persist = self.fig.add_subplot(gs[2, 1])
        ax_persist.set_title('Persistencia', fontsize=10, color='white')
        self.slider_persistence = Slider(ax_persist, '', 10, 300, 
                                        valinit=self.persistence, valfmt='%d',
                                        facecolor='lightgreen', alpha=0.8)
        
        # Controles manuales - Fila 3
        ax_vx = self.fig.add_subplot(gs[3, 0])
        ax_vx.set_title('Voltaje X Manual', fontsize=10, color='lime')
        self.slider_vx = Slider(ax_vx, '', -100, 100, 
                               valinit=self.manual_vx, valfmt='%d V',
                               facecolor='lime', alpha=0.6)
        
        ax_vy = self.fig.add_subplot(gs[3, 1])
        ax_vy.set_title('Voltaje Y Manual', fontsize=10, color='cyan')
        self.slider_vy = Slider(ax_vy, '', -100, 100, 
                               valinit=self.manual_vy, valfmt='%d V',
                               facecolor='cyan', alpha=0.6)
        
        # Controles sinusoidales - Canal X
        ax_amp_x = self.fig.add_subplot(gs[2, 2])
        ax_amp_x.set_title('Amplitud X', fontsize=9, color='lime')
        self.slider_amp_x = Slider(ax_amp_x, '', 0, 100, 
                                  valinit=self.sine_params['amplitude_x'], valfmt='%d V',
                                  facecolor='lime', alpha=0.6)
        
        ax_freq_x = self.fig.add_subplot(gs[2, 3])
        ax_freq_x.set_title('Frecuencia X', fontsize=9, color='lime')
        self.slider_freq_x = Slider(ax_freq_x, '', 0.1, 5.0, 
                                   valinit=self.sine_params['frequency_x'], valfmt='%.1f Hz',
                                   facecolor='lime', alpha=0.6)
        
        # Controles sinusoidales - Canal Y
        ax_amp_y = self.fig.add_subplot(gs[3, 2])
        ax_amp_y.set_title('Amplitud Y', fontsize=9, color='cyan')
        self.slider_amp_y = Slider(ax_amp_y, '', 0, 100, 
                                  valinit=self.sine_params['amplitude_y'], valfmt='%d V',
                                  facecolor='cyan', alpha=0.6)
        
        ax_freq_y = self.fig.add_subplot(gs[3, 3])
        ax_freq_y.set_title('Frecuencia Y', fontsize=9, color='cyan')
        self.slider_freq_y = Slider(ax_freq_y, '', 0.1, 5.0, 
                                   valinit=self.sine_params['frequency_y'], valfmt='%.1f Hz',
                                   facecolor='cyan', alpha=0.6)
        
        # Botones de modo
        ax_mode = self.fig.add_axes([0.02, 0.02, 0.08, 0.12])
        self.radio_mode = RadioButtons(ax_mode, ('Manual', 'Lissajous'), activecolor='yellow')
        self.radio_mode.set_active(0 if self.mode == 'manual' else 1)
        
        # Botones de control
        ax_start = self.fig.add_axes([0.12, 0.08, 0.06, 0.04])
        self.btn_start = Button(ax_start, 'INICIAR', color='green', hovercolor='lightgreen')
        
        ax_stop = self.fig.add_axes([0.19, 0.08, 0.06, 0.04])
        self.btn_stop = Button(ax_stop, 'PARAR', color='red', hovercolor='lightcoral')
        
        ax_reset = self.fig.add_axes([0.26, 0.08, 0.06, 0.04])
        self.btn_reset = Button(ax_reset, 'RESET', color='orange', hovercolor='yellow')
        
        # Conectar eventos
        self.slider_acceleration.on_changed(self.update_acceleration)
        self.slider_persistence.on_changed(self.update_persistence)
        self.slider_vx.on_changed(self.update_manual_vx)
        self.slider_vy.on_changed(self.update_manual_vy)
        self.slider_amp_x.on_changed(self.update_amp_x)
        self.slider_freq_x.on_changed(self.update_freq_x)
        self.slider_amp_y.on_changed(self.update_amp_y)
        self.slider_freq_y.on_changed(self.update_freq_y)
        self.radio_mode.on_clicked(self.update_mode)
        self.btn_start.on_clicked(self.start_simulation)
        self.btn_stop.on_clicked(self.stop_simulation)
        self.btn_reset.on_clicked(self.reset_simulation)
    
    def update_acceleration(self, val):
        self.acceleration_voltage = int(val)
        # Forzar recálculo inmediato
        if not self.is_running:
            self.current_position = self.calculate_position(self.time)
    
    def update_persistence(self, val):
        self.persistence = int(val)
    
    def update_manual_vx(self, val):
        self.manual_vx = val
        # Forzar recálculo inmediato en modo manual
        if not self.is_running and self.mode == 'manual':
            self.current_position = self.calculate_position(self.time)
    
    def update_manual_vy(self, val):
        self.manual_vy = val
        # Forzar recálculo inmediato en modo manual
        if not self.is_running and self.mode == 'manual':
            self.current_position = self.calculate_position(self.time)
    
    def update_amp_x(self, val):
        self.sine_params['amplitude_x'] = val
    
    def update_freq_x(self, val):
        self.sine_params['frequency_x'] = val
    
    def update_amp_y(self, val):
        self.sine_params['amplitude_y'] = val
    
    def update_freq_y(self, val):
        self.sine_params['frequency_y'] = val
    
    def update_mode(self, label):
        self.mode = 'manual' if label == 'Manual' else 'sinusoidal'
        # Limpiar rastro al cambiar modo
        self.trail_points_x = []
        self.trail_points_y = []
    
    def start_simulation(self, event):
        self.is_running = True
        print("Simulación iniciada")
    
    def stop_simulation(self, event):
        self.is_running = False
        print("⏸Simulación pausada")
    
    def reset_simulation(self, event):
        self.is_running = False
        self.time = 0
        self.trail_points_x = []
        self.trail_points_y = []
        self.current_position = {'x': 0, 'y': 0}
        self.voltage_history_x = []
        self.voltage_history_y = []
        self.time_history = []
        print("Simulación reiniciada")
    
    def animate(self, frame):
        """Función de animación principal"""
        if self.is_running:
            self.time += 0.05  # Incremento de tiempo
            
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
            while len(self.time_history) > 1 and self.time_history[-1] - self.time_history[0] > time_window:
                self.time_history.pop(0)
                self.voltage_history_x.pop(0)
                self.voltage_history_y.pop(0)
        else:
            # Incluso cuando no está corriendo, calcular posición actual
            self.current_position = self.calculate_position(self.time)
        
        # Actualizar todas las vistas SIEMPRE
        self.update_lateral_view()
        self.update_superior_view()
        self.update_screen_view()
        self.update_voltage_plots()
        self.update_info_panel()
        
        # Forzar redibujado
        self.fig.canvas.draw_idle()
        
        return []
    
    def update_lateral_view(self):
        """Actualiza la vista lateral"""
        deflection_y = self.current_position['y'] * 0.3  # Escalar para la vista
        
        # Trayectoria del haz
        beam_x = [50, 120, 180, 260]
        beam_y = [100, 100, 100 + deflection_y * 0.5, 100 + deflection_y]
        
        self.beam_lateral.set_data(beam_x, beam_y)
        self.dot_lateral.set_data([260], [100 + deflection_y])
    
    def update_superior_view(self):
        """Actualiza la vista superior"""
        deflection_x = self.current_position['x'] * 0.3  # Escalar para la vista
        
        # Trayectoria del haz
        beam_x = [50, 120, 180, 260]
        beam_y = [100, 100, 100 + deflection_x * 0.5, 100 + deflection_x]
        
        self.beam_superior.set_data(beam_x, beam_y)
        self.dot_superior.set_data([260], [100 + deflection_x])
    
    def update_screen_view(self):
        """Actualiza la vista de la pantalla"""
        # Actualizar rastro
        if len(self.trail_points_x) > 1:
            self.trail_line.set_data(self.trail_points_x, self.trail_points_y)
        else:
            self.trail_line.set_data([], [])
        
        # Actualizar punto actual
        self.current_dot.set_data([self.current_position['x']], [self.current_position['y']])
    
    def update_voltage_plots(self):
        """Actualiza las gráficas de voltajes"""
        if len(self.time_history) > 1:
            # Actualizar líneas de voltaje
            self.voltage_x_line.set_data(self.time_history, self.voltage_history_x)
            self.voltage_y_line.set_data(self.time_history, self.voltage_history_y)
            
            # Ajustar límites de tiempo
            time_min = self.time_history[0]
            time_max = self.time_history[-1]
            self.ax_voltage_x.set_xlim(time_min, max(time_max, time_min + 1))
            self.ax_voltage_y.set_xlim(time_min, max(time_max, time_min + 1))
            
            # Actualizar líneas de tiempo actual
            if self.is_running:
                self.time_line_x.set_xdata([self.time, self.time])
                self.time_line_y.set_xdata([self.time, self.time])
        else:
            # Mostrar voltajes actuales incluso sin historial
            current_voltages = self.get_voltages(self.time)
            self.voltage_x_line.set_data([self.time], [current_voltages['vx']])
            self.voltage_y_line.set_data([self.time], [current_voltages['vy']])
            
            self.ax_voltage_x.set_xlim(self.time - 0.5, self.time + 0.5)
            self.ax_voltage_y.set_xlim(self.time - 0.5, self.time + 0.5)
    
    def update_info_panel(self):
        """Actualiza el panel de información"""
        initial_velocity = self.calculate_initial_velocity()
        voltages = self.get_voltages(self.time)

        status = " EJECUTANDO" if self.is_running else " PAUSADO"

        info_str = f"""{status}

        Tiempo: {self.time:.2f} s
        Modo: {self.mode.upper()}
        Aceleración: {self.acceleration_voltage} V
        Vel. Inicial: {initial_velocity/1e6:.1f} Mm/s

        VOLTAJES ACTUALES:
          X: {voltages['vx']:+7.1f} V
          Y: {voltages['vy']:+7.1f} V

        POSICIÓN PANTALLA:
          X: {self.current_position['x']:+7.1f}
          Y: {self.current_position['y']:+7.1f}

        Rastro: {len(self.trail_points_x)} puntos"""
        
        self.info_text.set_text(info_str)
    
    def run(self):
        """Ejecuta la simulación"""
        plt.show()



def main():
    """Función principal para ejecutar la simulación"""
    print(" Simulación de Tubo de Rayos Catódicos (CRT)")
    print("=" * 50)
    print(" INSTRUCCIONES:")
    print("• Usar controles deslizantes para ajustar parámetros")
    print("• Cambiar entre modo Manual y Lissajous (botones radio)")
    print("• Controles: Iniciar, Parar, Reset")
    print("• En modo Lissajous: experimenta con diferentes frecuencias")
    print("")
    print(" SUGERENCIAS:")
    print("• Modo Manual: Mueve los sliders Vx y Vy para controlar el punto")
    print("• Modo Lissajous:")
    print("  - Frecuencias iguales (1:1) → Círculos y elipses")
    print("  - Relación 1:2 → Figura de ocho")
    print("  - Relación 2:3 → Figuras más complejas")
    print("• Ajusta la persistencia para rastros más largos o cortos")
    print("=" * 50)
    
    try:
        # Crear y ejecutar simulación
        crt_sim = CRTSimulation()
        crt_sim.run()
    except KeyboardInterrupt:
        print("\n Simulación terminada por el usuario.")
    except Exception as e:
        print(f" Error: {e}")
        print(" Asegúrate de tener instalado matplotlib: pip install matplotlib numpy")

if __name__ == "__main__":
    main()