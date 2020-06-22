'''This is optimization control adapter for deformable mirror Mirao52.
Takes a camera handle and deformable mirror handle as inputs,
and optimizes PSF in one or two ROIs.
Copyright @nvladimus, 2020
'''

from PyQt5 import QtCore, QtWidgets
import sys
import logging
import widget as wd
from functools import partial
logging.basicConfig()

config = {
    'simulation': True,  # use if no camera and DM are connected.
    'n_iter': 50,  # number of SPGD iterations
    'n_ROIs': 2,  # number of ROIs to apply optimization to
    'gain_ini': 0.03,  # gain parameter in SPGD algorithm.
    'gain_dynamic': True,  # if True, gain grows as (~1/metric) during optimization
    'delta_cmd_volts': 0.002,  # DM perturbation amplitude for individual actuators (in volts).
    'regularization_rate': 0.25,  # weighted average between left/right side of DM, per step.
    'dm_cmd_ini': 'zeros',  # 'zeros' for (0,0, ..) initial command, 'flat' for factory-provided flat command.
    'metric': 'R2integral',  # 'FWHMxy', 'shannonDCT', 'R2Integral', 'R4Integral'
    'object_tracking': 'mass'  # 'xy' for peak, 'mass' for center-of-mass, None for no tracking.
}


class Device(QtCore.QObject):
    sig_update_gui = QtCore.pyqtSignal()

    def __init__(self, dev_name='DM optimizer', gui_on=True, logger_name='Optimizer'):
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

    def run(self):
        self.logger.info('Did something')

    def save_report(self):
        self.logger.info('Report saved')

    def update_config(self, key, value):
        if key in self.config.keys():
            self.config[key] = value
            self.logger.info(f"changed {key} to {value}")
        else:
            self.logger.error("Parameter name not found in config file")
        if self.gui_on:
            self.sig_update_gui.emit()

    def _setup_gui(self):
        self.gui.add_tabs("Control Tabs", tabs=['Main'])
        tab_name = 'Main'
        self.gui.add_checkbox('Simulation', tab_name, value=self.config['simulation'], enabled=False,
                              func=partial(self.update_config, 'simulation'))
        self.gui.add_button('Initialize', tab_name, func=self.initialize)
        self.gui.add_numeric_field('n(iterations)', tab_name, value=self.config['n_iter'],
                                   vmin=5, vmax=1000, func=partial(self.update_config, 'n_iter'))
        self.gui.add_numeric_field('n(ROIS)', tab_name, value=self.config['n_ROIs'], enabled=False)
        self.gui.add_numeric_field('gain (initial)', tab_name, value=self.config['gain_ini'], decimals=2,
                                   vmin=0, vmax=1000, func=partial(self.update_config, 'gain_ini'))
        self.gui.add_checkbox('Dynamic gain', tab_name, value=self.config['gain_dynamic'],
                              func=partial(self.update_config, 'gain_dynamic'))
        self.gui.add_numeric_field('Actuator perturb amp. (V)', tab_name, value=self.config['delta_cmd_volts'],
                                   decimals=3, vmin=0, vmax=0.25, func=partial(self.update_config, 'delta_cmd_volts'))

        self.gui.add_numeric_field('Regularization rate', tab_name, value=self.config['regularization_rate'],
                                   decimals=2, vmin=0, vmax=1, func=partial(self.update_config, 'regularization_rate'))
        self.gui.add_combobox('DM initial command', tab_name, items=['zeros', 'flat'],
                              value=self.config['dm_cmd_ini'], func=partial(self.update_config, 'dm_cmd_ini'))

        self.gui.add_combobox('Metric', tab_name, items=['R2integral', 'FWHMxy', 'shannonDCT',  'R4integral'],
                              value=self.config['metric'], func=partial(self.update_config, 'metric'))

        self.gui.add_combobox('Object tracking', tab_name, items=['mass', 'peak', 'None'],
                              value=self.config['object_tracking'], func=partial(self.update_config, 'object_tracking'))

        self.gui.add_button('Run', tab_name, func=self.run)
        self.gui.add_button('Save report', tab_name, self.save_report)

    @QtCore.pyqtSlot()
    def _update_gui(self):
        #self.gui.update_param('Parameter 1', self.config['param1'])
        self.logger.info('GUI updated')


# run if the module is launched as a standalone program
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    dev = Device()
    dev.gui.show()
    app.exec_()
