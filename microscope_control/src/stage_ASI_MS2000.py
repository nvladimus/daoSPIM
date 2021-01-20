"""
ASI XY stage interface for MS-2000 controller.
To launch as a standalone app, run `python stage_ASI_MS2000.py`.
To launch inside another program, see `gui_demo.py`
Copyright Nikita Vladimirov @nvladimus 2020
Todo: add output triggers
"""
import serial
import widget as wd
import logging
import sys
import time
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal

config = {
    'simulation': False,
    'port': "COM18",
    'baud': 9600,
    'timeout_s': 2.0,
    'units_mm': 1e-4,
    'max_speed_mm/s': 7.5,
    'encoder_step_mm': 1.0/45397.6}
logging.basicConfig()


class MotionController(QtCore.QObject):
    """
    All spatial units are mm.
    """
    sig_update_gui = pyqtSignal()

    def __init__(self, dev_name='ASI MS2000', gui_on=True, logger_name='ASI stage'):
        super().__init__()
        self.port = config['port']
        self.baud = config['baud']
        self.timeout_s = config['timeout_s']
        self.units = config['units_mm']
        self.simulation = config['simulation']
        self.encoder_step_mm = config['encoder_step_mm']
        self.speed_x = self.speed_y = config['max_speed_mm/s']
        self.pulse_intervals_x = 0.01
        self.enc_counts_per_pulse = round(self.pulse_intervals_x / self.encoder_step_mm)
        self.scan_limits_xx_yy = [0.0, 0.1, 0.0, 0.0]  # [x_start, x_stop, y_start, y_stop]
        self.n_scan_lines = 2
        self._ser = None
        self.initialized = False
        self.position_x_mm = self.position_y_mm = 0.0
        self.target_pos_x_mm = self.target_pos_y_mm = 0.0
        self.backlash_mm = 0.03 # some stages are configured without anti-BL gear for smooth motion, and need a margin.
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

    def initialize(self, port, baud=9600, timeout_s=2):
        self.port = port
        self.baud = baud
        self.timeout_s = timeout_s
        if not self.simulation:
            try:
                self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout_s)
                self.logger.info(f"Connected to port {self.port}")
                self.get_position()
                self.get_speed()
                self.initialized = True
            except Exception as e:
                self.logger.error(f"Could not initialize stage: {e}")
        else:
            self.logger.debug(f"Simulation: connected to port {self.port}")

    def get_position(self):
        if not self.simulation:
            response = self.write_with_response(b'W X Y')
            if response[:2] == ":A" and len(response) >= 3:
                words = response.split(" ")
                if len(words) >= 3:
                    self.position_x_mm = float(words[1]) * self.units
                    self.position_y_mm = float(words[2]) * self.units
        else:
            self.logger.debug(f"Simulation: get_position().")
        if self.gui_on:
            self.sig_update_gui.emit()

    def get_speed(self):
        if not self.simulation:
            response = self.write_with_response(b"s x? y?")
            if response[:2] == ":A" and len(response) >= 3:
                words = response.split(" ")
                if len(words) >= 3:
                    self.speed_x = float(words[1][2:])
                    self.speed_y = float(words[2][2:])
                    self.logger.info(f'speed: ({self.speed_x}, {self.speed_y})')
        else:
            self.logger.debug(f"Simulation: get_speed().")
        if self.gui_on:
            self.sig_update_gui.emit()

    def write_with_response(self, command, terminator=b'\r'):
        try:
            self._flush()
            self._ser.write(command + terminator)
            response = self._ser.read_until(terminator=b'\r\n').decode('utf-8')
            return response[:-2]
        except Exception as e:
            self.logger.error(f"write_with_response() {e}")
            return None

    def _flush(self):
        if self._ser is not None:
            self._ser.reset_input_buffer()
            self._ser.reset_output_buffer()
        else:
            self.logger.error("_flush(): serial port not initialized")

    def close(self):
        if not self.simulation:
            try:
                self._ser.close()
                self.logger.info("closed")
            except Exception as e:
                self.logger.error(f"Could not disconnect {e}")
        else:
            self.logger.debug("Simulation: disconnect()")

    def _set_port(self, port):
        self.port = port
        self.logger.info(f"Port {self.port}")

    def _set_baud(self, baud):
        self.baud = baud
        self.logger.info(f"Port {int(self.baud)}")

    def set_target_x(self, target_x_mm): self.target_pos_x_mm = target_x_mm

    def set_target_y(self, target_y_mm): self.target_pos_y_mm = target_y_mm

    def set_speed(self, speed_mms, **kwargs):
        if 'axis' in kwargs.keys():
            axis = kwargs['axis']
        else:
            self.logger.error("set_speed(): keyword /'axis/' is missing")
        if axis == 'X':
            self.speed_x = speed_mms
        elif axis == 'Y':
            self.speed_y = speed_mms
        else:
            self.logger.error("set_speed(): argument axis must be /'X/' or /'Y/'")
        if not self.simulation:
            response = self.write_with_response(f"S {axis}={speed_mms}".encode())
            if response[:2] != ":A":
                self.logger.warning(f"set_speed() unexpected response: {response}")
            else:
                self.get_speed()
        else:
            pass
        if self.gui_on:
            self.sig_update_gui.emit()

    def move_abs(self, pos_mm, sleep_s=0.05):
        assert len(pos_mm) == 2, "move_abs(): argument pos_mm should be 2-element array-like"
        command = f'M X={round(pos_mm[0]/self.units)} Y={round(pos_mm[1]/self.units)}'
        self.logger.debug(command)
        _ = self.write_with_response(command.encode())
        response = self.write_with_response(b'/')
        while response[0] != 'N':
            response = self.write_with_response(b'/')
            time.sleep(sleep_s)
        self.logger.debug(f"move complete")
        self.get_position()

    def set_trigger_intervals(self, interval_mm, **kwargs):
        if 'trigger_axis' in kwargs.keys():
            trigger_axis = kwargs['trigger_axis']
            if trigger_axis == 'X':
                self.pulse_intervals_x = interval_mm
                self.enc_counts_per_pulse = round(interval_mm / self.encoder_step_mm)
            else:
                self.logger.error("set_scan_region(): value of /'trigger_axis/' is invalid.")
            if not self.simulation:
                self._setup_scan()
            if self.gui_on:
                self.sig_update_gui.emit()
        else:
            self.logger.error("set_trigger_intervals(): keyword /'trigger_axis/' is misssing.")

    def set_scan_region(self, pos_mm, **kwargs):
        # check which keyword is passed, and switch accordingly
        if 'scan_boundary' in kwargs.keys():
            boundary = kwargs['scan_boundary']
            if boundary == 'x_start':
                self.scan_limits_xx_yy[0] = pos_mm
            elif boundary == 'x_stop':
                self.scan_limits_xx_yy[1] = pos_mm
            elif boundary == 'y_start':
                self.scan_limits_xx_yy[2] = pos_mm
            elif boundary == 'y_stop':
                self.scan_limits_xx_yy[3] = pos_mm
            else:
                self.logger.error("set_scan_region(): value of /'scan_boundary/' is invalid.")
            if not self.simulation:
                self._setup_scan()
            else:
                self.logger.debug("Simulation: set_scan_region().")
            if self.gui_on:
                self.sig_update_gui.emit()
        else:
            self.logger.error("set_scan_region(): keyword /'scan_boundary/' is misssing.")

    def set_n_scan_lines(self, n):
        self.n_scan_lines = n
        if not self.simulation:
            self._setup_scan()
        if self.gui_on:
            self.sig_update_gui.emit()

    def _setup_scan(self):
        """Send the scan parameters to the stage"""
        # set x-limits and trigger interval
        command = f'SCANR X={self.scan_limits_xx_yy[0]:.4f} ' \
                  f'Y={self.scan_limits_xx_yy[1]:.4f} ' \
                  f'Z={self.enc_counts_per_pulse}'
        _ = self.write_with_response(command.encode())
        self.logger.debug(command)
        # set y-limits and the number of lines
        command = f'SCANV X={self.scan_limits_xx_yy[2]:.4f} ' \
                  f'Y={self.scan_limits_xx_yy[3]:.4f} ' \
                  f'Z={self.n_scan_lines}'
        self.logger.debug(command)
        _ = self.write_with_response(command.encode())
        self._set_scan_mode()
        _ = self.write_with_response(b'TTL X=1')

    def _set_scan_mode(self, raster=True):
        """set RASTER (0) or SERPENTINE (1) scan mode"""
        mode = 0 if raster else 1
        _ = self.write_with_response(f'SCAN F={mode}'.encode())
        self.logger.debug(f'scan mode {mode}')

    def start_scan(self):
        """Scan the stage with ENC_INT module.
        Functions set_scan_region() and set_trigger_intervals() must be called before this.
        """
        _ = self.write_with_response(b'SCAN')

    def halt(self):
        response = self.write_with_response(b'\\')
        self.logger.info(f'halt() response: {response}')

    def _setup_gui(self):
        self.gui.add_tabs("Control Tabs", tabs=['Connection', 'Motion', 'Scanning'])
        tab_name = 'Connection'
        # Connection controls
        self.gui.add_checkbox('Simulation', tab_name, self.simulation, enabled=False)
        self.gui.add_button('Initialize', tab_name, lambda: self.initialize(self.port, self.baud, self.timeout_s))
        self.gui.add_string_field('Port', tab_name, value=self.port, func=self._set_port)
        self.gui.add_numeric_field('Baud', tab_name, value=self.baud, func=self._set_baud, vmin=9600, vmax=115200)
        self.gui.add_button('Disconnect', tab_name, func=self.close)
        # Position/speed controls
        tab_name = 'Motion'
        groupbox_name = 'Position'
        self.gui.add_groupbox(label=groupbox_name, parent=tab_name)
        self.gui.add_numeric_field('X pos., mm',  groupbox_name, value=-1, enabled=False, decimals=5)
        self.gui.add_numeric_field('Y pos., mm', groupbox_name,  value=-1, enabled=False, decimals=5)
        self.gui.add_button('Update position', groupbox_name, func=self.get_position)
        # Absolute move
        self.gui.add_numeric_field('Target X, mm', groupbox_name,
                                   value=0, vmin=-25., vmax=25., decimals=5, func=self.set_target_x)
        self.gui.add_numeric_field('Target Y, mm', groupbox_name,
                                   value=0, vmin=-25., vmax=25., decimals=5, func=self.set_target_y)
        self.gui.add_button('Move to target', groupbox_name,
                            lambda: self.move_abs((self.target_pos_x_mm, self.target_pos_y_mm)))
        self.gui.add_button('STOP', groupbox_name, func=self.halt)

        tab_name = 'Motion'
        groupbox_name = 'Speed'
        self.gui.add_groupbox(label=groupbox_name, parent=tab_name)
        self.gui.add_numeric_field('Speed X, mm/s', groupbox_name,
                                   value=self.speed_x, vmin=0, vmax=7.5, decimals=5,
                                   func=self.set_speed, **{'axis': 'X'})
        self.gui.add_numeric_field('Speed Y, mm/s', groupbox_name,
                                   value=self.speed_y, vmin=0, vmax=7.5, decimals=5,
                                   func=self.set_speed, **{'axis': 'Y'})

        tab_name = 'Scanning'
        self.gui.add_combobox("Scan mode", tab_name, ['Raster', 'Serpentine'], value='Raster',
                              func=lambda x: self._set_scan_mode(x == 'Raster'))
        groupbox_name = 'Scan region'
        self.gui.add_groupbox(label=groupbox_name, parent=tab_name)
        self.gui.add_numeric_field('X start, mm', groupbox_name,
                                   value=self.scan_limits_xx_yy[0], vmin=-25, vmax=25, decimals=4,
                                   func=self.set_scan_region, **{'scan_boundary': 'x_start'})
        self.gui.add_numeric_field('X stop, mm', groupbox_name,
                                   value=self.scan_limits_xx_yy[1], vmin=-25, vmax=25, decimals=4,
                                   func=self.set_scan_region, **{'scan_boundary': 'x_stop'})
        self.gui.add_numeric_field('Y start, mm', groupbox_name,
                                   value=self.scan_limits_xx_yy[2], vmin=-25, vmax=25, decimals=4,
                                   func=self.set_scan_region, **{'scan_boundary': 'y_start'})
        self.gui.add_numeric_field('Y stop, mm', groupbox_name,
                                   value=self.scan_limits_xx_yy[3], vmin=-25, vmax=25, decimals=4,
                                   func=self.set_scan_region, **{'scan_boundary': 'y_stop'})
        self.gui.add_numeric_field('Trigger interval X, mm', groupbox_name,
                                   value=self.pulse_intervals_x, vmin=0, vmax=25, decimals=5,
                                   func=self.set_trigger_intervals, **{'trigger_axis': 'X'})
        self.gui.add_numeric_field('Num. of lines', groupbox_name,
                                   value=self.n_scan_lines, vmin=0, vmax=10000, decimals=0,
                                   func=self.set_n_scan_lines)
        self.gui.add_numeric_field('Backlash margin, mm', tab_name,
                                   value=self.backlash_mm, vmin=0, vmax=0.05, decimals=3, enabled=False)
        self.gui.add_button('Start scanning', tab_name, func=self.start_scan)

    @QtCore.pyqtSlot()
    def _update_gui(self):
        self.gui.update_numeric_field('X pos., mm', self.position_x_mm)
        self.gui.update_numeric_field('Y pos., mm', self.position_y_mm)
        self.gui.update_numeric_field('Speed X, mm/s', self.speed_x)
        self.gui.update_numeric_field('Speed Y, mm/s', self.speed_y)
        self.gui.update_numeric_field('X start, mm', self.scan_limits_xx_yy[0])
        self.gui.update_numeric_field('X stop, mm', self.scan_limits_xx_yy[1])
        self.gui.update_numeric_field('Y start, mm', self.scan_limits_xx_yy[2])
        self.gui.update_numeric_field('Y stop, mm', self.scan_limits_xx_yy[3])
        self.gui.update_numeric_field('Trigger interval X, mm', self.pulse_intervals_x)


# run if the module is launched as a standalone program
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dev = MotionController()
    dev.gui.show()
    app.exec_()
