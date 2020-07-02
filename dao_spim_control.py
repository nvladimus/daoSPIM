"""
Main program for daoSPIM control.
"""
import sys
sys.path.append('./src')
sys.path.append('./config')
import config
import os
from PyQt5 import QtWidgets
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
import numpy as np
from skimage.external import tifffile
import time
from collections import deque
import hamamatsu_camera as cam
import npy2bdv
import lightsheet_generator as lsg
import deformable_mirror_Mirao52e as def_mirror
import etl_controller_Optotune as etl
import stage_ASI_MS2000 as stage
import scipy.optimize as opt
import logging
logging.basicConfig()


class CameraWindow(QtWidgets.QWidget):
    """Class for stand-alone image display"""
    sig_update_metrics = pyqtSignal()

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.cam_sensor_dims = self.cam_image_dims = parent.dev_cam.config['image_shape']
        self.image_display = pg.ImageView(self)
        self.roi_line_fwhm = self.roi_line_fwhm_data = self.roi_fwhm_text = None
        self.button_cam_snap = QtWidgets.QPushButton('Snap')
        self.button_cam_live = QtWidgets.QPushButton('Live')
        self.combobox_fwhm = QtWidgets.QComboBox()
        self.layout = QtWidgets.QGridLayout(self)
        self.initUI()
        self.add_ROIs()
        self.add_signals()

    def initUI(self):
        """Image display window setup."""
        self.setWindowTitle("Image display window")
        self.move(600, 100)
        self.image_display.setMinimumSize(1200, 800)
        self.image_display.setLevels(100, 500)
        self.combobox_fwhm.addItem("no FWHM(ROI)")
        self.combobox_fwhm.addItem("FWHM(1D)")
        ini_image = np.random.randint(100, 200, size=self.cam_image_dims, dtype='uint16')
        self.image_display.setImage(ini_image, autoRange=False, autoLevels=False, autoHistogramRange=False)
        self.layout.addWidget(self.image_display, 0, 0, 1, 6)
        self.layout.addWidget(self.button_cam_snap, 1, 0)
        self.layout.addWidget(self.combobox_fwhm, 1, 1)
        self.layout.addWidget(self.button_cam_live, 2, 0)
        self.setLayout(self.layout)
        self.setFixedSize(self.layout.sizeHint())

    def add_ROIs(self):
        """Overlay ROIs on top of image display"""
        roi_height_um = 50
        grid_spacing_um = 50
        roi_height_px = int(roi_height_um / config.microscope['pixel_size_um'])
        grid_spacing_px = int(grid_spacing_um / config.microscope['pixel_size_um'])
        dm_diameter_px = int(1000. * config.dm['diameter_mm'] / config.camera['pixel_um'])
        roi_L = pg.RectROI([self.cam_sensor_dims[1]/8.0,
                            self.cam_sensor_dims[0]/2.0 - int(roi_height_px / 2)],
                           [self.cam_sensor_dims[1]/4.0,
                            roi_height_px], movable=False)
        roi_R = pg.RectROI([self.cam_sensor_dims[1]/8.0 + self.cam_sensor_dims[1]/2.0,
                            self.cam_sensor_dims[0] / 2.0 - int(roi_height_px / 2)],
                           [self.cam_sensor_dims[1]/4.0,
                            roi_height_px], movable=False)
        roi_circle = pg.CircleROI([self.cam_sensor_dims[1]/2.0 - dm_diameter_px/2.0,
                                   self.cam_sensor_dims[0]/2.0 - dm_diameter_px/2.0],
                                  [dm_diameter_px, dm_diameter_px], movable=False,
                                  pen=pg.mkPen((100, 100, 100)))
        roi_vline = pg.InfiniteLine(pos=self.cam_sensor_dims[1]/2.0,
                                    angle=90, movable=False,
                                    pen=pg.mkPen((100, 100, 100)))
        # FWHM ROI for interactive curve fitting
        self.roi_line_fwhm = pg.LineROI([-100 + self.cam_sensor_dims[1] * 0.75,
                                         self.cam_sensor_dims[0]/2.0],
                                        [100 + self.cam_sensor_dims[1] * 0.75,
                                         self.cam_sensor_dims[0]/2.0],
                                        width=4, pen=pg.mkPen((200, 200, 0)))
        self.roi_fwhm_text = pg.TextItem("FWHM: none", color=(200, 200, 0))
        self.roi_fwhm_text.setPos(100, 100)

        for i in range(-3, 4):
            vpos = self.cam_sensor_dims[0]/2.0 + i * grid_spacing_px
            roi_hline = pg.InfiniteLine(pos=vpos, angle=0, movable=False, pen=pg.mkPen((150, 150, 150)))
            text_hline = pg.TextItem(f"{i * grid_spacing_um} um", color=(200, 200, 200))
            text_hline.setPos(self.cam_sensor_dims[0]/2.0, vpos)
            # grid_spacing_um
            self.image_display.getView().addItem(roi_hline)
            self.image_display.getView().addItem(text_hline)

        self.image_display.getView().addItem(roi_L)
        self.image_display.getView().addItem(roi_R)
        self.image_display.getView().addItem(roi_circle)
        self.image_display.getView().addItem(roi_vline)
        self.image_display.getView().addItem(self.roi_line_fwhm)
        self.image_display.getView().addItem(self.roi_fwhm_text)
        self.image_display.getView().invertY(False)

    def add_signals(self):
        self.combobox_fwhm.currentTextChanged.connect(self.compute_fwhm)
        self.sig_update_metrics.connect(self.compute_fwhm)

    def compute_fwhm(self):
        if self.combobox_fwhm.currentText() == "FWHM(1D)":
            im = self.image_display.getImageItem()
            self.roi_line_fwhm_data = self.roi_line_fwhm.getArrayRegion(im.image, im)
            avg_array = self.roi_line_fwhm_data.mean(axis=1)
            try:
                _, fwhm = self.compute_fwhm_1d(avg_array)
            except ValueError as e:
                fwhm = 0
            fwhm_um = fwhm * config.microscope['pixel_size_um']
            self.roi_fwhm_text.setText(f"FWHM: {fwhm_um:.2f} um")
            roi_pos = self.roi_line_fwhm.pos()
            self.roi_fwhm_text.setPos(roi_pos)

    def sigma2fwhm(self, sigma):
        return 2.0 * sigma * np.sqrt(2 * np.log(2))

    def normalize_array(self, arr, low_percentile=5.0):
        bg = np.percentile(arr, low_percentile)
        arr_normalized = np.clip((arr - bg) / (arr.max() - bg), 0, 1)
        return arr_normalized

    def gaussian_1d(self, x, xo, sigma_x, amplitude, offset):
        """"Return 1D gaussian"""
        xo = float(xo)
        g = offset + amplitude * np.exp(- ((x - xo) ** 2) / (2 * sigma_x ** 2))
        return g.ravel()

    def compute_fwhm_1d(self, arr):
        arr_norm = self.normalize_array(arr)
        x = np.linspace(0, arr_norm.shape[0] - 1, arr_norm.shape[0]) + 0.5
        # estimate the center position
        peak_val = arr_norm.max()
        max_ind_array = np.where(arr_norm == peak_val)
        if len(max_ind_array) > 0:
            x_peak = max_ind_array[0][0]
        else:
            x_peak = int(arr_norm.shape[0] / 2.0)
        # Parameters: xpos, sigmaX, amp, offset
        initial_guess = (x_peak, 1, 1, 0)
        popt, pcov = opt.curve_fit(self.gaussian_1d, (x),
                                   arr_norm.ravel(), p0=initial_guess,
                                   bounds=((arr_norm.shape[0] * 0.2,
                                            0.1,  # min sigma
                                            0.8, -0.2),  # min amp, offset
                                           (arr_norm.shape[0] * 0.8,
                                            arr_norm.shape[0] * 0.15,  # max sigma
                                            1.2, 0.2)))  # max amp, offset
        xcenter, sigmaX, amp, offset = popt
        fwhm = self.sigma2fwhm(sigmaX)
        return xcenter, fwhm


def get_dirname(path): return '.../' + os.path.basename(os.path.normpath(path)) + '/'


class MainWindow(QtWidgets.QWidget):
    """Wiring up all controls together"""
    def __init__(self, logger_name='main_window'):
        super().__init__()
        self.cam_window = None
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.DEBUG)
        # tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tab_camera = QtWidgets.QWidget()
        self.tab_stage = QtWidgets.QWidget()
        self.tab_lightsheet = QtWidgets.QWidget()
        self.tab_defm = QtWidgets.QWidget()
        self.tab_etl = QtWidgets.QWidget()

        # deformable mirror widgets
        self.dev_dm = def_mirror.DmController(logger_name=self.logger.name + '.DM')

        # light-sheet widget
        self.ls_generator = lsg.LightsheetGenerator()

        # stage widgets
        self.dev_stage = stage.MotionController(logger_name=self.logger.name + '.stage')

        self.groupbox_scanning = QtWidgets.QGroupBox("Scanning")
        self.button_stage_x_move_right = QtWidgets.QPushButton("move ->")
        self.button_stage_x_move_left = QtWidgets.QPushButton("<- move")
        self.spinbox_stage_x_move_step = QtWidgets.QSpinBox(suffix=" um")
        self.button_stage_pos_start = QtWidgets.QPushButton("Mark x-start")
        self.button_stage_pos_stop = QtWidgets.QPushButton("Mark x-stop")
        self.button_stage_start_scan = QtWidgets.QPushButton("Start scan cycle")
        self.checkbox_stage_use_fixed_range = QtWidgets.QCheckBox("Use fixed range, um")
        self.spinbox_stage_speed_x = QtWidgets.QDoubleSpinBox(suffix=' mm/s (speed)')
        self.spinbox_stage_step_x = QtWidgets.QDoubleSpinBox(suffix=' um (trig. intvl)')
        self.spinbox_stage_range_x = QtWidgets.QDoubleSpinBox(suffix=' um (range)')
        self.spinbox_stage_n_cycles = QtWidgets.QSpinBox(suffix=' cycles (time pts)')
        self.label_stage_start_pos = QtWidgets.QLabel("0.0")
        self.label_stage_stop_pos = QtWidgets.QLabel("0.0")

        # camera widgets
        self.dev_cam = cam.CamController(logger_name=self.logger.name + '.camera')

        # ETL widget
        self.dev_etl = etl.ETL_controller(logger_name=self.logger.name + '.ETL')

        # acquisition
        self.groupbox_acq_params = QtWidgets.QGroupBox("Acquisition")
        self.button_cam_acquire = QtWidgets.QPushButton('Acquire and save')
        self.spinbox_n_timepoints = QtWidgets.QSpinBox()
        self.spinbox_frames_per_stack = QtWidgets.QSpinBox()
        self.spinbox_nangles = QtWidgets.QSpinBox()

        # saving
        self.groupbox_saving = QtWidgets.QGroupBox("Saving")

        self.button_save_folder = QtWidgets.QPushButton(get_dirname(config.saving['root_folder']))
        self.line_subfolder = QtWidgets.QLineEdit("subfolder")
        self.line_prefix = QtWidgets.QLineEdit("stack")
        self.combobox_file_format = QtWidgets.QComboBox()
        self.checkbox_simulation = QtWidgets.QCheckBox("Simulation mode")

        self.button_exit = QtWidgets.QPushButton('Exit')

        # GUI layouts
        self.layout = QtWidgets.QVBoxLayout(self)
        self.tab_camera.layout = QtWidgets.QFormLayout()
        self.tab_stage.layout = QtWidgets.QFormLayout()
        self.tab_lightsheet.layout = QtWidgets.QFormLayout()
        self.tab_defm.layout = QtWidgets.QFormLayout()
        self.tab_etl.layout = QtWidgets.QFormLayout()
        self.initUI()

        # Internal parameters
        self.n_frames_per_stack = self.n_stacks_to_grab = self.n_frames_to_grab = self.n_angles = None
        self.file_save_running = self.abort_pressed = False
        self.root_folder = config.saving['root_folder']
        self.dir_path = self.file_path = None
        self.file_format = "HDF5"
        # Set up threads and signals
        self.thread_live_mode = QtCore.QThread()
        self.worker_live_mode = LiveImagingWorker(self, self.dev_cam)
        self.worker_live_mode.moveToThread(self.thread_live_mode)
        self.thread_live_mode.started.connect(self.worker_live_mode.update)
        self.worker_live_mode.sig_finished.connect(self.thread_live_mode.quit)

        self.thread_saving_files = QtCore.QThread()
        self.worker_saving = SavingStacksWorker(self, self.dev_cam, self.logger)
        self.worker_saving.moveToThread(self.thread_saving_files)
        self.thread_saving_files.started.connect(self.worker_saving.run)

        self.thread_frame_grabbing = QtCore.QThread()
        self.worker_grabbing = CameraFrameGrabbingWorker(self, self.dev_cam, self.logger)
        self.worker_grabbing.moveToThread(self.thread_frame_grabbing)
        self.thread_frame_grabbing.started.connect(self.worker_grabbing.run)
        self.worker_grabbing.signal_save_data.connect(self.worker_saving.append_new_data)
        self.worker_grabbing.sig_dummy_send.connect(self.worker_saving.dummy_receive)

        self.thread_stage_scanning = QtCore.QThread()
        self.worker_stage_scanning = StageScanningWorker(self, self.logger)
        self.worker_stage_scanning.moveToThread(self.thread_stage_scanning)
        self.thread_stage_scanning.started.connect(self.worker_stage_scanning.scan)
        self.worker_stage_scanning.finished.connect(self.thread_stage_scanning.quit)

    def initUI(self):
        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setWindowTitle("Microscope control")
        self.move(50, 100)
        # set up Tabs
        self.tabs.addTab(self.tab_camera, "Camera")
        self.tabs.addTab(self.tab_stage, "Stage")
        self.tabs.addTab(self.tab_lightsheet, "Light sheet")
        self.tabs.addTab(self.tab_defm, "Def. mirror")
        self.tabs.addTab(self.tab_etl, "ETL")

        # DEFORMABLE Mirror tab
        self.tab_defm.layout.addWidget(self.dev_dm.gui)
        self.dev_dm.gui.setFixedWidth(300)
        self.tab_defm.setLayout(self.tab_defm.layout)

        # ETL tab
        self.tab_etl.layout.addWidget(self.dev_etl.gui)
        self.dev_etl.gui.setFixedWidth(300)
        self.tab_etl.setLayout(self.tab_etl.layout)

        #LIGHTSHEET tab
        self.tab_lightsheet.layout.addWidget(self.ls_generator.gui)
        self.tab_lightsheet.setLayout(self.tab_lightsheet.layout)

        # Stage tab
        self.dev_stage.gui.setFixedWidth(300)
        self.button_stage_pos_start.setFixedWidth(80)
        self.button_stage_pos_stop.setFixedWidth(80)

        self.label_stage_start_pos.setFixedWidth(60)
        self.label_stage_stop_pos.setFixedWidth(60)

        self.button_stage_start_scan.setFixedWidth(240)
        self.checkbox_stage_use_fixed_range.setChecked(True)

        self.spinbox_stage_speed_x.setValue(0.2)
        self.spinbox_stage_speed_x.setMinimum(0.01)
        self.spinbox_stage_speed_x.setFixedWidth(160)
        self.spinbox_stage_speed_x.setDecimals(3)
        self.spinbox_stage_speed_x.setEnabled(False)

        self.spinbox_stage_step_x.setDecimals(3)
        self.spinbox_stage_step_x.setValue(config.scanning['step_x_um'])
        self.spinbox_stage_step_x.setMinimum(0.022)
        self.spinbox_stage_step_x.setFixedWidth(160)
        self.spinbox_stage_step_x.setSingleStep(0.022)

        self.spinbox_stage_n_cycles.setValue(1)
        self.spinbox_stage_n_cycles.setMinimum(1)
        self.spinbox_stage_n_cycles.setMaximum(1000)
        self.spinbox_stage_n_cycles.setFixedWidth(160)
        self.spinbox_stage_n_cycles.setEnabled(False)

        self.spinbox_stage_range_x.setValue(50)
        self.spinbox_stage_range_x.setFixedWidth(160)
        self.spinbox_stage_range_x.setDecimals(0)
        self.spinbox_stage_range_x.setSingleStep(1)
        self.spinbox_stage_range_x.setRange(1, 1000)

        self.button_stage_x_move_right.setFixedWidth(80)
        self.button_stage_x_move_left.setFixedWidth(80)

        self.spinbox_stage_x_move_step.setValue(5)
        self.spinbox_stage_x_move_step.setFixedWidth(60)
        self.spinbox_stage_x_move_step.setRange(1, 500)

        layout_stage_start_stop = QtWidgets.QGridLayout()
        layout_stage_start_stop.addWidget(self.button_stage_pos_start, 0, 0)
        layout_stage_start_stop.addWidget(self.label_stage_start_pos, 0, 1)
        layout_stage_start_stop.addWidget(self.button_stage_pos_stop, 0, 2)
        layout_stage_start_stop.addWidget(self.label_stage_stop_pos, 0, 3)
        layout_stage_start_stop.addWidget(self.button_stage_x_move_right, 1, 0)
        layout_stage_start_stop.addWidget(self.spinbox_stage_x_move_step, 1, 1)
        layout_stage_start_stop.addWidget(self.button_stage_x_move_left, 1, 2)

        self.tab_stage.layout.addWidget(self.dev_stage.gui)
        self.tab_stage.layout.addWidget(self.spinbox_stage_speed_x)
        self.tab_stage.layout.addWidget(self.spinbox_stage_step_x)
        self.tab_stage.layout.addWidget(self.checkbox_stage_use_fixed_range)
        self.tab_stage.layout.addWidget(self.spinbox_stage_range_x)
        self.tab_stage.layout.addWidget(self.spinbox_stage_n_cycles)
        self.tab_stage.layout.addRow(layout_stage_start_stop)
        self.tab_stage.layout.addRow(self.button_stage_start_scan)

        self.tab_stage.setLayout(self.tab_stage.layout)

        # CAMERA window
        self.cam_window = CameraWindow(self)
        self.cam_window.show()

        # acquisition params
        self.groupbox_acq_params.setFixedWidth(300)

        self.spinbox_n_timepoints.setValue(1)
        self.spinbox_n_timepoints.setFixedWidth(60)
        self.spinbox_n_timepoints.setMaximum(10000)
        self.spinbox_n_timepoints.setMinimum(1)

        self.spinbox_frames_per_stack.setValue(40)
        self.spinbox_frames_per_stack.setFixedWidth(60)
        self.spinbox_frames_per_stack.setRange(1, 1000)

        self.spinbox_nangles.setValue(2)
        self.spinbox_nangles.setEnabled(False)
        self.spinbox_nangles.setFixedWidth(60)

        layout_acquisition = QtWidgets.QFormLayout()
        layout_acquisition.addRow("Images per stack:", self.spinbox_frames_per_stack)
        layout_acquisition.addRow("Time points:", self.spinbox_n_timepoints)
        layout_acquisition.addRow("n(angles):", self.spinbox_nangles)
        self.groupbox_acq_params.setLayout(layout_acquisition)

        # saving, layouts
        self.groupbox_saving.setFixedWidth(300)
        self.line_subfolder.setAlignment(QtCore.Qt.AlignRight)
        self.line_prefix.setAlignment(QtCore.Qt.AlignRight)
        self.combobox_file_format.setFixedWidth(80)
        self.combobox_file_format.addItem("HDF5")
        self.combobox_file_format.addItem("TIFF")

        layout_files = QtWidgets.QFormLayout()
        layout_files.addRow(self.button_save_folder)
        layout_files.addRow(self.line_subfolder)
        layout_files.addRow(self.line_prefix)
        layout_files.addRow("Format", self.combobox_file_format)
        self.groupbox_saving.setLayout(layout_files)

        # Camera controls layout
        self.dev_cam.gui.setFixedWidth(300)
        self.button_cam_acquire.setFixedWidth(300)
        # self.checkbox_with_scanning.setChecked(True)
        # self.checkbox_with_scanning.setToolTip('Start scanning cycle after camera started')

        self.tab_camera.layout.addWidget(self.dev_cam.gui)
        self.tab_camera.layout.addWidget(self.groupbox_acq_params)
        self.tab_camera.layout.addWidget(self.button_cam_acquire)
        self.tab_camera.layout.addWidget(self.groupbox_saving)
        self.tab_camera.setLayout(self.tab_camera.layout)

        # global layout
        self.button_exit.setFixedWidth(120)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.button_exit)
        self.setLayout(self.layout)

        # Signals Camera control
        self.cam_window.button_cam_snap.clicked.connect(self.button_snap_clicked)
        self.cam_window.button_cam_live.clicked.connect(self.button_live_clicked)
        self.button_cam_acquire.clicked.connect(self.button_acquire_clicked)
        self.button_save_folder.clicked.connect(self.button_save_folder_clicked)
        self.combobox_file_format.currentTextChanged.connect(self.set_file_format)
        self.button_exit.clicked.connect(self.button_exit_clicked)

        # Signals Stage control
        self.button_stage_x_move_right.clicked.connect(self.stage_x_move_right)
        self.button_stage_x_move_left.clicked.connect(self.stage_x_move_left)
        self.button_stage_pos_start.clicked.connect(self.stage_mark_start_pos)
        self.button_stage_pos_stop.clicked.connect(self.stage_mark_stop_pos)
        self.button_stage_start_scan.clicked.connect(self.start_scan)

        self.dev_cam.gui.params['Exposure, ms'].editingFinished.connect(self.update_calculator)
        self.spinbox_stage_step_x.valueChanged.connect(self.update_calculator)
        self.spinbox_stage_range_x.valueChanged.connect(self.update_calculator)
        self.spinbox_n_timepoints.valueChanged.connect(self.update_calculator)

    def start_scan(self):
        self.worker_stage_scanning.setup(self.dev_stage, self.n_stacks_to_grab)
        self.thread_stage_scanning.start()

    def stage_x_move_right(self):
        if self.dev_stage.initialized:
            self.dev_stage.get_position()
            pos_x, pos_y = self.dev_stage.position_x_mm, self.dev_stage.position_y_mm
            new_x, new_y = pos_x - 0.001 * self.spinbox_stage_x_move_step.value(), pos_y
            self.dev_stage.move_abs((new_x, new_y))
            self.logger.debug(f'new_x:{new_x:.4f}')
        else:
            self.logger.error("Please activate stage first")

    def stage_x_move_left(self):
        if self.dev_stage.initialized:
            self.dev_stage.get_position()
            pos_x, pos_y = self.dev_stage.position_x_mm, self.dev_stage.position_y_mm
            new_x, new_y = pos_x + 0.001 * self.spinbox_stage_x_move_step.value(), pos_y
            self.dev_stage.move_abs((new_x, new_y))
            self.logger.debug(f'new_x:{new_x:.4f}')
        else:
            self.logger.error("Please activate stage first")

    def stage_mark_start_pos(self):
        if self.dev_stage.initialized:
            self.dev_stage.get_position()
            pos = self.dev_stage.position_x_mm - self.dev_stage.backlash_mm
            self.label_stage_start_pos.setText(f'{pos:.4f}')
            self.dev_stage.set_scan_region(pos, scan_boundary='x_start')
            self.dev_stage.set_scan_region(self.dev_stage.position_y_mm, scan_boundary='y_start')
        else:
            self.logger.error("Please activate stage first")

    def stage_mark_stop_pos(self):
        if self.dev_stage.initialized:
            self.dev_stage.get_position()
            if self.checkbox_stage_use_fixed_range.isChecked():
                start = float(self.label_stage_start_pos.text().strip())
                pos = start + self.spinbox_stage_range_x.value()/1000. + 2*self.dev_stage.backlash_mm
                self.label_stage_stop_pos.setText(f'{pos:.4f}')
            else:
                pos = self.dev_stage.position_x_mm + self.dev_stage.backlash_mm
                self.label_stage_stop_pos.setText(f'{pos:.4f}')
            self.dev_stage.set_scan_region(pos, scan_boundary='x_stop')
            self.dev_stage.set_scan_region(self.dev_stage.position_y_mm, scan_boundary='y_stop')
        else:
            self.logger.error("Please activate stage first")

    def update_calculator(self):
        # speed = (stepX) / (timing between steps, trigger-coupled to exposure)
        if self.dev_cam.exposure_ms != 0:
            stage_speed_x = self.spinbox_stage_step_x.value() / self.dev_cam.exposure_ms
            self.spinbox_stage_speed_x.setValue(stage_speed_x)

        if self.spinbox_n_timepoints.value() != 0:
            self.spinbox_stage_n_cycles.setValue(self.spinbox_n_timepoints.value())

        # feed the trigger interval to the stage settings
        if self.dev_stage.initialized:
            stage_step_x_mm = 0.001 * self.spinbox_stage_step_x.value()
            self.dev_stage.set_trigger_intervals(stage_step_x_mm, trigger_axis='X')
            self.dev_stage.set_speed(stage_speed_x, axis='X')

        if self.spinbox_stage_speed_x.value() != 0:
            exposure_ms = self.spinbox_stage_step_x.value() / self.spinbox_stage_speed_x.value()
            if self.dev_cam is not None:
                self.dev_cam.set_exposure(exposure_ms)

        # n(trigger pulses, coupled to exposure) = (scan range) / (stepX)
        if self.spinbox_stage_step_x.value() != 0:
            n_triggers = int((self.spinbox_stage_range_x.value() + 1000 * 2 * self.dev_stage.backlash_mm)
                             / self.spinbox_stage_step_x.value())
            self.spinbox_frames_per_stack.setValue(n_triggers)
            if self.ls_generator.initialized:
                self.ls_generator.set_switching_period(n_triggers)

    def button_exit_clicked(self):
        if self.dev_cam.dev_handle is not None:
            self.dev_cam.dev_handle.shutdown()
        if self.dev_dm.dev_handle is not None:
            self.dev_dm.close()
        self.cam_window.close()
        self.close()

    def button_snap_clicked(self):
        self.dev_cam.snap()
        self.display_image(self.dev_cam.last_image, position=(0, self.dev_cam.cam_voffset))

    def display_image(self, image, position=None, text_update=False):
        """
        Update the GUI with new image from the camera.
        :param image: 2-dim numpy array, full resolution, 'uint16' type.
        :param text_update: print image min and max in log window (default False)
        :param position: tuple of image (x,y) position.
        :return: None
        """
        self.cam_window.image_display.setImage(image.T, autoRange=False, autoLevels=False,
                                    pos=position, autoHistogramRange=False)
        self.cam_window.sig_update_metrics.emit()
        if text_update:
            self.logger.info("(min, max): (" + str(image.min()) + "," + str(image.max()) + ")\n")

    def button_live_clicked(self):
        if not self.dev_cam.status == 'Running':
            self.dev_cam.status = 'Running'
            self.thread_live_mode.start()
            self.cam_window.button_cam_live.setText("Stop")
            self.cam_window.button_cam_live.setStyleSheet('QPushButton {color: red;}')
        else:  # if clicked while running
            self.dev_cam.status = 'Idle'
            self.cam_window.button_cam_live.setText("Live")
            self.cam_window.button_cam_live.setStyleSheet('QPushButton {color: black;}')

    def button_acquire_clicked(self):
        '''
        Start camera acquisition and file saving
        '''
        # start acquisition
        if (not self.abort_pressed) and (self.dev_cam.status != 'Running') and (not self.file_save_running):
            self.create_folder()
            self.check_cam_initialized()
            self.dev_cam.status = 'Running'
            self.button_acquire_reset()
            self.n_frames_per_stack = int(self.spinbox_frames_per_stack.value())
            self.n_stacks_to_grab = int(self.spinbox_n_timepoints.value() * self.spinbox_nangles.value())
            self.n_frames_to_grab = self.n_stacks_to_grab * self.n_frames_per_stack
            self.n_angles = int(self.spinbox_nangles.value())
            self.dev_cam.setup()
            self.ls_generator.setup()
            self.worker_grabbing.setup(self.n_frames_to_grab)
            self.worker_saving.setup(self.n_frames_to_grab, self.n_frames_per_stack,
                                     self.n_angles, self.dev_cam.frame_height_px)
            self.thread_frame_grabbing.start()
            self.thread_saving_files.start()
            if not self.dev_cam.config['simulation']:
                self.dev_cam.dev_handle.setACQMode("run_till_abort")
        # If pressed DURING acquisition, abort acquisition and saving
        elif self.dev_cam.status == 'Running' and self.file_save_running:
            self.dev_cam.status = 'Idle'
            self.abort_pressed = True
            self.button_acquire_reset()
            self.thread_frame_grabbing.wait()
            self.thread_saving_files.wait()

    def check_cam_initialized(self):
        if self.dev_cam.config['simulation']:
            pass
        elif self.dev_cam.dev_handle is None:
            self.logger.error("Please initialize the camera.")
            self.abort_pressed = True

    def create_folder(self):
        """Create new folder for acquisition."""
        self.dir_path = self.root_folder + "/" + self.line_subfolder.text()
        i_dir = 0
        while os.path.exists(self.dir_path + f'_v{i_dir}'): i_dir += 1
        self.dir_path += f'_v{i_dir}'
        os.mkdir(self.dir_path)
        self.file_path = self.dir_path + "/" + self.line_prefix.text()
        self.logger.info("Experiment folder: " + self.dir_path)

    def button_acquire_reset(self):
        if (not self.dev_cam.status == 'Running') and (not self.file_save_running):
            self.button_cam_acquire.setText("Acquire and save")
            self.button_cam_acquire.setStyleSheet('QPushButton {color: black;}')
        if (not self.dev_cam.status == 'Running') and self.file_save_running:
            self.button_cam_acquire.setText("Saving...")
            self.button_cam_acquire.setStyleSheet('QPushButton {color: blue;}')
        if self.dev_cam.status == 'Running':
            self.button_cam_acquire.setText("Abort")
            self.button_cam_acquire.setStyleSheet('QPushButton {color: red;}')

    def button_save_folder_clicked(self):
        file_dialog = QtWidgets.QFileDialog()
        file_dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        folder = file_dialog.getExistingDirectory(self, "Save to folder", self.root_folder)
        if folder:
            self.root_folder = folder
            self.button_save_folder.setText(get_dirname(folder))
            self.logger.info("Root folder for saving: " + self.root_folder)

    def set_file_format(self, new_format):
        self.file_format = new_format


class LiveImagingWorker(QtCore.QObject):
    """
    Acquire one image at a time and display it.
    """
    sig_finished = pyqtSignal()

    def __init__(self, parent_window, camera):
        super().__init__()
        self.parent_window = parent_window
        self.camera = camera

    @QtCore.pyqtSlot()
    def update(self):
        while self.camera.status == 'Running':
            self.parent_window.button_snap_clicked()
            time.sleep(0.2)
        self.sig_finished.emit()


class StageScanningWorker(QtCore.QObject):
    """
    Scan the stage multiple cycles. Proper use of QThread via worker object.
    """
    finished = pyqtSignal()

    def __init__(self, camera_window, logger):
        super().__init__()
        self.camera_window = camera_window
        self.logger = logger
        self.dev_stage = None

    @QtCore.pyqtSlot()
    def setup(self, dev_stage, n_lines):
        self.dev_stage = dev_stage
        self.dev_stage.set_n_scan_lines(n_lines)

    @QtCore.pyqtSlot()
    def scan(self):
        if self.dev_stage.initialized:
            self.dev_stage.start_scan()
            # wait for response of move completion
            response = self.dev_stage.write_with_response(b'/')
            while response[0] != 'N':
                response = self.dev_stage.write_with_response(b'/')
                time.sleep(0.05)
            self.dev_stage.logger.debug(f"move complete")
            # return to scan start position
            self.dev_stage.move_abs((self.dev_stage.scan_limits_xx_yy[0], self.dev_stage.scan_limits_xx_yy[2]))
            self.dev_stage.get_position()
        else:
            self.logger.error("Please activate stage first")
        self.finished.emit()


class CameraFrameGrabbingWorker(QtCore.QObject):
    """
    Grab images from the camera and save them into list.
    """
    signal_GUI = pyqtSignal()
    signal_save_data = pyqtSignal(object)
    signal_display_image = pyqtSignal(object)
    sig_dummy_send = pyqtSignal()

    def __init__(self, parent_window, camera, logger):
        super().__init__()
        self.parent_window = parent_window
        self.camera = camera
        self.logger = logger
        self.signal_GUI.connect(self.parent_window.button_acquire_reset)
        self.signal_display_image.connect(self.parent_window.display_image)
        self.gui_update_interval_s = 1.0
        self.n_frames_to_grab = None
        self.n_frames_grabbed = None

    def setup(self, n_frames_to_grab):
        self.n_frames_to_grab = n_frames_to_grab
        self.n_frames_grabbed = 0

    @QtCore.pyqtSlot()
    def run(self):
        if not self.camera.config['simulation']:
            self.camera.dev_handle.startAcquisition()
        self.logger.info("Camera started")
        start_time = time.time()
        while (self.camera.status == 'Running') and (self.n_frames_grabbed < self.n_frames_to_grab):
            if self.camera.config['simulation']:
                self.n_frames_grabbed += 1
                sim_image_16bit = np.random.randint(100, 200, size=2048 * 2048, dtype='uint16')
                frame_data = [sim_image_16bit]
                self.signal_save_data.emit(frame_data)
                self.signal_display_image.emit(np.reshape(frame_data, self.camera.config['image_shape']))
            else:
                [frames, dims] = self.camera.dev_handle.getFrames()
                self.n_frames_grabbed += len(frames)
                if len(frames) > 0:
                    frame_data = []
                    for frame in frames:
                        frame_data.append(frame.getData())
                    self.signal_save_data.emit(frame_data)
                    self.sig_dummy_send.emit()
                    self.logger.debug(f"dummy emitted")
                    time_stamp = time.time()
                    if (time_stamp - start_time) >= self.gui_update_interval_s:
                        start_time = time.time()
                        self.signal_display_image.emit(np.reshape(frame_data[0], dims))
        # Clean up after the main cycle is done
        if not self.camera.config['simulation']:
            self.camera.dev_handle.stopAcquisition()
            self.logger.debug(f"camera finished")
        self.camera.status = 'Idle'
        self.signal_GUI.emit()


class SavingStacksWorker(QtCore.QObject):
    """
    Save stacks to files
    """
    signal_GUI = pyqtSignal()

    def __init__(self, parent_window, camera, logger):
        super().__init__()
        self.parent_window = parent_window
        self.camera = camera
        self.logger = logger
        self.frames_to_save = self.frames_per_stack = self.n_angles = self.frames_saved = None
        self.stack_counter = self.angle_counter = self.bdv_writer = self.stack = self.cam_image_height = None
        self.frameQueue = deque([])
        self.signal_GUI.connect(self.parent_window.button_acquire_reset)

    def setup(self, frames_to_save, frames_per_stack, n_angles, image_height):
        self.frames_to_save = frames_to_save
        self.frames_per_stack = frames_per_stack
        self.n_angles = n_angles
        self.frames_saved = 0
        self.stack_counter = 0
        self.angle_counter = 0
        self.cam_image_height = image_height
        self.stack = np.empty((frames_per_stack, self.cam_image_height, 2048), 'uint16')

    @QtCore.pyqtSlot(object)
    def append_new_data(self, obj_list):
        if len(obj_list) > 0:
            self.logger.debug(f"received {len(obj_list)}")
            self.frameQueue.extend(obj_list)
        else:
            pass

    @QtCore.pyqtSlot()
    def dummy_receive(self):
        self.logger.debug("dummy received")

    @QtCore.pyqtSlot()
    def run(self):
        self.parent_window.file_save_running = True
        if self.parent_window.file_format == "HDF5":
            self.bdv_writer = npy2bdv.BdvWriter(self.parent_window.file_path + '.h5',
                                                nangles=self.n_angles,
                                                subsamp=((1, 1, 1),))
        elif self.parent_window.file_format == "TIFF":
            pass

        while (self.frames_saved < self.frames_to_save) and not self.parent_window.abort_pressed:
            if len(self.frameQueue) >= self.frames_per_stack:
                for iframe in range(self.frames_per_stack):
                    plane = self.frameQueue.popleft()
                    self.stack[iframe, :, :] = np.reshape(plane, (self.cam_image_height, 2048))
                    self.frames_saved += 1
                # print("stack#" + str(self.stack_counter))
                # print("frames_saved:" + str(self.frames_saved))
                # print("queue length:" + str(len(self.frameQueue)))
                self.logger.debug(f"frames: {self.frames_saved} of {self.frames_to_save}")
                if self.parent_window.file_format == "HDF5":
                    z_voxel_size = self.parent_window.spinbox_stage_step_x.value() / np.sqrt(2)
                    z_anisotropy = z_voxel_size / config.microscope['pixel_size_um']
                    affine_matrix = np.array(((1.0, 0.0, 0.0, 0.0),
                                              (0.0, 1.0, -z_anisotropy, 0.0),
                                              (0.0, 0.0, 1.0, 0.0)))
                    voxel_size = (config.microscope['pixel_size_um'], config.microscope['pixel_size_um'], z_voxel_size)
                    self.bdv_writer.append_view(self.stack,
                                                time=int(self.stack_counter / self.n_angles),
                                                angle=self.angle_counter,
                                                m_affine=affine_matrix,
                                                name_affine="unshearing transformation",
                                                calibration=(1, 1, 1),
                                                voxel_size_xyz=voxel_size,
                                                exposure_time=self.camera.exposure_ms
                                                )
                elif self.parent_window.file_format == "TIFF":
                    file_name = self.parent_window.file_path + \
                                "_t{:05d}a{:01d}.tiff".format(self.stack_counter, self.angle_counter)
                    tifffile.imsave(file_name, self.stack)
                else:
                    self.logger.error(f"unknown format:{self.parent_window.file_format}")

                self.stack_counter += 1
                self.angle_counter = (self.angle_counter + 1) % self.n_angles
            else:
                time.sleep(0.02)
        # clean-up:
        if self.parent_window.file_format == "HDF5":
            if not self.parent_window.abort_pressed:
                self.bdv_writer.write_xml_file(ntimes=int(self.stack_counter / self.n_angles),
                                               camera_name="Hamamatsu OrcaFlash 4.3")
            self.bdv_writer.close()
        elif self.parent_window.file_format == "TIFF":
            pass
        self.frameQueue.clear()
        self.parent_window.file_save_running = False
        self.logger.info(f"Saved {self.frames_saved} images in {self.stack_counter} stacks with {self.n_angles} angles")
        self.signal_GUI.emit()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
