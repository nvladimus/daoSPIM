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

config = {'port': "COM18",
          'baud': 9600,
          'timeout_s': 2,
          'units_mm': 1e-4,
          'max_speed_mm/s': 7.5,
          'encoder_step_mm': 1.0/45396}
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
        self.encoder_step_mm = config['encoder_step_mm']
        self.speed_x = self.speed_y = config['max_speed_mm/s']
        self.pulse_intervals_xy = [0.01, 0.01]
        self.enc_counts_per_pulse_xy = [round(self.pulse_intervals_xy[0] / self.encoder_step_mm),
                                        round(self.pulse_intervals_xy[1] / self.encoder_step_mm)]
        self.scan_limits_xx_yy = [0, 0.1, 0, 0.1]  # [x_start, x_stop, y_start, y_stop]
        self._ser = None
        self.position_x_mm = self.position_y_mm = None
        self.target_pos_x_mm = self.target_pos_y_mm = 0
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
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout_s)
            self.logger.info(f"Connected to port {self.port}")
            self.get_position()
            self.get_speed()
        except Exception as e:
            self.logger.error(f"Could not initialize stage: {e}")

    def get_position(self):
        response = self.write_with_response(b'W X Y')
        if response[:2] == ":A" and len(response) >= 3:
            words = response.split(" ")
            if len(words) >= 3:
                self.position_x_mm = float(words[1]) * self.units
                self.position_y_mm = float(words[2]) * self.units
        if self.gui_on:
            self.sig_update_gui.emit()

    def get_speed(self):
        response = self.write_with_response(b"s x? y?")
        if response[:2] == ":A" and len(response) >= 3:
            words = response.split(" ")
            if len(words) >= 3:
                self.speed_x = float(words[1][2:])
                self.speed_y = float(words[2][2:])
                self.logger.info(f'speed: ({self.speed_x}, {self.speed_y})')
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

    def disconnect(self):
        try:
            self._ser.close()
            self.logger.info("closed")
        except Exception as e:
            self.logger.error(f"Could not disconnect {e}")

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
        response = self.write_with_response(f"S {axis}={speed_mms}".encode())
        if response[:2] != ":A":
            self.logger.warning(f"set_speed() unexpected response: {response}")
        else:
            self.get_speed()

    def move_abs(self, pos_mm, sleep_s=0.05):
        assert len(pos_mm) == 2, "move_abs(): argument pos_mm should be 2-element array-like"
        command = f'M X={pos_mm[0]/self.units} Y={pos_mm[1]/self.units}'.encode()
        _ = self.write_with_response(command)
        response = self.write_with_response(b'/')
        while response[0] != 'N':
            response = self.write_with_response(b'/')
            time.sleep(sleep_s)
        self.logger.info(f"move complete")
        self.get_position()

    def set_trigger_intervals(self, interval_mm, **kwargs):
        if 'trigger_axis' in kwargs.keys():
            trigger_axis = kwargs['trigger_axis']
            if trigger_axis == 'X':
                self.pulse_intervals_xy[0] = interval_mm
                self.enc_counts_per_pulse_xy[0] = round(interval_mm / self.encoder_step_mm)
            elif trigger_axis == 'Y':
                self.pulse_intervals_xy[1] = interval_mm
                self.enc_counts_per_pulse_xy[1] = round(interval_mm / self.encoder_step_mm)
            else:
                self.logger.error("set_scan_region(): value of /'trigger_axis/' is invalid.")
            self._setup_scan()
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
            self._setup_scan()
        else:
            self.logger.error("set_scan_region(): keyword /'scan_boundary/' is misssing.")

    def _setup_scan(self):
        """Send the scan parameters to the stage"""
        # set x-limits
        command = f'SCANR X={self.scan_limits_xx_yy[0]} ' \
                  f'Y={self.scan_limits_xx_yy[1]} ' \
                  f'Z={self.enc_counts_per_pulse_xy[0]}'
        _ = self.write_with_response(command.encode())
        # set y-limits
        command = f'SCANV X={self.scan_limits_xx_yy[2]} ' \
                  f'Y={self.scan_limits_xx_yy[3]} ' \
                  f'Z={self.enc_counts_per_pulse_xy[1]}'
        _ = self.write_with_response(command.encode())
        # set RASTER (0) or SERPENTINE (1) scan mode:
        _ = self.write_with_response(b'SCAN F=1')
        _ = self.write_with_response(b'TTL X=1')

    def start_scan(self):
        """Scan the stage with ENC_INT module.
        Functions set_scan_region() and set_trigger_intervals() must be called before it
        """
        self.logger.info(f'scan limits: {self.scan_limits_xx_yy}')
        self.logger.info(f'enc counts per pulse: {self.enc_counts_per_pulse_xy}')
        response = self.write_with_response(b'SCAN')

    def halt(self):
        response = self.write_with_response(b'\\')
        self.logger.info(f'halt() response: {response}')

    def _setup_gui(self):
        self.gui.add_tabs("Control Tabs", tabs=['Connection', 'Motion', 'Scanning'])
        tab_name = 'Connection'
        # Connection controls
        self.gui.add_string_field('Port', tab_name, value=self.port, func=self._set_port)
        self.gui.add_numeric_field('Baud', tab_name, value=self.baud, func=self._set_baud,
                                   vmin=9600, vmax=115200, enabled=True, decimals=0)
        self.gui.add_button('Connect', tab_name,
                            lambda: self.initialize(self.port, self.baud, self.timeout_s))
        self.gui.add_button('Disconnect', tab_name,
                            lambda: self.disconnect())
        # Position/speed controls
        tab_name = 'Motion'
        groupbox_name = 'Position'
        self.gui.add_groupbox(title=groupbox_name, parent=tab_name)
        self.gui.add_numeric_field('X pos., mm',  groupbox_name,
                                   value=-1, vmin=-1e6, vmax=1e6, enabled=False, decimals=5)
        self.gui.add_numeric_field('Y pos., mm', groupbox_name,
                                   value=-1, vmin=-1e6, vmax=1e6, enabled=False, decimals=5)
        self.gui.add_button('Update position', groupbox_name,
                            lambda: self.get_position())
        # Absolute move
        self.gui.add_numeric_field('Target X, mm', groupbox_name,
                                   value=0, vmin=-25., vmax=25., decimals=5,
                                   enabled=True, func=self.set_target_x)
        self.gui.add_numeric_field('Target Y, mm', groupbox_name,
                                   value=0, vmin=-25., vmax=25., decimals=5,
                                   enabled=True, func=self.set_target_y)
        self.gui.add_button('Move to target', groupbox_name,
                            lambda: self.move_abs((self.target_pos_x_mm, self.target_pos_y_mm)))
        self.gui.add_button('STOP', groupbox_name,
                            lambda: self.halt())

        tab_name = 'Motion'
        groupbox_name = 'Speed'
        self.gui.add_groupbox(title=groupbox_name, parent=tab_name)
        self.gui.add_numeric_field('Speed X, mm/s', groupbox_name,
                                   value=self.speed_x, vmin=0, vmax=7.5, decimals=5,
                                   enabled=True, func=self.set_speed, **{'axis': 'X'})
        self.gui.add_numeric_field('Speed Y, mm/s', groupbox_name,
                                   value=self.speed_y, vmin=0, vmax=7.5, decimals=5,
                                   enabled=True, func=self.set_speed, **{'axis': 'Y'})

        tab_name = 'Scanning'
        groupbox_name = 'Scan region'
        self.gui.add_groupbox(title=groupbox_name, parent=tab_name)
        self.gui.add_numeric_field('X start, mm', groupbox_name,
                                   value=self.scan_limits_xx_yy[0], vmin=-25, vmax=25, decimals=4,
                                   enabled=True, func=self.set_scan_region, **{'scan_boundary': 'x_start'})
        self.gui.add_numeric_field('X stop, mm', groupbox_name,
                                   value=self.scan_limits_xx_yy[1], vmin=-25, vmax=25, decimals=4,
                                   enabled=True, func=self.set_scan_region, **{'scan_boundary': 'x_stop'})
        self.gui.add_numeric_field('Y start, mm', groupbox_name,
                                   value=self.scan_limits_xx_yy[2], vmin=-25, vmax=25, decimals=4,
                                   enabled=True, func=self.set_scan_region, **{'scan_boundary': 'y_start'})
        self.gui.add_numeric_field('Y stop, mm', groupbox_name,
                                   value=self.scan_limits_xx_yy[3], vmin=-25, vmax=25, decimals=4,
                                   enabled=True, func=self.set_scan_region, **{'scan_boundary': 'y_stop'})
        self.gui.add_numeric_field('Trigger interval X, mm', groupbox_name,
                                   value=self.pulse_intervals_xy[0], vmin=0, vmax=25, decimals=4,
                                   enabled=True, func=self.set_trigger_intervals, **{'trigger_axis': 'X'})
        self.gui.add_numeric_field('Trigger interval Y, mm', groupbox_name,
                                   value=self.pulse_intervals_xy[1], vmin=0, vmax=25, decimals=4,
                                   enabled=True, func=self.set_trigger_intervals, **{'trigger_axis': 'Y'})
        self.gui.add_button('Start scanning', groupbox_name,
                            lambda: self.start_scan())

    @QtCore.pyqtSlot()
    def _update_gui(self):
        self.gui.update_numeric_field('X pos., mm', self.position_x_mm)
        self.gui.update_numeric_field('Y pos., mm', self.position_y_mm)
        self.gui.update_numeric_field('Speed X, mm/s', self.speed_x)
        self.gui.update_numeric_field('Speed Y, mm/s', self.speed_y)


# run if the module is launched as a standalone program
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dev = MotionController()
    dev.gui.show()
    app.exec_()
