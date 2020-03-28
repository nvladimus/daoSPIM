"""
Todo: test on hardware. This version is not tested yet!
Module for controlling deformable mirror Mirao 52e (Imaging Optics)
License GPL-3.0
by @nvladimus, 2020
"""

import ctypes
import widget as wd
import logging
import sys
import os
import numpy as np
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal

config = {'dll_path': "./deformable_mirror/mirao52e.dll",
          'flat_file': './deformable_mirror/flat.mro'}
logging.basicConfig()


class DmController(QtCore.QObject):
    """
    Mirao52e control.
    Communication protocol: serial, via native DLL wrapping.
    """
    sig_update_gui = pyqtSignal()

    def __init__(self, dev_name='Mirao52e', gui_on=True, logger_name='Mirao'):
        super().__init__()
        self.errors = {}
        self.initialize_err_codes(self.errors)
        self.dll_path = config['dll_path']
        self.flat_file = config['flat_file']
        self.cmd_flat = None
        self.dev_handle = None
        self.n_actuators = 52
        self.diameter_mm = 15.0
        self.command = np.zeros(self.n_actuators)
        self._status = ctypes.c_int64()  # possibly c_int32() in some versions, Todo: test
        self._trigger = ctypes.c_int64()
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        self.check_files()
        # GUI setup
        self.gui_on = gui_on
        if self.gui_on:
            self.logger.info("GUI activated")
            self.gui = wd.widget(dev_name)
            self._setup_gui()
            self.sig_update_gui.connect(self._update_gui)

    def check_files(self):
        if not os.path.exists(self.dll_path):
            self.logger.error(f"DLL file does not exist at {self.dll_path}.")
        else:
            try:
                self.dev_handle = ctypes.windll.LoadLibrary(self.dll_path)
            except Exception as e:
                self.logger.error(f"Could not load DLL file from {self.dll_path}: {e}")
            if os.path.exists(self.flat_file):
                self.cmd_flat = self.read_mro_file(self.flat_file)
            else:
                self.logger.error(f"Flat-command file does not exist at {self.dll_path}.")

    def initialize(self):
        """Open deformable mirror session"""
        if self.dev_handle is not None:
            try:
                self.dev_handle.mro_open(ctypes.byref(self._status))
            except:
                pass
            self.update_log(self._status.value)
            if self.gui_on:
                self.sig_update_gui.emit()
        else:
            self.logger.error("DM device handle is empty, check DLL path.")

    def apply_flat(self):
        """Apply factory-supplied flat command from .mro file"""
        if self.dev_handle is not None:
            self.cmd_flat = self.read_mro_file(self.flat_file)
            try:
                self.dev_handle.mro_applySmoothCommand(self.cmd_flat.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                                       self._trigger, ctypes.byref(self._status))
            except:
                pass
            self.update_log(self._status.value)
            if self.gui_on:
                self.sig_update_gui.emit()
        else:
            self.logger.error("DM is not initialized")

    def apply_cmd(self, command: np.ndarray):
        """Apply command (numpy array)"""
        if command.shape[0] != self.n_actuators:
            self.logger.error("Command dimensions are incorrect")
        elif self.dev_handle is None:
            self.logger.error("DM is not initialized")
        else:
            try:
                self.dev_handle.mro_applySmoothCommand(command.ctypes.data_as(ctypes.POINTER(ctypes.c_float)),
                                                       self._trigger, ctypes.byref(self._status))
            except:
                pass
            self.update_log(self._status.value)
            if self.gui_on:
                self.sig_update_gui.emit()

    def read_npy_file(self, filepath=''):
        """Read command from .npy file and apply immediately.
        If self.gui_on, open a file dialog. Otherwise, take filepath from arguments.
        """
        if self.gui_on:
            filepath, _filter = QtWidgets.QFileDialog.getOpenFileName(self.gui, "Open .npy file", "./",
                                                                      "Numpy files (*.npy)")
        try:
            self.command = np.load(filepath)
            self.apply_cmd(self.command)
        except Exception as e:
            self.logger.error(f'Numpy file {filepath} failed to open.')

    def read_mro_file(self, filepath: str) -> np.ndarray:
        if self.dev_handle is not None:
            cpath = ctypes.c_char_p(filepath.encode('utf-8'))
            cmdType = ctypes.c_double * self.n_actuators
            cmd = cmdType()
            self.dev_handle.mro_readCommandFile.argtypes = [ctypes.c_char_p, cmdType, ctypes.POINTER(ctypes.c_int64)]
            if os.path.exists(filepath) and filepath[-4:] == '.mro':
                try:
                    self.dev_handle.mro_readCommandFile(cpath, cmd, ctypes.byref(self._status))
                except:
                    pass
                self.update_log(self._status.value)
            else:
                self.logger.error(f'MRO file {filepath} not found, or has invalid extension (must be .mro).')
        else:
            self.logger.error(f'DM handle is None, device is not initialized.')
            cmd = [0]*self.n_actuators
        return np.asarray(cmd)

    def update_log(self, return_status: int):
        if return_status == 0:
            self.logger.debug(self.errors[return_status])
        else:
            self.logger.error(self.errors[return_status])

    def disconnect(self):
        """Close deformable mirror session"""
        if self.dev_handle is None:
            self.logger.error(f'DM was not initialized, cannot close.')
        else:
            try:
                self.dev_handle.mro_close(ctypes.byref(self._status))
            except:
                pass
            self.update_log(self._status.value)
            if self.gui_on:
                self.sig_update_gui.emit()

    def initialize_err_codes(self, errors):
        """Populate the errors dictionary with meaningful messages"""
        errors[0] = 'MRO_OK, No error'
        errors[1] = 'MRO_UNKNOWN_ERROR'
        errors[2] = 'MRO_DEVICE_NOT_OPENED_ERROR, mirao 52-e is not opened.'
        errors[3] = 'MRO_DEFECTIVE_DEVICE_ERROR, mirao 52-e has been identified as defective.'
        errors[4] = 'MRO_DEVICE_ALREADY_OPENED_ERROR, mirao 52-e is already opened.'
        errors[5] = 'MRO_DEVICE_IO_ERROR, a communication error has been detected.'
        errors[6] = 'MRO_DEVICE_LOCKED_ERROR, a temperature overheat or an excess of current has lead mirao 52-e to a protection state.'
        errors[7] = 'MRO_DEVICE_DISCONNECTED_ERROR'
        errors[8] = 'MRO_DEVICE_DRIVER_ERROR, an internal driver malfunction'
        errors[9] = 'MRO_FILE_EXISTS_ERROR, the file to write already exists and its not allowed to overwrite it.'
        errors[10] = 'MRO_FILE_FORMAT_ERROR, the considered file is corrupted or has not a valid file format.'
        errors[11] = 'MRO_FILE_IO_ERROR, an error has been detected while reading/writing a file.'
        errors[12] = 'MRO_INVALID_COMMAND_ERROR, there are two possibilities: \n' + \
                     '(1) A least one of the values of the command is out of specs (value > 1.0 or < -1.0).\n' + \
                     '(2) The sum of the absolute values of the command values is greater than 25.0.'
        errors[13] = 'MRO_NULL_POINTER_ERROR, a null pointer has been identified as a parameter which cannot be null.'
        errors[14] = 'MRO_OUT_OF_BOUNDS_ERROR, this happens when an index parameter is out of its possible values.'
        errors[15] = 'MRO_OPERATION_ONGOING_ERROR, operation already in progress. The requested operation cannot be performed due to a synchronization lock.'
        errors[16] = 'MRO_SYSTEM_ERROR, An error has been detected while calling the operating system.'
        errors[17] = 'MRO_UNAVAILABLE_DATA_ERROR, The requested data is unavailable.\n' + \
                     'This can be due to the call of an unavailable functionality or a functionality that needs monitoring to be enabled.'
        errors[18] = 'MRO_UNDEFINED_VALUE_ERROR, The requested value is not available. Ex: request of an undefined stock command value.'
        errors[19] = 'MRO_OUT_OF_SPECIFICATIONS_ERROR, The value, which is not an index, is out of allowed values.'
        errors[20] = 'MRO_FILE_FORMAT_VERSION_ERROR, The file format version is not supported.\n' +\
                     'The version of the MRO file format is not handled by this mirao 52-e API.'
        errors[21] = 'MRO_USB_INVALID_HANDLE, This error implies either an operating system error or an internal driver error.'
        errors[22] = 'MRO_USB_DEVICE_NOT_FOUND, mirao 52-e cannot be found among the USB ports.\n' + \
                     ' There may be several possibilities:\n' + \
                     '(1) The device is not connected to the computer or the connection is defective,\n' + \
                     '(2) The USB port is not correctly installed in the operating system,\n' + \
                     '(3) The mirao 52-e device is not turned ON,\n' + \
                     '(4) The mirao 52-e device is already opened by another process,\n' + \
                     '(5) The mirao 52-e device is defective.'
        errors[23] = 'MRO_USB_DEVICE_NOT_OPENED, Internal driver not opened. This error implies an operating system error.'
        errors[24] = 'MRO_USB_IO_ERROR, Internal driver IO error. The internal driver encountered a problem for reading from \
        or writing to the hardware device.'
        errors[25] = 'MRO_USB_INSUFFICIENT_RESOURCES, There are insufficient system resources to perform the requested operation.'
        errors[26] = 'MRO_USB_INVALID_BAUD_RATE, The configuration of the connection speed is not supported.'
        errors[27] = 'MRO_USB_NOT_SUPPORTED, A functionality is not supported by the internal driver. \n ' +\
                     'Implies an operating system error perhaps due to a bad USB driver version.'
        errors[28] = 'MRO_FILE_IO_EACCES, Permission denied. A file cannot be accessed due to a permission denied error.'
        errors[29] = 'MRO_FILE_IO_EAGAIN, No more processes. An attempt to create a new process failed.'
        errors[30] = 'MRO_FILE_IO_EBADF, Bad file number. An invalid internal file descriptor has been used. This is an operating system error.'
        errors[31] = 'MRO_FILE_IO_EINVAL, An internal invalid argument has been used with a file IO function. This is an operating system error.'
        errors[32] = 'MRO_FILE_IO_EMFILE, Too many opened files. The maximum number of open files allowed by the operating system has been reached.'
        errors[33] = 'MRO_FILE_IO_ENOENT, No such file or directory. The considered file or directory does not exists.'
        errors[34] = 'MRO_FILE_IO_ENOMEM, Not enough memory. The operation requested cannot be performed because the process is out of memory.'
        errors[35] = 'MRO_FILE_IO_ENOSPC, No space left on device. A file cannot be written because the hard drive lacks of space.'

    def _setup_gui(self):
        self.gui.add_tabs("Control Tabs", tabs=['Control', 'Config'])
        tab_name = 'Control'
        groupbox_name = 'Connection'
        self.gui.add_groupbox(title=groupbox_name, parent=tab_name)
        self.gui.add_button('Initialize', groupbox_name, lambda: self.initialize())
        self.gui.add_button('Disconnect', groupbox_name, lambda: self.disconnect())
        self.gui.add_string_field('Status', groupbox_name, value=self.errors[self._status.value], enabled=False)

        groupbox_name = 'Commands'
        self.gui.add_groupbox(title=groupbox_name, parent=tab_name)
        self.gui.add_button('Apply flat', groupbox_name, lambda: self.apply_flat())
        self.gui.add_button('Load from .npy file', groupbox_name, lambda: self.read_npy_file())

        tab_name = 'Config'
        groupbox_name = 'Required files'
        self.gui.add_groupbox(title=groupbox_name, parent=tab_name)
        self.gui.add_string_field('DLL path', groupbox_name, value=self.dll_path, enabled=False)
        self.gui.add_string_field('Flat file', groupbox_name, value=self.flat_file, enabled=False)

    @QtCore.pyqtSlot()
    def _update_gui(self):
        self.gui.update_string_field('Status', self.errors[self._status.value].split()[0])


# run if the module is launched as a standalone program
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dev = DmController()
    dev.gui.show()
    app.exec_()
