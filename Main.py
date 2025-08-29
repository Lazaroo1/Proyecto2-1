Class CRTSimulation: 
    def __init__(self):
        # Constantes físicas del CRT
        self.ELECTRON_CHARGE = 1.602e-19  # Coulombs
        self.ELECTRON_MASS = 9.109e-31   # kg
        self.CRT_LENGTH = 0.4            # metros
        self.PLATE_LENGTH = 0.08         # metros
        self.PLATE_SEPARATION = 0.02     # metros
        self.SCREEN_SIZE = 0.2           # metros
        
        #contralables 
        self.acceleration_voltage = 2000
        self.manual_vx = 0 
        self.manual_vy = 0
        self.persistence = 100
        self.mode = "manual"
        
        self.sine_params = {
            "amplitude_x": 50,
            "frequency_x": 1.0,
            "phase_x": 0.0
            "amplitude_y": 50,
            "frequency_y": 1.0,
            "phase_y": 0.0
        }
        
        self.time = 0 
        self.is_running = False
        self.trail_points = []
        self.current_position = {'x': 0, 'y': 0}
        