'''This is class for generating triggered AO waveforms.
The AO task listens to the input TTL pulse (eg from camera) and generates
short finite AO waveform to synchronously move galvo and turn on the laser.
Copyright @nvladimus, 2020
'''

from PyQt5 import QtCore, QtWidgets
import sys
import logging
import numpy as np
import PyDAQmx as pd
import ctypes as ct
import widget as wd
import serial
from functools import partial

config = {
    'swipe_duration_ms': 1.0,
    'L-galvo_offsets_volts': -0.40,
    'R-galvo_offsets_volts': 0.35,
    'L-galvo_amp_volts': 0.70,
    'R-galvo_amp_volts': 0.70,
    'laser_max_volts': 1.0, #Check your laser modulation voltage!!! Laser can be damaged by high voltage.
    'laser_pow_volts': 0.6,
    'arduino_switcher_port': 'COM6', # set None is no arduino board is used.
    'active_arm': 'left',
    'switch_auto': True,
    'switch_every_n_pulses': 100,
    'DAQ_trig_in_ch': '/Dev1/PFI0',
    'DAQ_AO_ch': '/Dev1/ao0:1',
    'DAQ_sample_rate_Hz': 20000
}

logging.basicConfig()


class LightsheetGenerator(QtCore.QObject):
    sig_update_gui = QtCore.pyqtSignal()

    def __init__(self, dev_name='LS generator', gui_on=True, logger_name='Lightsheet'):
        super().__init__()
        self.config = config
        self.daqmx_task = self.serial_arduino = None
        self.initialized = False
        self.status = "OFF"
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
                self.serial_arduino = None
                self.logger.info('Arduino connection closed')
            except serial.SerialException as e:
                self.logger.error(f"Could not close Arduino connection: {e}")
        if self.daqmx_task:
            self.cleanup_daqmx_task()
            self.logger.info('DAQmx task closed.')
            self.status = "OFF"
            self.initialized = False
            if self.gui_on: self.sig_update_gui.emit()

    def create_daqmx_task(self):
        """Create the DAQmx task, but don't start it yet."""
        self.daqmx_task = pd.Task()
        try:
            max_volts = 5.0
            self.daqmx_task.CreateAOVoltageChan(self.config['DAQ_AO_ch'], "galvo-laser",
                                                -max_volts, max_volts, pd.DAQmx_Val_Volts, None)
            self.logger.info('DAQmx AO task created.')
        except pd.DAQException as e:
            self.logger.error(f"Create DAQmx task error: {e.message}")

    def cleanup_daqmx_task(self):
        """Stop and clear the DAQmx task"""
        if self.daqmx_task:
            try:
                self.daqmx_task.StopTask()
                self.daqmx_task.ClearTask()
                self.daqmx_task = None
            except pd.DAQException as e:
                self.logger.error(f"Cleanup DAQmx error: {e.message}")
        else:
            self.logger.error("DAQmx task is None")

    def connect_arduino(self, port):
        """"The Arduino switcher is optional, needed here only for periodic biasing of the galvo signal"""
        if self.serial_arduino is None:
            try:
                self.serial_arduino = serial.Serial(port, 9600, timeout=2)
                self.serial_arduino.write("?ver\n".encode())
                status = self.serial_arduino.readline().decode('utf-8')
                self.logger.info(f"Connected to Arduino switcher, v. {status}")
            except serial.SerialException as e:
                self.logger.error(f"Could not connect to Arduino, SerialException: {e}")

    def setup_arduino(self):
        """"Send the galvo bias values and N(frames per stack) to the Arduino switcher that flips the galvo bias
        every N input pulses"""
        # automatic switching mode
        if self.config['switch_auto']:
            if self.serial_arduino:
                n_TTL_inputs = int(self.config['switch_every_n_pulses'])
                galvo_offsets = self.config['L-galvo_offsets_volts'], self.config['R-galvo_offsets_volts']
                self.serial_arduino.write(f'n {n_TTL_inputs}\n'.encode())
                self.serial_arduino.write(f'v0 {galvo_offsets[0]}\n'.encode())
                self.serial_arduino.write(f'v1 {galvo_offsets[1]}\n'.encode())
                self.serial_arduino.write('reset\n'.encode())
        # no switching, zero bias, fixed arm mode
        else:
            if self.serial_arduino:
                self.serial_arduino.write('n 10000\n'.encode())
                self.serial_arduino.write('v0 0.0\n'.encode())
                self.serial_arduino.write('v1 0.0\n'.encode())
                self.serial_arduino.write('reset\n'.encode())

    def set_switching_period(self, n: int):
        self.config['switch_every_n_pulses'] = n
        self.setup_arduino()
        if self.gui_on: self.sig_update_gui.emit()

    def setup_ls(self):
        """Set up the lightsheet DAQmx task. """
        assert self.config['laser_pow_volts'] <= self.config['laser_max_volts'], 'Laser voltage too high'
        if self.daqmx_task:
            try:
                if self.config['active_arm'] == 'left':
                    offset, amp = self.config['L-galvo_offsets_volts'], self.config['L-galvo_amp_volts']
                else:
                    offset, amp = self.config['R-galvo_offsets_volts'], self.config['R-galvo_amp_volts']
                self.task_config(wf_duration_ms=self.config['swipe_duration_ms'],
                                 galvo_offset_V=offset * (not self.config['switch_auto']),
                                 galvo_amplitude_V=amp,
                                 laser_amplitude_V=self.config['laser_pow_volts'],
                                 galvo_inertia_ms=0.2)
                self.logger.info('DAQmx AO task configured.')
                self.status = "ON"
                if self.gui_on: self.sig_update_gui.emit()
                self.initialized = True
            except pd.DAQException as e:
                self.logger.error(f"Config DAQmx: {e.message}")
        else:
            self.logger.error("DAQmx task is None")

    def task_config(self, wf_duration_ms, galvo_offset_V, galvo_amplitude_V, laser_amplitude_V,
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
        samples_per_ch = np.int(self.config['DAQ_sample_rate_Hz'] / 1000. * wf_duration_ms)
        self.daqmx_task.StopTask()
        self.daqmx_task.CfgSampClkTiming("", self.config['DAQ_sample_rate_Hz'],
                                         pd.DAQmx_Val_Rising, pd.DAQmx_Val_FiniteSamps, samples_per_ch)

        self.daqmx_task.CfgDigEdgeStartTrig(self.config['DAQ_trig_in_ch'], pd.DAQmx_Val_Rising)
        self.daqmx_task.SetTrigAttribute(pd.DAQmx_StartTrig_Retriggerable, True)
        # generate galvo AO waveform
        wf_galvo = np.zeros(samples_per_ch)
        wf_sawtooth = np.linspace(-galvo_amplitude_V / 2.0, galvo_amplitude_V / 2.0, samples_per_ch - 2)
        # note that the last value of waveform should be zero or galvo_offset_V constant
        wf_galvo[1:-1] = wf_sawtooth
        wf_galvo = wf_galvo + galvo_offset_V
        # generate laser ON/OFF waveform
        wf_laser = np.zeros(samples_per_ch)
        laser_delay_samples = int(self.config['DAQ_sample_rate_Hz'] / 1000. * galvo_inertia_ms)
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

    def update_config(self, key, value):
        if key in self.config.keys():
            self.config[key] = value
            self.logger.debug(f'{key}: {value}')
        else:
            self.logger.error("Parameter name not found in config file")
        self.setup()
        if self.gui_on:
            self.sig_update_gui.emit()

    def setup(self):
        self.setup_arduino()
        self.setup_ls()

    def _setup_gui(self):
        self.gui.add_tabs("Control Tabs", tabs=['LS settings', 'DAQ settings'])
        tab_name = 'LS settings'
        self.gui.add_button('Initialize', tab_name, func=self.initialize)
        self.gui.add_string_field('Port', tab_name, value=self.config['arduino_switcher_port'], enabled=False)
        self.gui.add_string_field('Status', tab_name, value=self.status, enabled=False)
        self.gui.add_numeric_field('Swipe duration', tab_name, value=self.config['swipe_duration_ms'],
                                   vmin=0.1, vmax=100, decimals=1,
                                   func=partial(self.update_config, 'swipe_duration_ms'))
        self.gui.add_numeric_field('L-arm galvo offset', tab_name, value=self.config['L-galvo_offsets_volts'],
                                   vmin=-10, vmax=10, decimals=2,
                                   func=partial(self.update_config, 'L-galvo_offsets_volts'))
        self.gui.add_numeric_field('R-arm galvo offset', tab_name, value=self.config['R-galvo_offsets_volts'],
                                   vmin=-10, vmax=10,  decimals=2,
                                   func=partial(self.update_config, 'R-galvo_offsets_volts'))
        self.gui.add_numeric_field('L-galvo amp (V)', tab_name, value=self.config['L-galvo_amp_volts'],
                                   vmin=-1., vmax=1.,  decimals=2,
                                   func=partial(self.update_config, 'L-galvo_amp_volts'))
        self.gui.add_numeric_field('R-galvo amp (V)', tab_name, value=self.config['R-galvo_amp_volts'],
                                   vmin=-1., vmax=1., decimals=2,
                                   func=partial(self.update_config, 'R-galvo_amp_volts'))
        self.gui.add_numeric_field('Laser power (V)', tab_name, value=self.config['laser_pow_volts'],
                                   vmin=0, vmax=self.config['laser_max_volts'], decimals=2,
                                   func=partial(self.update_config, 'laser_pow_volts'))
        self.gui.add_combobox('Active arm', tab_name, ['left', 'right'], value=self.config['active_arm'],
                              func=partial(self.update_config, 'active_arm'))
        self.gui.add_numeric_field('Switch every N pulses', tab_name, value=self.config['switch_every_n_pulses'],
                                   vmin=0, vmax=10000, decimals=0,
                                   func=partial(self.update_config, 'switch_every_n_pulses'))
        self.gui.add_checkbox('Auto-switching', tab_name,  value=self.config['switch_auto'],
                              func=partial(self.update_config, 'switch_auto'))
        self.gui.add_button('Disconnect', tab_name, lambda: self.close())

        tab_name = 'DAQ settings'
        self.gui.add_string_field('Trigger-in channel', tab_name,
                                  value=self.config['DAQ_trig_in_ch'], enabled=False)
        self.gui.add_string_field('AO channels (galvo, laser)', tab_name,
                                  value=self.config['DAQ_AO_ch'], enabled=False)
        self.gui.add_numeric_field('Sample rate, Hz', tab_name, value=self.config['DAQ_sample_rate_Hz'], enabled=False)

    @QtCore.pyqtSlot()
    def _update_gui(self):
        self.gui.update_param('Active arm', self.config['active_arm'])
        self.gui.update_param('Switch every N pulses', self.config['switch_every_n_pulses'])
        self.gui.update_param('Status', self.status)


# run if the module is launched as a standalone program
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dev = LightsheetGenerator()
    dev.gui.show()
    app.exec_()
