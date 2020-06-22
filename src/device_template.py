'''This is a template for device adapter.
Copyright @nvladimus, 2020
'''

from PyQt5 import QtCore, QtWidgets
import sys
import logging
import widget as wd
from functools import partial
logging.basicConfig()

config = {
    'param1': 1.0,  # numerical parameter
    'param2': 'string',  # string parameter
    'param3': True,  # checkbox
    'param4': 'option1'  # combobox parameter
}


class Device(QtCore.QObject):
    sig_update_gui = QtCore.pyqtSignal()

    def __init__(self, dev_name='Device name', gui_on=True, logger_name='dev logger'):
        super().__init__()
        self.config = config
        self.initialized = False
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
        self.logger.info('Initialized')

    def close(self):
        self.logger.info('Closed')

    def do_something(self):
        self.logger.info('Did something')

    def update_config(self, key, value):
        if key in self.config.keys():
            self.config[key] = value
            self.logger.info(f"changed {key} to {value}")
        else:
            self.logger.error("Parameter name not found in config file")
        if self.gui_on:
            self.sig_update_gui.emit()

    def _setup_gui(self):
        self.gui.add_tabs("Control Tabs", tabs=['Tab 1', 'Tab 2'])
        tab_name = 'Tab 1'
        self.gui.add_button('Initialize', tab_name, func=self.initialize)
        self.gui.add_numeric_field('Parameter 1', tab_name, value=self.config['param1'],
                                   vmin=0.1, vmax=100, decimals=1,
                                   func=partial(self.update_config, 'param1'))
        self.gui.add_string_field('Parameter 2', tab_name, value=self.config['param2'], enabled=False)
        self.gui.add_checkbox('Parameter 3', tab_name,  value=self.config['param3'],
                              func=partial(self.update_config, 'param3'))
        self.gui.add_combobox('Parameter 4', tab_name, items=['option1', 'option2'],
                              value=self.config['param4'], func=partial(self.update_config, 'param4'))
        self.gui.add_button('Disconnect', tab_name, lambda: self.close())

    @QtCore.pyqtSlot()
    def _update_gui(self):
        self.gui.update_param('Parameter 1', self.config['param1'])
        self.logger.info('GUI updated')


# run if the module is launched as a standalone program
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dev = Device()
    dev.gui.show()
    app.exec_()
