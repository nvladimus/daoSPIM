'''
Hardware configuration
'''

lightsheet_generation = {
    'swipe_duration_ms': 1.0,
    'galvo_offset0_volts': -0.35,
    'galvo_offset1_volts': 0.35,
    'galvo_amp0_volts': 0.60,
    'galvo_amp1_volts': 0.60,
    'laser_max_volts': 5.0,
    'laser_set_volts': 1.0,
    'arduino_switcher_port': 'COM6'
}

camera = {
    'pixel_um': 6.5
}

stages = {
    'type': 'MHW',  # 'MHW' for Maerzhauser-Wetzlar
    'controller': 'Tango',
    'port': 'COM8',
    'baudrate': 57600,
    'x_speed_max': 2.0,  # mm/s
    'x_accel': 0.2  # m/s2
}
# deformable mirror
dm = {'diameter_mm': 15.0}

saving = {
    'root_folder': 'C:/Users/nvladim/Pictures/'
}

microscope = {
    'pixel_size_um': 0.14625
}

