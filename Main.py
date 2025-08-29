import nympy as np

class CRTSimulation: 
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


        self.setup_interface()

    def calculate_initial_velocity(self):
       energia_cinetica = self.ELECTRON_CHARGE * self.acceleration_voltage
       return np.sqrt(2 * energia_cinetica / self.ELECTRON_MASS)


   def calculate_deflection (self,voltage, PLATE_LENGTH, PLATE_SEPARATION, initial_velocity):
       electric_field = voltage / PLATE_SEPARATION
       force = self.ELECTRON_CHARGE * electric_field
       acceleration = force/ self.ELECTRON_MASS
       time_in_plates = PLATE_LENGTH / initial_velocity
       
       deflection_in_plates = 0.5 * acceleration * time_in_plates **2 
       velocity_after_plates = acceleration * time_in_plates
       time_to_screen = (self.CRT_LENGTH - PLATE_LENGTH) / initial_velocity
       
       additional_deflection = velocity_after_plates * time_to_screen

       return deflection_in_plates + additional_deflection
   
   
    def get_voltages(self, t): 
        if self.mode == 'manual':
            return{'vx': self.manual_vx, 'vy': self.manual_vy}
        else: 
            vx = (self.sine_params['amplitude_x'] * 
                  np.sin(2 * np.pi * self.sine_params['frequency_x'] * t + 
                         np.radians(self.sine_params['phase_x'])))
            vy = (self.sine_params['amplitude_y'] * 
                  np.sin(2 * np.pi * self.sine_params['frequency_y'] * t + 
                         np.radians(self.sine_params['phase_y'])))
            return {'vx': vx, 'vy': vy}
        