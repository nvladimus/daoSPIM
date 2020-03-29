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
    'exposure_ms': 20.0,
    'pixel_um': 6.5,
    'image_width': 2048,
    'image_height': 2048,
    # triggers in
    'trig_in': False,
    'trig_in_mode': 'Normal',  # 'Normal', 'Start'
    'trig_in_source': 'external',  # 'internal', 'external', 'software', 'master pulse'
    'trig_in_type': 'SYNCREADOUT',  # 'EDGE', 'LEVEL', 'SYNCREADOUT'
    # triggers out
    'trig_out': True,
    'trig_out_kind': 'EXPOSURE',  # 'LOW', 'EXPOSURE', 'PROGRAMMABLE', 'TRIGGER READY', 'HIGH'
    # misc
    'subtract_background': 100 # value to subtract from image intensity when saving
}

etl = {
    'model': 'Optotune EL-16-40-TC-VIS-5D-C',
    'port': 'COM11'
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

