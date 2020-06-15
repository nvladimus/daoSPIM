'''This is class for generating triggered AO waveforms.
The AO task listens to the input TTL pulse (eg from camera) and generates
short finite AO waveform to synchronously move galvo and turn on the laser.
Copyright @nvladimus, 2020
'''

from PyQt5 import QtCore
import numpy as np
import PyDAQmx as pd
import ctypes as ct
import widget as wd
import serial

config = {
    'swipe_duration_ms': 1.0,
    'galvo_offsets_volts': (-0.32, 0.45),
    'galvo_amp_volts': (0.60, 0.60),
    'laser_max_volts': 1.0,
    'laser_set_volts': 1.0,
    'arduino_switcher_port': 'COM6', # set None is no arduino board is used.
    'switch_auto': True
}


class LightsheetGenerator(QtCore.QObject):
    sig_update_gui = QtCore.pyqtSignal()

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

    def initialize(self):
        if self.config['arduino_switcher_port']:
            self.connect_arduino(self.config['arduino_switcher_port'])
            self.setup_arduino()
        self.create_daqmx_task()
        self.setup_ls()

    def close(self):
        if self.serial_arduino:
            try:
                self.serial_arduino.close()
            except serial.SerialException as e:
                self.logger.error(f"Could not close Arduino connection: {e}")
        if self.daqmx_task:
            self.cleanup_daqmx_task()

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
        try:
            self.daqmx_task.StopTask()
            self.daqmx_task.ClearTask()
        except pd.DAQException as e:
            self.logger.error(f"DAQmx error: {e.message}")

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

    def setup_arduino(self, n_TTL_inputs=10000):
        """"Send the galvo bias values and N(frames per stack) to the Arduino switcher that flips the galvo bias
        every N input pulses"""
        # automatic mode
        if self.config['switch_auto']:
            if self.serial_arduino:
                galvo_offsets = self.config['galvo_offsets_volts']
                self.serial_arduino.write(f'n {n_TTL_inputs}\n'.encode())
                self.serial_arduino.write('reset\n'.encode())
                self.serial_arduino.write(f'v0 {galvo_offsets[0]}\n'.encode())
                self.serial_arduino.write(f'v1 {galvo_offsets[1]}\n'.encode())
        # no switching, zero bias, fixed arm mode
        else:
            if self.serial_arduino:
                self.serial_arduino.write('n 10000\n'.encode())
                self.serial_arduino.write('v0 0.0\n'.encode())
                self.serial_arduino.write('v1 0.0\n'.encode())
                self.serial_arduino.write('reset\n'.encode())

    def setup_ls(self):
        """Set up the lightsheet DAQmx task. """
        assert self.config['laser_set_volts'] <= self.config['laser_max_volts'], 'Laser voltage too high'
        if self.daqmx_task:
            try:
                task_config(wf_duration_ms=self.config['swipe_duration_ms'],
                            galvo_offset_V=self.config['galvo_offset_volts'][0],
                            galvo_amplitude_V=self.config['galvo_amp_volts'][0],
                            laser_amplitude_V=self.config['laser_set_volts'],
                            galvo_inertia_ms=0.2)
            except pd.DAQException as e:
                self.logger.error(f"DAQmx: {e}")
        else:
            self.logger.error("DAQmx task is None")

    def task_config(self, wf_duration_ms=50, galvo_offset_V=0, galvo_amplitude_V=1.0, laser_amplitude_V=0.0,
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
        sampleRate_Hz = 20000
        samples_per_ch = np.int(sampleRate_Hz / 1000. * wf_duration_ms)
        self.daqmx_task.StopTask()
        self.daqmx_task.CfgSampClkTiming("", sampleRate_Hz, pd.DAQmx_Val_Rising, pd.DAQmx_Val_FiniteSamps, samples_per_ch)

        self.daqmx_task.CfgDigEdgeStartTrig("/Dev1/PFI0", pd.DAQmx_Val_Rising)
        self.daqmx_task.SetTrigAttribute(pd.DAQmx_StartTrig_Retriggerable, True)
        # generate galvo AO waveform
        wf_galvo = np.zeros(samples_per_ch)
        wf_sawtooth = np.linspace(-galvo_amplitude_V / 2.0, galvo_amplitude_V / 2.0, samples_per_ch - 2)
        # note that the last value of waveform should be zero or galvo_offset_V constant
        wf_galvo[1:-1] = wf_sawtooth
        wf_galvo = wf_galvo + galvo_offset_V
        # generate laser ON/OFF waveform
        wf_laser = np.zeros(samples_per_ch)
        laser_delay_samples = int(sampleRate_Hz / 1000. * galvo_inertia_ms)
        wf_laser[laser_delay_samples:-1] = laser_amplitude_V  # laser wf must end with zero for safety reasons.
        # combine
        wform2D = np.column_stack((wf_galvo, wf_laser))
        # write to buffer
        samples_per_ch_ct = ct.c_int32()
        samples_per_ch_ct.value = samples_per_ch
        self.daqmx_task.WriteAnalogF64(samples_per_ch, False, 10, pd.DAQmx_Val_GroupByScanNumber,
                            wform2D, ct.byref(samples_per_ch_ct), None)
        # restart the task
        self.daqmx_task.StartTask()

    def update_config(self, **kwargs):
        for k, v in zip(kwargs.keys(), kwargs.values()):
            self.config[k] = v
        self.setup_arduino()
        self.setup_ls()

    #Todo GUI with callbacks, testing.
    def _setup_gui(self):
        self.gui.add_tabs("Control Tabs", tabs=['LS settings', 'DAQ settings'])
        tab_name = 'LS settings'
        self.gui.add_button('Initialize', tab_name, lambda: self.initialize())
        self.gui.add_numeric_field('Swipe duration', tab_name, value=self.config['swipe_duration_ms'],
                                   vmin=0.1, vmax=100, enabled=True, decimals=1,
                                   func=self.update_config, **{'swipe_duration_ms'}
                                   )
        self.gui.add_button('Disconnect', tab_name, lambda: self.close())


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
