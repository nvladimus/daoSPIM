'''This is class for generating triggered AO waveforms.
The AO task listens to the input TTL pulse (eg from camera) and generates
short finite AO waveform to synchronously move galvo and turn on the laser.
Copyright @nvladimus, 2020
'''

import numpy as np
import PyDAQmx as pd
import ctypes as ct
import widget as wd
import serial

config = {
    'swipe_duration_ms': 1.0,
    'galvo_offset0_volts': -0.32,
    'galvo_offset1_volts': 0.45,
    'galvo_amp0_volts': 0.60,
    'galvo_amp1_volts': 0.60,
    'laser_max_volts': 5.0,
    'laser_set_volts': 1.0,
    'arduino_switcher_port': 'COM6'
}


class LightsheetGenerator(QtCore.QObject):
    sig_update_gui = pyqtSignal()

    def __init__(self, dev_name='LS generator', gui_on=True, logger_name='Lightsheet'):
        super().__init__()
        self.config = config
        self.daqmx_task = self.serial_arduino = None
        self.initialized = self.ls_active = False
        # logger setup
        self.logger_name = logger_name
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        # GUI setup
        self.gui_on = gui_on
        if self.gui_on:
            self.logger.info("GUI activated")
            self.gui = wd.widget(dev_name)
            self._setup_gui()
            self.sig_update_gui.connect(self._update_gui)

    def create_daqmx_task(self):
        """Create the DAQmx task, but don't start it yet."""
        self.daqmx_task = pd.Task()
        try:
            self.daqmx_task.CreateAOVoltageChan("/Dev1/ao0:1", "galvo-laser",
                                                -self.config['laser_max_volts'],
                                                self.config['laser_max_volts'], pd.DAQmx_Val_Volts, None)
        except pd.DAQException as e:
            self.logger.error(f"DAQmx error: {e.message}")

    def cleanup_daqmx_task(self):
        """Stop and clear the DAQmx task"""
        self.daqmx_task.StopTask()
        self.daqmx_task.ClearTask()

    def connect_arduino(self, port):
        """"The Arduino switcher is optional, needed here only for periodic biasing of the galvo signal"""
        if self.serial_arduino is None:
            try:
                self.serial_arduino = serial.Serial(port, 9600, timeout=2)
                self.serial_arduino.write("?ver\n".encode())
                status = self.serial_arduino.readline().decode('utf-8')
                self.logger.info(f"Connected to Arduino switcher, version: {status}")
            except serial.SerialException as e:
                self.logger.error(f"Could not connect to Arduino, SerialException: {e}")
                self.serial_arduino.close()
            except Exception as e:
                self.logger.error(f"Could not connect to Arduino, Exception: {e}")

    def setup_arduino_switcher(self, switch_auto=True, galvo_offsets_v = (0, 0), n_TTL_inputs: int):
        """"Send the galvo bias values and N(frames per stack) to the Arduino switcher that flips the galvo bias
        every N input pulses"""
        assert len(galvo_offsets_v) == 2, "Argument galvo_offsets_v must be a 2-long tuple"
        # automatic mode
        if switch_auto:
            if self.serial_arduino:
                self.serial_arduino.write(f'n {n_TTL_inputs}\n'.encode())
                self.serial_arduino.write('reset\n'.encode())
                self.serial_arduino.write(f'v0 {galvo_offsets_v[0]}\n'.encode())
                self.serial_arduino.write(f'v1 {galvo_offsets_v[1]}\n'.encode())
        # no switching, zero bias, fixed arm mode
        else:
            if self.serial_arduino:
                self.serial_arduino.write('n 10000\n'.encode())
                self.serial_arduino.write('v0 0.0\n'.encode())
                self.serial_arduino.write('v1 0.0\n'.encode())
                self.serial_arduino.write('reset\n'.encode())


    def setup_ls(self, galvo_amp_V, galvo_offset_V, ls_duration_ms, laser_on_V):
        """Set up the lightsheet DAQmx task. """
        if self.daqmx_task:
            try:
                task_config(self.daqmx_task, wf_duration_ms=ls_duration_ms,
                               galvo_offset_V=galvo_offset_V, galvo_amplitude_V=galvo_amp_V,
                               laser_amplitude_V=laser_on_V, galvo_inertia_ms=0.2)
            except pd.DAQException as e:
                self.logger.error(f"DAQmx: {e}")
            except Exception as e:
                self.logger.error(f"Non-DAQmx: {e}")
        else:
            self.logger.error("DAQmx task is None")

    def activate_ls(self):
        """Create and start DAQmx stask for TTL-triggered lightsheet"""
        if not self.ls_active:
            self.create_daqmx_task()
            self.setup_lightsheet()
            self.ls_active = True
            self.button_ls_activate.setText("Inactivate light sheet")
            self.button_ls_activate.setStyleSheet('QPushButton {color: blue;}')
        else:
            self.cleanup_daqmx_task()
            self.ls_active = False
            self.button_ls_activate.setText("Activate light sheet")
            self.button_ls_activate.setStyleSheet('QPushButton {color: red;}')

    def detect_serial_ports(self):
        ports = ['COM%s' % (i + 1) for i in range(256)]
        ports_available = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                ports_available.append(port)
            except (OSError, serial.SerialException):
                self.logger.error(f"detect_serial_ports(), Exception: {e}")
        return ports_available

    #Todo GUI with callbacks, Initialize, testing.

def task_config(task, wf_duration_ms=50,
                   galvo_offset_V=0,
                   galvo_amplitude_V=1.0,
                   laser_amplitude_V=0.0,
                   galvo_inertia_ms=0.20):
    """Configuration and automatic restart of light-sheet generation DAQmx AO task.
    Channels:
        ao0, galvo
        ao1, laser
    Parameters:
        task, existing DAQmx AO task
        wf_duration_ms
        galvo_offset_V
        galvo_amplitude_V
        laser_amplitude_V.
        galvo_inertia_ms, delay in laser onset after galvo, to accomodate galvo inertia.
    """
    task.StopTask()
    sampleRate_Hz = 20000
    samples_per_ch = np.int(sampleRate_Hz/1000. * wf_duration_ms)
    task.CfgSampClkTiming("", sampleRate_Hz, pd.DAQmx_Val_Rising, pd.DAQmx_Val_FiniteSamps, samples_per_ch)

    task.CfgDigEdgeStartTrig("/Dev1/PFI0", pd.DAQmx_Val_Rising)
    task.SetTrigAttribute(pd.DAQmx_StartTrig_Retriggerable, True)
    
    # generate galvo AO waveform
    wf_galvo = np.zeros(samples_per_ch)
    wf_sawtooth = np.linspace(-galvo_amplitude_V/2.0, galvo_amplitude_V/2.0, samples_per_ch-2)
    # note that the last value of waveform should be zero or galvo_offset_V constant
    wf_galvo[1:-1] = wf_sawtooth
    wf_galvo = wf_galvo + galvo_offset_V
    # generate laser ON/OFF waveform
    wf_laser = np.zeros(samples_per_ch)
    laser_delay_samples = int(sampleRate_Hz/1000. * galvo_inertia_ms)
    wf_laser[laser_delay_samples:-1] = laser_amplitude_V  # laser wf must end with zero for safety reasons.
    # combine
    wform2D = np.column_stack((wf_galvo,wf_laser))
    # write to buffer
    samples_per_ch_ct = ct.c_int32()
    samples_per_ch_ct.value = samples_per_ch
    task.WriteAnalogF64(samples_per_ch, False, 10, pd.DAQmx_Val_GroupByScanNumber,
                        wform2D, ct.byref(samples_per_ch_ct), None)
    # restart the task
    task.StartTask()
