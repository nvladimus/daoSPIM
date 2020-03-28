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
import ctypes
import PyDAQmx as pd
import numpy as np
from skimage.external import tifffile
import time
from collections import deque
import hamamatsu_camera as cam
import npy2bdv
import lsgeneration as ls
import deformable_mirror_Mirao52e as def_mirror
import serial
import etl_controller_Optotune as etl
import scipy.optimize as opt


class CameraWindow(QtWidgets.QWidget):
    """Class for stand-alone image display"""
    sig_update_metrics = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.cam_sensor_dims = self.cam_image_dims = (config.camera['image_width'], config.camera['image_height'])
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
            #grid_spacing_um
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


class MainWindow(QtWidgets.QWidget):
    """Wiring up all controls together"""
    def __init__(self):
        super().__init__()
        self.cam_window = None

        # tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tab_camera = QtWidgets.QWidget()
        self.tab_stage = QtWidgets.QWidget()
        self.tab_lightsheet = QtWidgets.QWidget()
        self.tab_defm = QtWidgets.QWidget()
        self.tab_etl = QtWidgets.QWidget()

        # deformable mirror widgets
        self.dev_dm = def_mirror.DmController()

        # light-sheet widgets
        self.spinbox_ls_duration = QtWidgets.QDoubleSpinBox()
        self.spinbox_ls_galvo_offset0 = QtWidgets.QDoubleSpinBox()
        self.spinbox_ls_galvo_offset1 = QtWidgets.QDoubleSpinBox()
        self.spinbox_ls_galvo_amp0 = QtWidgets.QDoubleSpinBox()
        self.spinbox_ls_galvo_amp1 = QtWidgets.QDoubleSpinBox()
        self.spinbox_ls_laser_volts = QtWidgets.QDoubleSpinBox()
        self.checkbox_ls_switch_automatically = QtWidgets.QCheckBox("Switch arms automatically")
        self.combobox_ls_side = QtWidgets.QComboBox()
        self.button_ls_activate = QtWidgets.QPushButton("Activate light sheet")
        self.combobox_ls_port = QtWidgets.QComboBox()
        self.serial_ls = None

        # stage widgets
        self.button_stage_connect = QtWidgets.QPushButton("Connect to stage")
        self.button_stage_x_move_right = QtWidgets.QPushButton("move ->")
        self.button_stage_x_move_left = QtWidgets.QPushButton("<- move")
        self.spinbox_stage_x_move_step = QtWidgets.QSpinBox(suffix=" um")
        self.button_stage_pos_start = QtWidgets.QPushButton("Mark start pos. >")
        self.button_stage_pos_stop = QtWidgets.QPushButton("< Mark stop pos.")
        self.button_stage_start_scan = QtWidgets.QPushButton("Start scan cycle")
        self.checkbox_stage_use_fixed_range = QtWidgets.QCheckBox("Use fixed range, um")
        self.combobox_stage_port = QtWidgets.QComboBox()
        self.combobox_stage_scan_mode = QtWidgets.QComboBox()
        self.spinbox_stage_speed_x = QtWidgets.QDoubleSpinBox()
        self.spinbox_stage_step_x = QtWidgets.QDoubleSpinBox()
        self.spinbox_stage_range_x = QtWidgets.QDoubleSpinBox()
        self.spinbox_stage_n_cycles = QtWidgets.QSpinBox()
        self.label_stage_start_pos = QtWidgets.QLabel("0.0")
        self.label_stage_stop_pos = QtWidgets.QLabel("0.0")
        self.label_stage_current_pos = QtWidgets.QLabel("0.0")
        self.serial_stage = None

        # camera widgets
        self.button_cam_initialize = QtWidgets.QPushButton('Initialize camera')
        self.button_cam_acquire = QtWidgets.QPushButton('Acquire and save')
        self.button_cam_disconnect = QtWidgets.QPushButton('Disconnect camera')
        self.label_cam_readout_time = QtWidgets.QLabel("Readout time, ms: ")

        # ETL widget
        self.dev_etl = etl.ETL_controller(config.etl['port'])

        # Global widgets
        self.text_log = QtWidgets.QTextEdit(self)
        self.button_exit = QtWidgets.QPushButton('Exit')

        # camera, acquisition
        self.groupbox_acq_params = QtWidgets.QGroupBox("Acquisition")
        self.spinbox_exposure_ms = QtWidgets.QDoubleSpinBox()
        self.spinbox_n_timepoints = QtWidgets.QSpinBox()
        self.spinbox_frames_per_stack = QtWidgets.QSpinBox()
        self.spinbox_nangles = QtWidgets.QSpinBox()
        self.button_cam_set_roi = QtWidgets.QPushButton('Set camera ROI height')
        self.spinbox_vsize = QtWidgets.QSpinBox()

        # Triggers IN
        self.groupbox_triggering = QtWidgets.QGroupBox("Triggering")
        self.checkbox_triggers_in = QtWidgets.QCheckBox("Triggers IN")
        self.combobox_input_trig_mode = QtWidgets.QComboBox()
        self.combobox_input_trig_type = QtWidgets.QComboBox()
        self.combobox_mpulse_source = QtWidgets.QComboBox()
        self.combobox_input_trig_source = QtWidgets.QComboBox()
        self.combobox_mpulse_mode = QtWidgets.QComboBox()
        self.lineedit_mpulse_nbursts = QtWidgets.QLineEdit("10")
        self.lineedit_mpulse_interval = QtWidgets.QLineEdit("10")

        # Triggers OUT
        self.checkbox_triggers_out = QtWidgets.QCheckBox("Triggers OUT")
        self.combobox_output_trig_kind = QtWidgets.QComboBox()
        self.lineedit_output_trig_period = QtWidgets.QLineEdit("1")
        self.combobox_output_trig_polarity = QtWidgets.QComboBox()
        self.combobox_output_trig_source = QtWidgets.QComboBox()

        # saving
        self.groupbox_saving = QtWidgets.QGroupBox("Saving")
        self.button_saveto = QtWidgets.QPushButton("...")
        self.lineedit_experimentID = QtWidgets.QLineEdit("sample")
        self.lineedit_file_prefix = QtWidgets.QLineEdit("stacks")
        self.combobox_file_format = QtWidgets.QComboBox()
        self.checkbox_simulation = QtWidgets.QCheckBox("Simulation mode")

        # pixel calibration metadata
        self.spinbox_pixel_xy_um = QtWidgets.QDoubleSpinBox()
        self.spinbox_pixel_z_um = QtWidgets.QDoubleSpinBox()
        self.checkbox_pixel_unshear_z = QtWidgets.QCheckBox("Unshear (stage +)")

        # GUI layouts
        self.layout = QtWidgets.QVBoxLayout(self)
        self.tab_camera.layout = QtWidgets.QGridLayout()
        self.tab_stage.layout = QtWidgets.QFormLayout()
        self.tab_lightsheet.layout = QtWidgets.QFormLayout()
        self.tab_defm.layout = QtWidgets.QFormLayout()
        self.tab_etl.layout = QtWidgets.QFormLayout()
        self.initUI()

        # Internal parameters
        self.param_init = None
        self.cam_handle = None
        self.cam_running = False
        self.n_frames_per_stack = None
        self.n_stacks_to_grab = None
        self.n_frames_to_grab = None
        self.n_angles = None
        self.file_save_running = False
        self.abort_pressed = False
        self.simulation_mode = False
        self.root_folder = config.saving['root_folder']
        self.dir_path = None
        self.file_path = None
        self.file_format = "HDF5"
        self.cam_exposure_ms = config.camera['exposure_ms']
        self.cam_last_image = None
        self.daqmx_task_AO_ls = None
        self.ls_active = False
        # Set up threads and signals
        # Live mode image display worker+thread:
        self.thread_live_mode = QtCore.QThread()
        self.worker_live_mode = LiveImagingWorker(self)
        self.worker_live_mode.moveToThread(self.thread_live_mode)
        self.thread_live_mode.started.connect(self.worker_live_mode.update)
        self.worker_live_mode.sig_finished.connect(self.thread_live_mode.quit)

        self.thread_saving_files = SavingStacksThread(self)
        self.thread_frame_grabbing = CameraFrameGrabbingThread(self, self.thread_saving_files)
        # stage scanning worker+thread:
        self.thread_stage_scanning = QtCore.QThread()
        self.worker_stage_scanning = StageScanningWorker(self)
        self.worker_stage_scanning.moveToThread(self.thread_stage_scanning)
        self.thread_stage_scanning.started.connect(self.worker_stage_scanning.scan)
        self.worker_stage_scanning.finished.connect(self.thread_stage_scanning.quit)

    def initUI(self):
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
        self.spinbox_ls_duration.setDecimals(1)
        self.spinbox_ls_duration.setSingleStep(0.1)
        self.spinbox_ls_duration.setFixedWidth(60)
        self.spinbox_ls_duration.setValue(config.lightsheet_generation['swipe_duration_ms'])

        self.spinbox_ls_galvo_offset0.setRange(-10, 10)
        self.spinbox_ls_galvo_offset0.setDecimals(2)
        self.spinbox_ls_galvo_offset0.setFixedWidth(80)
        self.spinbox_ls_galvo_offset0.setValue(config.lightsheet_generation['galvo_offset0_volts'])

        self.spinbox_ls_galvo_offset1.setRange(-10, 10)
        self.spinbox_ls_galvo_offset1.setDecimals(2)
        self.spinbox_ls_galvo_offset1.setFixedWidth(80)
        self.spinbox_ls_galvo_offset1.setValue(config.lightsheet_generation['galvo_offset1_volts'])

        self.spinbox_ls_galvo_amp0.setSingleStep(0.1)
        self.spinbox_ls_galvo_amp0.setRange(0, 10)
        self.spinbox_ls_galvo_amp0.setFixedWidth(60)
        self.spinbox_ls_galvo_amp0.setValue(config.lightsheet_generation['galvo_amp0_volts'])

        self.spinbox_ls_galvo_amp1.setSingleStep(0.1)
        self.spinbox_ls_galvo_amp1.setRange(0, 10)
        self.spinbox_ls_galvo_amp1.setFixedWidth(60)
        self.spinbox_ls_galvo_amp1.setValue(config.lightsheet_generation['galvo_amp1_volts'])

        self.spinbox_ls_laser_volts.setRange(0, config.lightsheet_generation['laser_max_volts'])
        self.spinbox_ls_laser_volts.setDecimals(2)
        self.spinbox_ls_laser_volts.setSingleStep(0.05)
        self.spinbox_ls_laser_volts.setFixedWidth(60)
        self.spinbox_ls_laser_volts.setValue(config.lightsheet_generation['laser_set_volts'])

        self.checkbox_ls_switch_automatically.setChecked(True)
        self.checkbox_ls_switch_automatically.setEnabled(True)

        self.combobox_ls_side.setFixedWidth(80)
        self.combobox_ls_side.addItem("Left")
        self.combobox_ls_side.addItem("Right")
        self.combobox_ls_side.setEnabled(False)

        self.combobox_ls_port.setFixedWidth(80)
        self.combobox_ls_port.addItems(self.detect_serial_ports())
        self.combobox_ls_port.setCurrentText(config.lightsheet_generation['arduino_switcher_port'])

        self.button_ls_activate.setFixedWidth(160)
        self.button_ls_activate.setStyleSheet('QPushButton {color: red;}')

        self.tab_lightsheet.layout.addRow("Swipe duration, ms", self.spinbox_ls_duration)
        self.tab_lightsheet.layout.addRow("L-arm galvo offset, V", self.spinbox_ls_galvo_offset0)
        self.tab_lightsheet.layout.addRow("R-arm galvo offset, V", self.spinbox_ls_galvo_offset1)
        self.tab_lightsheet.layout.addRow("L-arm galvo amplitude, V", self.spinbox_ls_galvo_amp0)
        self.tab_lightsheet.layout.addRow("R-arm galvo amplitude, V", self.spinbox_ls_galvo_amp1)
        self.tab_lightsheet.layout.addRow("Laser power ctrl, V", self.spinbox_ls_laser_volts)
        self.tab_lightsheet.layout.addRow("Illumination objective", self.combobox_ls_side)
        self.tab_lightsheet.layout.addRow(self.button_ls_activate)
        self.tab_lightsheet.layout.addRow(self.checkbox_ls_switch_automatically)
        self.tab_lightsheet.layout.addRow("Arduino COM port", self.combobox_ls_port)
        self.tab_lightsheet.setLayout(self.tab_lightsheet.layout)

        # Stage tab
        self.button_stage_connect.setFixedWidth(160)
        self.button_stage_connect.setStyleSheet('QPushButton {color: red;}')

        self.button_stage_pos_start.setFixedWidth(120)
        self.button_stage_pos_stop.setFixedWidth(120)
        self.label_stage_start_pos.setFixedWidth(60)
        self.label_stage_stop_pos.setFixedWidth(60)

        self.button_stage_start_scan.setFixedWidth(320)
        self.checkbox_stage_use_fixed_range.setChecked(True)

        self.spinbox_stage_speed_x.setValue(0.2)
        self.spinbox_stage_speed_x.setMinimum(0.01)
        self.spinbox_stage_speed_x.setFixedWidth(80)
        self.spinbox_stage_speed_x.setDecimals(4)
        self.spinbox_stage_speed_x.setEnabled(False)

        self.spinbox_stage_step_x.setValue(3.5)
        self.spinbox_stage_step_x.setMinimum(0.01)
        self.spinbox_stage_step_x.setFixedWidth(60)
        self.spinbox_stage_step_x.setSingleStep(0.1)

        self.spinbox_stage_n_cycles.setValue(3)
        self.spinbox_stage_n_cycles.setMinimum(1)
        self.spinbox_stage_n_cycles.setMaximum(1000)
        self.spinbox_stage_n_cycles.setFixedWidth(60)

        self.spinbox_stage_range_x.setValue(50)
        self.spinbox_stage_range_x.setFixedWidth(80)
        self.spinbox_stage_range_x.setDecimals(0)
        self.spinbox_stage_range_x.setSingleStep(1)
        self.spinbox_stage_range_x.setRange(1, 1000)

        self.combobox_stage_port.addItems(self.detect_serial_ports())
        self.combobox_stage_port.setCurrentText(config.stages['port'])
        self.combobox_stage_port.setFixedWidth(80)

        self.combobox_stage_scan_mode.addItems(['linear', 'discrete'])
        self.combobox_stage_scan_mode.setCurrentText('linear')
        self.combobox_stage_scan_mode.setFixedWidth(80)

        self.button_stage_x_move_right.setFixedWidth(80)
        self.button_stage_x_move_left.setFixedWidth(80)

        self.spinbox_stage_x_move_step.setValue(5)
        self.spinbox_stage_x_move_step.setFixedWidth(80)
        self.spinbox_stage_x_move_step.setRange(1, 500)

        layout_stage_start_stop = QtWidgets.QGridLayout()
        layout_stage_start_stop.addWidget(self.button_stage_pos_start, 0, 0)
        layout_stage_start_stop.addWidget(self.label_stage_start_pos, 0, 1)
        layout_stage_start_stop.addWidget(self.button_stage_pos_stop, 0, 3)
        layout_stage_start_stop.addWidget(self.label_stage_stop_pos, 0, 2)

        layout_manual_move = QtWidgets.QGridLayout()
        layout_manual_move.addWidget(self.button_stage_x_move_right, 0, 0)
        layout_manual_move.addWidget(self.button_stage_x_move_left, 0, 1)
        layout_manual_move.addWidget(self.spinbox_stage_x_move_step, 0, 2)

        self.tab_stage.layout.addRow(self.button_stage_connect)
        self.tab_stage.layout.addRow(self.combobox_stage_port)
        self.tab_stage.layout.addRow("Current position, mm:", self.label_stage_current_pos)
        self.tab_stage.layout.addRow("Stage scanning speed, mm/s", self.spinbox_stage_speed_x)
        self.tab_stage.layout.addRow("Trigger step, micron", self.spinbox_stage_step_x)
        self.tab_stage.layout.addRow(self.checkbox_stage_use_fixed_range, self.spinbox_stage_range_x)
        self.tab_stage.layout.addRow("Scanning cycles", self.spinbox_stage_n_cycles)
        self.tab_stage.layout.addRow("Scanning mode", self.combobox_stage_scan_mode)
        self.tab_stage.layout.addRow(layout_stage_start_stop)
        self.tab_stage.layout.addRow(layout_manual_move)
        self.tab_stage.layout.addRow(self.button_stage_start_scan)

        self.tab_stage.setLayout(self.tab_stage.layout)

        # CAMERA window
        self.cam_window = CameraWindow()
        self.cam_last_image = np.random.randint(100, 110, size=self.cam_window.cam_image_dims, dtype='uint16')
        self.cam_window.show()

        # log window
        self.text_log.setReadOnly(True)
        self.text_log.setMaximumHeight(120)
        self.text_log.setSizePolicy(QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Minimum,
                                                          QtWidgets.QSizePolicy.Minimum))
        # acquisition params
        self.button_cam_initialize.setFixedWidth(160)
        self.button_cam_acquire.setFixedWidth(160)
        self.button_cam_disconnect.setFixedWidth(160)
        self.button_cam_set_roi.setFixedWidth(160)
        self.spinbox_exposure_ms.setValue(config.camera['exposure_ms'])
        self.spinbox_exposure_ms.setFixedWidth(60)
        self.spinbox_exposure_ms.setSingleStep(0.1)
        self.spinbox_exposure_ms.setDecimals(1)

        self.spinbox_n_timepoints.setValue(1)
        self.spinbox_n_timepoints.setFixedWidth(60)
        self.spinbox_n_timepoints.setMaximum(10000)
        self.spinbox_n_timepoints.setMinimum(1)

        self.spinbox_frames_per_stack.setValue(40)
        self.spinbox_frames_per_stack.setFixedWidth(60)
        self.spinbox_frames_per_stack.setRange(1, 1000)

        self.spinbox_nangles.setValue(2)
        self.spinbox_nangles.setMinimum(1)
        self.spinbox_nangles.setFixedWidth(60)

        self.spinbox_vsize.setMaximum(self.cam_window.cam_sensor_dims[0])
        self.spinbox_vsize.setValue(400)
        self.spinbox_vsize.setMinimum(64)
        self.spinbox_vsize.setSingleStep(4)
        self.spinbox_vsize.setFixedWidth(60)

        self.label_cam_readout_time.setText("Readout time, ms: "
                                            + "{:2.1f}".format(self.cam_get_readout_time(self.spinbox_vsize.value())))

        layout_acquisition_col0 = QtWidgets.QFormLayout()
        layout_acquisition_col0.addRow("Exposure, ms:", self.spinbox_exposure_ms)
        layout_acquisition_col0.addRow("Images per stack:", self.spinbox_frames_per_stack)
        layout_acquisition_col0.addRow("Time points:", self.spinbox_n_timepoints)
        layout_acquisition_col0.addRow("n(angles):", self.spinbox_nangles)

        layout_acquisition_col1 = QtWidgets.QFormLayout()
        layout_acquisition_col1.addRow(self.button_cam_set_roi)
        layout_acquisition_col1.addRow("ROI vertical size", self.spinbox_vsize)
        layout_acquisition_col1.addRow(self.label_cam_readout_time)

        layout_acquisition = QtWidgets.QGridLayout()
        layout_acquisition.addLayout(layout_acquisition_col0, 0, 0)
        layout_acquisition.addLayout(layout_acquisition_col1, 0, 1)
        self.groupbox_acq_params.setLayout(layout_acquisition)

        # saving, layouts
        layout_saving = QtWidgets.QGridLayout()
        layout_files = QtWidgets.QFormLayout()
        layout_pixel_meta = QtWidgets.QFormLayout()
        layout_saving.addLayout(layout_files, 0, 0)
        layout_saving.addLayout(layout_pixel_meta, 0, 1)
        self.groupbox_saving.setLayout(layout_saving)

        # saving, widgets
        self.button_saveto.setFixedWidth(80)
        self.lineedit_experimentID.setAlignment(QtCore.Qt.AlignRight)
        self.lineedit_file_prefix.setAlignment(QtCore.Qt.AlignRight)
        self.combobox_file_format.setFixedWidth(80)
        self.combobox_file_format.addItem("HDF5")
        self.combobox_file_format.addItem("TIFF")

        layout_files.addRow("Root folder:", self.button_saveto)
        layout_files.addRow("Expt ID (subfolder)", self.lineedit_experimentID)
        layout_files.addRow("File prefix", self.lineedit_file_prefix)
        layout_files.addRow("Format", self.combobox_file_format)

        # pixel metadata
        self.spinbox_pixel_xy_um.setDecimals(5)
        self.spinbox_pixel_xy_um.setValue(config.microscope['pixel_size_um'])
        self.spinbox_pixel_z_um.setEnabled(False)
        self.spinbox_pixel_z_um.setDecimals(5)
        self.checkbox_pixel_unshear_z.setChecked(True)

        layout_pixel_meta.addRow("Pixel size (x,y), um", self.spinbox_pixel_xy_um)
        layout_pixel_meta.addRow("Step (z) from stage, um", self.spinbox_pixel_z_um)
        layout_pixel_meta.addRow(self.checkbox_pixel_unshear_z)

        # trigger IN
        self.checkbox_triggers_in.setChecked(config.camera['trig_in'])
        self.combobox_input_trig_mode.addItem("Normal", 1)
        self.combobox_input_trig_mode.addItem("Start", 6)
        self.combobox_input_trig_mode.setCurrentText(config.camera['trig_in_mode'])

        self.combobox_input_trig_source.addItem("internal")
        self.combobox_input_trig_source.addItem("external")
        self.combobox_input_trig_source.addItem("software")
        self.combobox_input_trig_source.addItem("master pulse")
        self.combobox_input_trig_source.setCurrentText(config.camera['trig_in_source'])

        self.combobox_input_trig_type.addItem("EDGE", 1)
        self.combobox_input_trig_type.addItem("LEVEL", 2)
        self.combobox_input_trig_type.addItem("SYNCREADOUT", 3)
        self.combobox_input_trig_type.setCurrentText(config.camera['trig_in_type'])

        self.combobox_mpulse_source.addItem("external")
        self.combobox_mpulse_source.addItem("software")
        self.combobox_mpulse_source.setCurrentIndex(0)
        self.combobox_mpulse_source.setEnabled(False)

        self.combobox_mpulse_mode.addItem("CONTINUOUS")
        self.combobox_mpulse_mode.addItem("START")
        self.combobox_mpulse_mode.addItem("BURST")
        self.combobox_mpulse_mode.setCurrentIndex(2)
        self.combobox_mpulse_mode.setEnabled(False)

        self.lineedit_mpulse_nbursts.setValidator(QtGui.QIntValidator())
        self.lineedit_mpulse_nbursts.setFixedWidth(100)
        self.lineedit_mpulse_nbursts.setAlignment(QtCore.Qt.AlignRight)
        self.lineedit_mpulse_nbursts.setEnabled(False)

        self.lineedit_mpulse_interval.setValidator(QtGui.QIntValidator())
        self.lineedit_mpulse_interval.setFixedWidth(100)
        self.lineedit_mpulse_interval.setAlignment(QtCore.Qt.AlignRight)
        self.lineedit_mpulse_interval.setEnabled(False)

        layout_triggering_in = QtWidgets.QFormLayout()
        layout_triggering_in.addRow(self.checkbox_triggers_in)
        layout_triggering_in.addRow("Trigger mode", self.combobox_input_trig_mode)
        layout_triggering_in.addRow("Trigger source", self.combobox_input_trig_source)
        layout_triggering_in.addRow("Trigger type", self.combobox_input_trig_type)
        layout_triggering_in.addRow("M.pulse source", self.combobox_mpulse_source)
        layout_triggering_in.addRow("M.pulse mode", self.combobox_mpulse_mode)
        layout_triggering_in.addRow("M.pulse bursts", self.lineedit_mpulse_nbursts)
        layout_triggering_in.addRow("M.pulse interval, ms", self.lineedit_mpulse_interval)

        # trigger OUT
        self.checkbox_triggers_out.setChecked(config.camera['trig_out'])
        self.combobox_output_trig_kind.addItem("LOW")
        self.combobox_output_trig_kind.addItem("EXPOSURE")
        self.combobox_output_trig_kind.addItem("PROGRAMMABLE")
        self.combobox_output_trig_kind.addItem("TRIGGER READY")
        self.combobox_output_trig_kind.addItem("HIGH")
        self.combobox_output_trig_kind.setCurrentText(config.camera['trig_out_kind'])

        self.lineedit_output_trig_period.setValidator(QtGui.QDoubleValidator())
        self.lineedit_output_trig_period.setFixedWidth(80)
        self.lineedit_output_trig_period.setAlignment(QtCore.Qt.AlignRight)
        self.lineedit_output_trig_period.setEnabled(False)

        self.combobox_output_trig_polarity.addItem("NEGATIVE")
        self.combobox_output_trig_polarity.addItem("POSITIVE")
        self.combobox_output_trig_polarity.setCurrentText("POSITIVE")

        self.combobox_output_trig_source.addItem("READOUT END", 2)
        self.combobox_output_trig_source.addItem("VSYNC", 3)
        self.combobox_output_trig_source.addItem("Master pulse", 6)
        self.combobox_output_trig_source.setCurrentText("Master pulse")
        self.combobox_output_trig_source.setEnabled(False)

        layout_triggering_out = QtWidgets.QFormLayout()
        layout_triggering_out.addRow(self.checkbox_triggers_out)
        layout_triggering_out.addRow("Trigger kind", self.combobox_output_trig_kind)
        layout_triggering_out.addRow("Trigger source", self.combobox_output_trig_source)
        layout_triggering_out.addRow("Trig. period, ms", self.lineedit_output_trig_period)
        layout_triggering_out.addRow("Trigger polarity", self.combobox_output_trig_polarity)

        layout_triggering = QtWidgets.QGridLayout()
        layout_triggering.addLayout(layout_triggering_in, 0, 0)
        layout_triggering.addLayout(layout_triggering_out, 0, 1)
        self.groupbox_triggering.setLayout(layout_triggering)

        # simulation?
        self.checkbox_simulation.setChecked(False)

        # global layout, first column
        self.tab_camera.layout.addWidget(self.checkbox_simulation, 0, 0)
        self.tab_camera.layout.addWidget(self.button_cam_initialize, 1, 0)
        self.tab_camera.layout.addWidget(self.button_cam_acquire, 2, 0)
        self.tab_camera.layout.addWidget(self.button_cam_disconnect, 3, 0)
        self.tab_camera.layout.addWidget(self.groupbox_acq_params, 4, 0)
        self.tab_camera.layout.addWidget(self.groupbox_triggering, 5, 0)
        self.tab_camera.layout.addWidget(self.groupbox_saving, 6, 0)
        # second column
        self.tab_camera.setLayout(self.tab_camera.layout)

        # global layout
        self.button_exit.setFixedWidth(120)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.button_exit)
        self.layout.addWidget(self.text_log)
        self.setLayout(self.layout)

        # Signals Camera control
        self.button_cam_initialize.clicked.connect(self.cam_initialize)
        self.button_exit.clicked.connect(self.button_exit_clicked)
        self.cam_window.button_cam_snap.clicked.connect(self.button_snap_clicked)
        self.cam_window.button_cam_live.clicked.connect(self.button_live_clicked)
        self.button_cam_acquire.clicked.connect(self.button_acquire_clicked)
        self.button_cam_disconnect.clicked.connect(self.cam_disconnect)
        self.button_cam_set_roi.clicked.connect(self.cam_set_roi)
        self.spinbox_vsize.valueChanged.connect(self.cam_update_readout_time)
        self.checkbox_simulation.stateChanged.connect(self.checkbox_simulation_changed)
        self.button_saveto.clicked.connect(self.button_saveto_clicked)
        self.combobox_file_format.currentTextChanged.connect(self.set_file_format)
        self.combobox_input_trig_source.currentTextChanged.connect(self.activate_input_trig_options)
        self.combobox_output_trig_kind.currentTextChanged.connect(self.activate_output_trig_options)

        # Signals Stage control
        self.button_stage_connect.clicked.connect(self.activate_stage)
        self.button_stage_x_move_right.clicked.connect(self.stage_x_move_right)
        self.button_stage_x_move_left.clicked.connect(self.stage_x_move_left)
        self.button_stage_pos_start.clicked.connect(self.stage_mark_start_pos)
        self.button_stage_pos_stop.clicked.connect(self.stage_mark_stop_pos)
        self.button_stage_start_scan.clicked.connect(self.stage_start_scan_thread)

        # Signals LS generation
        self.button_ls_activate.clicked.connect(self.activate_lightsheet)
        self.checkbox_ls_switch_automatically.stateChanged.connect(self.set_ls_switching)

        # gray-out currently inactive options
        self.activate_input_trig_options(self.combobox_input_trig_source.currentText())
        self.activate_output_trig_options(self.combobox_output_trig_kind.currentText())

        self.update_calculator()
        self.spinbox_stage_step_x.valueChanged.connect(self.update_calculator)
        self.spinbox_stage_range_x.valueChanged.connect(self.update_calculator)
        self.spinbox_exposure_ms.valueChanged.connect(self.update_calculator)
        self.spinbox_n_timepoints.valueChanged.connect(self.update_calculator)

    def stage_start_scan_thread(self):
        self.worker_stage_scanning.setup(self.serial_stage,
                                         self.spinbox_stage_n_cycles.value(),
                                         float(self.label_stage_start_pos.text()),
                                         float(self.label_stage_stop_pos.text()),
                                         self.spinbox_stage_speed_x.value(),
                                         0.001 * self.spinbox_stage_step_x.value(),
                                         scan_mode=self.combobox_stage_scan_mode.currentText())
        self.thread_stage_scanning.start()

    def stage_x_move_right(self):
        if self.serial_stage is not None:
            step = 0.001 * self.spinbox_stage_x_move_step.value()
            if config.stages['type'] == 'MHW':
                try:
                    self.serial_stage.write(('!mor x ' + str(step) + '\r').encode())
                    status = self.serial_stage.read_until(terminator=b'\r').decode('utf-8')
                    self.stage_update_curr_pos()
                except Exception as e:
                    self.log_update("error:" + str(e) + "\n")
            else:
                self.log_update("Please activate stage first\n")

    def stage_x_move_left(self):
        if self.serial_stage is not None:
            step = -0.001 * self.spinbox_stage_x_move_step.value()
            if config.stages['type'] == 'MHW':
                try:
                    self.serial_stage.write(('!mor x ' + str(step) + '\r').encode())
                    status = self.serial_stage.read_until(terminator=b'\r').decode('utf-8')
                    self.stage_update_curr_pos()
                except Exception as e:
                    self.log_update("error:" + str(e) + "\n")
            else:
                self.log_update("Please activate stage first\n")

    def stage_update_curr_pos(self):
        # update current position
        if self.serial_stage is not None:
            if config.stages['type'] == 'MHW':
                try:
                    self.serial_stage.write('?pos x\r'.encode())
                    status = self.serial_stage.read_until(terminator=b'\r').decode('utf-8')
                    self.label_stage_current_pos.setText(status)
                except Exception as e:
                    self.log_update("error:" + str(e) + "\n")
        else:
            self.log_update("Please activate stage first\n")

    def stage_mark_start_pos(self):
        if self.serial_stage is not None:
            if config.stages['type'] == 'MHW':
                try:
                    self.serial_stage.write('?pos x\r'.encode())
                    status = self.serial_stage.read_until(terminator=b'\r').decode('utf-8')
                    self.label_stage_start_pos.setText(status)
                except Exception as e:
                    self.log_update("error:" + str(e) + "\n")
        else:
            self.log_update("Please activate stage first\n")

    def stage_mark_stop_pos(self):
        if self.serial_stage is not None:
            if config.stages['type'] == 'MHW':
                if self.checkbox_stage_use_fixed_range.isChecked():
                    try:
                        start = float(self.label_stage_start_pos.text().strip())
                        stop = start + 0.001*self.spinbox_stage_range_x.value()
                        self.label_stage_stop_pos.setText(str(stop))
                    except Exception as e:
                        self.log_update("error:" + str(e) + "\n")
                else:
                    try:
                        self.serial_stage.write('?pos x\r'.encode())
                        status = self.serial_stage.read_until(terminator=b'\r').decode('utf-8')
                        self.label_stage_stop_pos.setText(status)
                    except Exception as e:
                        self.log_update("error:" + str(e) + "\n")
        else:
            self.log_update("Please activate stage first\n")

    def activate_stage(self):
        if self.serial_stage is None:
            try:
                self.serial_stage = serial.Serial(self.combobox_stage_port.currentText(),
                                                  config.stages['baudrate'],
                                                  timeout=5.0, write_timeout=0.02)
                if config.stages['type'] == 'MHW':
                    self.serial_stage.write('?version\r'.encode())
                    status = self.serial_stage.read_until(terminator=b'\r').decode('utf-8')
                    self.log_update('connected to stage ' + status)
                    self.serial_stage.write('!dim 9\r'.encode())
                    self.log_update('units mm/s; ')
                    # self.serial_stage.write('!extmode 1\r'.encode()) # is this necessary?
                    # self.log_update('extended mode; ')
                    self.serial_stage.write('!stout 4\r'.encode())
                    self.log_update('TRIGGER_OUT set; ')
                    self.serial_stage.write('!trig 0\r'.encode())  # Trigger should be globally disabled for the initial configuration and may     remain enabled afterwards, even if the !trigr parameters are modified
                    self.serial_stage.write('!trigm 7\r'.encode())
                    self.log_update('trigger mode 7; ')
                    self.serial_stage.write('!trigs 500\r'.encode())
                    self.log_update('trigger pulse duration set (500 us); ')
                    self.serial_stage.write('!triga x\r'.encode())
                    self.log_update('trigger axis X; ')
                    self.serial_stage.write('!scanmode 0\r'.encode())
                    self.log_update('scanmode 0 (default); ')
                    self.serial_stage.write('!autostatus 3\r'.encode())
                    self.log_update('autostatus 3; ')
                    self.serial_stage.write(('!accel x ' + str(config.stages['x_accel']) + '\r').encode())
                    self.log_update('acceleration (x) set; ')
                    self.serial_stage.write(('!secvel x ' + str(config.stages['x_speed_max']) + '\r').encode())
                    #self.serial_stage.write('?secvel x\r'.encode())
                    #status = self.serial_stage.read_until(terminator=b'\r').decode('utf-8')
                    #self.log_update('secure velocity (mm/s) limit ' + status + '\n')
                    self.stage_update_curr_pos()
                else:
                    self.log_update("Stage type unknown, please check config file\n")
                self.button_stage_connect.setText("Disconnect stage")
                self.button_stage_connect.setStyleSheet('QPushButton {color: blue;}')
            except Exception as e:
                self.log_update("Could not connect to stage:" + str(e) + "\n")
        else:
            try:
                self.serial_stage.close()
                self.serial_stage = None
                self.button_stage_connect.setText("Connect to stage")
                self.button_stage_connect.setStyleSheet('QPushButton {color: red;}')
                self.log_update("Stage disconnected\n")
            except Exception as e:
                self.log_update("Failed to disconnect stage:" + str(e) + "\n")

    def cam_update_readout_time(self):
        self.label_cam_readout_time.setText("Readout time, ms: "
                                            + "{:2.1f}".format(self.cam_get_readout_time(self.spinbox_vsize.value())))

    def cam_get_readout_time(self, vsize):
        """Compute the ROI readout time based on vertical extent of ROI
        (Hamamatsu Orca Flash 4.3).
        Assuming triggered Sync Readout mode.
        Parameters:
            vsize: int
                Number of rows in the ROI.
        Return:
            double, ROI readout time, ms.
        """
        h1 = 9.74436E-3  # 1-row readout time, ms
        return ((vsize / 2.0) + 5) * h1

    def cam_set_roi(self):
        if self.cam_handle is not None:
            self.cam_handle.setPropertyValue("subarray_mode", 2)  # 1 / OFF; 2 / ON
            cam_roi_h = self.spinbox_vsize.value()
            cam_voffset = int((self.cam_window.cam_sensor_dims[0] - cam_roi_h) / 2.0)
            img_voffset = int((self.cam_window.cam_image_dims[0] - cam_roi_h) / 2.0)
            self.cam_handle.setPropertyValue("subarray_vsize", cam_roi_h)
            self.cam_handle.setPropertyValue("subarray_vpos", cam_voffset)
            self.cam_window.cam_image_dims = (self.cam_handle.getPropertyValue("image_height")[0],
                                              self.cam_handle.getPropertyValue("image_width")[0])
            if (img_voffset >= 0) and (img_voffset + cam_roi_h < self.cam_last_image.shape[0]):
                new_image = self.cam_last_image[img_voffset:(img_voffset + cam_roi_h), :]
            else:
                new_image = np.random.randint(100, 110,
                                              size=(cam_roi_h, self.cam_window.cam_image_dims[1]),
                                              dtype='uint16')
            self.display_image(new_image, position=(0, cam_voffset))
            self.log_update("New image dimensions: " + str(self.cam_window.cam_image_dims) + ' \n')
            self.log_update("New vpos offset: " +
                            str(self.cam_handle.getPropertyValue("subarray_vpos")[0]) + ' \n')
        else:
            self.log_update("Camera is not initialized\n")

    def set_ls_switching(self):
        if self.checkbox_ls_switch_automatically.isChecked():
            self.combobox_ls_side.setEnabled(False)
        else:
            self.combobox_ls_side.setEnabled(True)

    def detect_serial_ports(self):
        ports = ['COM%s' % (i + 1) for i in range(256)]
        ports_available = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                ports_available.append(port)
            except (OSError, serial.SerialException):
                pass
        return ports_available

    def cam_disconnect(self):
        """Close the connection to camera"""
        if self.cam_handle is not None:
            self.cam_handle.shutdown()
            self.cam_handle = None
            self.log_update("Camera disconnected\n")
        else:
            self.log_update("Camera already disconnected\n")

    def activate_lightsheet(self):
        """Create and start DAQmx stask for cam-triggered light-sheet"""
        # connect to Arduino LS switcher
        if self.checkbox_ls_switch_automatically and (self.serial_ls is None):
            try:
                self.serial_ls = serial.Serial(self.combobox_ls_port.currentText(), 9600, timeout=2)
                self.serial_ls.write("?ver\n".encode())
                status = self.serial_ls.readline().decode('utf-8')
                self.log_update("connected to Arduino switcher, version:" + status + "\n")
            except Exception as e:
                self.log_update("Cannot connect to Arduino, error:" + str(e) + "\n")

        if not self.ls_active:
            self.ls_active = True
            self.create_daqmx_task()
            self.setup_lightsheet()
            self.button_ls_activate.setText("Inactivate light sheet")
            self.button_ls_activate.setStyleSheet('QPushButton {color: blue;}')
        else:
            self.ls_active = False
            self.cleanup_daqmx_task()
            self.button_ls_activate.setText("Activate light sheet")
            self.button_ls_activate.setStyleSheet('QPushButton {color: red;}')

    def create_daqmx_task(self):
        """Create the DAQmx task, but don't start it yet."""
        self.daqmx_task_AO_ls = pd.Task()
        min_voltage = - config.lightsheet_generation['laser_max_volts']
        max_voltage = config.lightsheet_generation['laser_max_volts']
        self.daqmx_task_AO_ls.CreateAOVoltageChan("/Dev1/ao0:1", "galvo-laser",
                                                  min_voltage, max_voltage, pd.DAQmx_Val_Volts, None)

    def cleanup_daqmx_task(self):
        """Stop and clear the DAQmx task"""
        self.daqmx_task_AO_ls.StopTask()
        self.daqmx_task_AO_ls.ClearTask()

    def setup_lightsheet(self):
        """Set up the lightsheet for L/R arm illumination.
        Stops, re-configures, and restarts the DAQmx task.
        """
        galvo_amplitudes = self.spinbox_ls_galvo_amp0.value(), self.spinbox_ls_galvo_amp1.value()
        ls_duration_ms = self.spinbox_ls_duration.value()
        ls_laser_volts = self.spinbox_ls_laser_volts.value()

        # Arduino-controlled arm switcher
        if self.serial_ls is not None:
            # automatic mode
            if self.checkbox_ls_switch_automatically.isChecked():
                galvo_offsets = (0, 0)
                i_arm = 0
                self.serial_ls.write(('n ' + str(self.spinbox_frames_per_stack.value()) + '\n').encode())
                self.serial_ls.write('reset\n'.encode())
                self.serial_ls.write(('v0 ' + str(self.spinbox_ls_galvo_offset0.value()) + '\n').encode())
                self.serial_ls.write(('v1 ' + str(self.spinbox_ls_galvo_offset1.value()) + '\n').encode())
            # fixed arm mode
            else:
                galvo_offsets = self.spinbox_ls_galvo_offset0.value(), self.spinbox_ls_galvo_offset1.value()
                i_arm = self.combobox_ls_side.currentIndex()
                self.serial_ls.write('n 10000\n'.encode())
                self.serial_ls.write('v0 0.0\n'.encode())
                self.serial_ls.write('v1 0.0\n'.encode())
                self.serial_ls.write('reset\n'.encode())
        else:
            self.log_update("Error: Arduino switcher is not connected\n")

        if self.daqmx_task_AO_ls is not None:
            ls.task_config(self.daqmx_task_AO_ls,
                           wf_duration_ms=ls_duration_ms,
                           galvo_offset_V=galvo_offsets[i_arm],
                           galvo_amplitude_V=galvo_amplitudes[i_arm],
                           laser_amplitude_V=ls_laser_volts,
                           galvo_inertia_ms=0.2)
        else:
            self.log_update("Light sheet is inactive\n")

    def update_calculator(self):
        # speed = (stepX) / (timing between steps, trigger-coupled to exposure)
        if self.spinbox_exposure_ms.value() != 0:
            stage_speed_x = self.spinbox_stage_step_x.value() / self.spinbox_exposure_ms.value()
            self.spinbox_stage_speed_x.setValue(stage_speed_x)

        if self.spinbox_n_timepoints.value() != 0:
            self.spinbox_stage_n_cycles.setValue(self.spinbox_n_timepoints.value())

        stage_step_x = self.spinbox_stage_speed_x.value() * self.spinbox_exposure_ms.value()
        self.spinbox_stage_step_x.setValue(stage_step_x)

        if self.spinbox_stage_speed_x.value() != 0:
            exposure_ms = self.spinbox_stage_step_x.value() / self.spinbox_stage_speed_x.value()
            self.spinbox_exposure_ms.setValue(exposure_ms)

        # n(trigger pulses, coupled to exposure) = (scan range) / (stepX)
        if self.spinbox_stage_step_x.value() != 0:
            n_triggers = int(self.spinbox_stage_range_x.value() / self.spinbox_stage_step_x.value())
            self.spinbox_frames_per_stack.setValue(n_triggers)
            self.spinbox_pixel_z_um.setValue(self.spinbox_stage_step_x.value() / np.sqrt(2))

    def log_update(self, message):
        self.text_log.insertPlainText(message)
        self.text_log.moveCursor(QtGui.QTextCursor.End)

    def cam_initialize(self):
        if self.simulation_mode:
            self.log_update("connected to Camera 0, model: BestCameraEver\n")
        else:
            if self.cam_handle is None:
                self.param_init = cam.DCAMAPI_INIT(0, 0, 0, 0, None, None)
                self.param_init.size = ctypes.sizeof(self.param_init)
                error_code = cam.dcam.dcamapi_init(cam.ctypes.byref(self.param_init))
                if error_code != cam.DCAMERR_NOERROR:
                    raise cam.DCAMException("DCAM initialization failed with error code " + str(error_code))
                n_cameras = self.param_init.iDeviceCount
                if n_cameras > 0:
                    self.cam_handle = cam.HamamatsuCamera(camera_id=0)
                    self.log_update("connected to Camera 0, model: "
                                    + str(self.cam_handle.getModelInfo(0)) + "\n")
                    self.setup_camera()
            else:
                self.log_update("Camera already initialized! \n")

    def checkbox_simulation_changed(self):
        if self.checkbox_simulation.checkState():
            self.simulation_mode = True
            self.log_update("camera in simulation mode\n")
        else:
            self.simulation_mode = False

    def setup_camera(self, debug_mode=False):
        self.cam_exposure_ms = self.spinbox_exposure_ms.value()
        if (not self.simulation_mode) and (self.cam_handle is not None):
            min_exposure_time = self.cam_handle.getPropertyValue("timing_readout_time")[0]
            if min_exposure_time <= self.cam_exposure_ms/1000.:
                self.cam_handle.setPropertyValue("exposure_time", self.cam_exposure_ms/1000.)
                self.cam_handle.setPropertyValue("readout_speed", 2)
                if debug_mode:
                    self.log_update("Camera exposure time, ms: " + str(self.cam_exposure_ms) + '\n')
                self.setup_triggers()
            else:
                self.abort_pressed = True
                self.log_update("Error: camera exposure time smaller than readout time, check values.\n")
        else:
            self.log_update("Camera handle empty\n")

    def button_exit_clicked(self):
        if self.cam_handle is not None:
            self.cam_handle.shutdown()
        if self.dev_dm.dev_handle is not None:
            self.dev_dm.disconnect()
        if self.serial_ls is not None:
            self.serial_ls.close()
        if self.serial_stage is not None:
            self.serial_stage.close()
        self.cam_window.close()
        self.close()

    def button_snap_clicked(self):
        self.setup_camera()
        if self.simulation_mode:
            self.cam_last_image = np.random.randint(100, 200,
                                                    size=self.cam_window.cam_image_dims,
                                                    dtype='uint16')
        elif self.cam_handle is not None:
            self.cam_handle.setACQMode("fixed_length", number_frames=1)
            self.cam_handle.startAcquisition()
            [frames, dims] = self.cam_handle.getFrames()
            self.cam_handle.stopAcquisition()
            if len(frames) > 0:
                self.cam_last_image = np.reshape(frames[0].getData().astype(np.uint16), dims)
            else:
                self.log_update("Camera buffer empty. ")
                self.cam_last_image = np.zeros(self.cam_window.cam_image_dims)
        else:
            self.log_update("Camera is not initialized\n")
            self.cam_last_image = np.random.randint(100, 200, size=self.cam_window.cam_image_dims, dtype='uint16')
        self.display_image(self.cam_last_image)

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
            self.log_update("(min, max): (" + str(image.min()) + "," + str(image.max()) + ")\n")

    def button_live_clicked(self):
        if not self.cam_running:
            self.cam_running = True
            self.thread_live_mode.start()
            self.cam_window.button_cam_live.setText("Stop")
            self.cam_window.button_cam_live.setStyleSheet('QPushButton {color: red;}')
        else:
            self.cam_running = False
            #self.thread_live_mode.wait()
            self.cam_window.button_cam_live.setText("Live")
            self.cam_window.button_cam_live.setStyleSheet('QPushButton {color: black;}')

    def button_acquire_clicked(self):
        '''
        Start camera acquisition and file saving
        '''
        self.check_path_valid()
        self.check_cam_initialized()
        # start acquisition
        if not self.abort_pressed and not self.cam_running and not self.file_save_running:
            self.cam_running = True
            self.button_acquire_reset()
            self.n_frames_per_stack = int(self.spinbox_frames_per_stack.value())
            self.n_stacks_to_grab = int(self.spinbox_n_timepoints.value() * self.spinbox_nangles.value())
            self.n_frames_to_grab = self.n_stacks_to_grab * self.n_frames_per_stack
            self.n_angles = int(self.spinbox_nangles.value())

            self.setup_camera()
            if self.ls_active:
                self.setup_lightsheet()
            self.thread_frame_grabbing.setup(self.n_frames_to_grab)
            self.thread_saving_files.setup(self.n_frames_to_grab, self.n_frames_per_stack, self.n_angles)

            self.thread_frame_grabbing.start()
            self.thread_saving_files.start()

            if not self.simulation_mode:
                self.cam_handle.setACQMode("run_till_abort")
        # If pressed DURING acquisition, abort acquisition and saving
        if self.cam_running and self.file_save_running:
            self.cam_running = False
            self.abort_pressed = True
            self.button_acquire_reset()
            self.thread_frame_grabbing.wait()
            self.thread_saving_files.wait()

    def check_cam_initialized(self):
        if self.cam_handle is None:
            self.log_update("Please initialize the camera.\n")
            self.abort_pressed = True

    def check_path_valid(self):
        """Check folder name. Create new folder for acquisition.
        Abort if folder already exists. """
        if self.root_folder is None:
            self.log_update("Please specify root folder for data saving.\n")
            self.abort_pressed = True
        else:
            self.dir_path = self.root_folder + "/" + self.lineedit_experimentID.text()
            self.file_path = self.dir_path + "/" + self.lineedit_file_prefix.text()
            if os.path.exists(self.dir_path):
                self.log_update("Experiment subfolder already exists! Define new subfolder.\n")
                self.abort_pressed = True
            else:
                os.mkdir(self.dir_path)
                self.log_update("Experiment subfolder: " + self.dir_path + "\n")
                self.abort_pressed = False

    def button_acquire_reset(self):
        if not self.cam_running and not self.file_save_running:
            self.button_cam_acquire.setText("Acquire and save")
            self.button_cam_acquire.setStyleSheet('QPushButton {color: black;}')
        if not self.cam_running and self.file_save_running:
            self.button_cam_acquire.setText("Saving...")
            self.button_cam_acquire.setStyleSheet('QPushButton {color: blue;}')
        if self.cam_running:
            self.button_cam_acquire.setText("Abort")
            self.button_cam_acquire.setStyleSheet('QPushButton {color: red;}')

    def button_saveto_clicked(self):
        file_dialog = QtWidgets.QFileDialog()
        file_dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        folder = file_dialog.getExistingDirectory(self, "Save to folder", self.root_folder)
        if folder:
            self.root_folder = folder
            self.log_update("Root folder for saving: " + self.root_folder + "\n")

    def set_file_format(self, new_format):
        self.file_format = new_format

    def activate_input_trig_options(self, trigger_source):
        """Inactivate input trigger options that are not relevant to the current trigger source"""
        if trigger_source == "master pulse":
            m_pulse_enabled = True
        else:
            m_pulse_enabled = False
        self.combobox_mpulse_mode.setEnabled(m_pulse_enabled)
        self.combobox_mpulse_source.setEnabled(m_pulse_enabled)
        self.lineedit_mpulse_interval.setEnabled(m_pulse_enabled)
        self.lineedit_mpulse_nbursts.setEnabled(m_pulse_enabled)

    def activate_output_trig_options(self, trigger_kind):
        """Inactivate output trigger options that are not relevant to the current trigger source"""
        if trigger_kind == "PROGRAMMABLE":
            prog_enabled = True
        else:
            prog_enabled = False
        self.combobox_output_trig_source.setEnabled(prog_enabled)
        self.lineedit_output_trig_period.setEnabled(prog_enabled)

    def setup_triggers(self):
        """Orca-Flash4 specific triggering functions"""
        # Trigger IN
        if self.checkbox_triggers_in.isChecked():
            current_ind = self.combobox_input_trig_mode.currentIndex()
            # 1 - NORMAL, 6 - START
            self.cam_handle.setPropertyValue("trigger_mode",
                                             int(self.combobox_input_trig_mode.itemData(current_ind)))

            # 1 external, 2 software
            self.cam_handle.setPropertyValue("master_pulse_trigger_source",
                                         1 + self.combobox_mpulse_source.currentIndex())

            # 1 internal, 2 external, 3 software, 4 master pulse
            self.cam_handle.setPropertyValue("trigger_source",
                                             1 + self.combobox_input_trig_source.currentIndex())

            # 1 EDGE, 2 LEVEL, 3 SYNCREADOUT
            current_ind = self.combobox_input_trig_type.currentIndex()
            self.cam_handle.setPropertyValue("trigger_active", int(self.combobox_input_trig_type.itemData(current_ind)))

            # Master pulse, if necessary
            self.cam_handle.setPropertyValue("master_pulse_mode",
                                             1 + self.combobox_mpulse_mode.currentIndex())
                                            # 1 CONTINUOUS, 2 START, 3 BURST
            self.cam_handle.setPropertyValue("master_pulse_burst_times",
                                             int(self.lineedit_mpulse_nbursts.text()))
            self.cam_handle.setPropertyValue("master_pulse_interval",
                                             int(self.lineedit_mpulse_interval.text())/1000.)
            # self.log_update("IN trigger set. ")
        else:
            # reset to default values
            self.cam_handle.setPropertyValue("trigger_mode", 1)  # NORMAL / 1
            self.cam_handle.setPropertyValue("master_pulse_trigger_source", 2)  # SOFTWARE
            self.cam_handle.setPropertyValue("trigger_source", 1)  # INTERNAL
            self.cam_handle.setPropertyValue("trigger_active", 1)  # EDGE / 1
            self.cam_handle.setPropertyValue("master_pulse_mode", 1)  # CONTINUOUS /1
            self.cam_handle.setPropertyValue("master_pulse_burst_times", 1)
            self.cam_handle.setPropertyValue("master_pulse_interval", 0.1)
            # self.log_update("IN trigger default. ")

        # Trigger OUT
        if self.checkbox_triggers_out.isChecked():
            self.cam_handle.setPropertyValue("output_trigger_kind[0]",
                                             1 + self.combobox_output_trig_kind.currentIndex())
                                            # 1 LOW, 2 EXPOSURE, 3 PROGRAMABLE, 4 TRIGGER READY, 5 HIGH

            current_ind = self.combobox_output_trig_source.currentIndex()
            # 2 READOUT END, 3 VSYNC, 6 (master) TRIGGER
            self.cam_handle.setPropertyValue("output_trigger_source[0]",
                                             int(self.combobox_output_trig_source.itemData(current_ind)))
            # trigger duraion, s
            self.cam_handle.setPropertyValue("output_trigger_period[0]",
                                             int(self.lineedit_output_trig_period.text())/1000.)

            # 1 NEGATIVE, 2 POSITIVE
            self.cam_handle.setPropertyValue("output_trigger_polarity[0]",
                                             1 + self.combobox_output_trig_polarity.currentIndex())

        else:
            self.cam_handle.setPropertyValue("output_trigger_kind[0]", 2)
            self.cam_handle.setPropertyValue("output_trigger_source[0]", 2)
            self.cam_handle.setPropertyValue("output_trigger_period[0]", 0.001)
            self.cam_handle.setPropertyValue("output_trigger_polarity[0]", 2)
            # self.log_update("OUT trigger default.")


class LiveImagingWorker(QtCore.QObject):
    """
    Acquire one image at a time and display it.
    """
    sig_finished = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window

    @QtCore.pyqtSlot()
    def update(self):
        while self.main_window.cam_running:
            self.main_window.button_snap_clicked()
        self.sig_finished.emit()


class StageScanningWorker(QtCore.QObject):
    """
    Scan the stage multiple cycles. Proper use of QThread via worker object.
    """
    signal_log = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, camera_window):
        super().__init__()
        self.camera_window = camera_window
        self.serial_stage = None
        self.ncycles = None
        self.start_pos = None
        self.stop_pos = None
        self.speed = None
        self.trigger_step = None
        self.signal_log.connect(self.camera_window.log_update)
        self.scan_mode = None

    @QtCore.pyqtSlot()
    def setup(self, serial_stage, ncycles, start_pos, stop_pos, speed, trigger_step, scan_mode='linear'):
        """
        :param serial_stage:
        :param ncycles:
        :param start_pos:
        :param stop_pos:
        :param speed:
        :param trigger_step:
        :param scan_mode: str
            Scanning mode, 'linear' (default) for continuous motion, 'discrete', for stepwise motion.
        :return: None
        """
        self.serial_stage = serial_stage
        self.ncycles = ncycles
        self.start_pos = start_pos
        self.stop_pos = stop_pos
        self.speed = speed
        self.trigger_step = trigger_step
        self.scan_mode = scan_mode
        if self.serial_stage is not None:
            if config.stages['type'] == 'MHW':
                try:
                    self.serial_stage.write('!trig 0\r'.encode())  # disable global trigger
                    # go to start position
                    self.serial_stage.write(('!moa x ' + str(self.start_pos) + '\r').encode())
                    status = self.serial_stage.read(size=1)
                    # set axis velocity
                    self.serial_stage.write(('!vel x ' + str(self.speed) + '\r').encode())
                    # set trigger distance, um
                    self.serial_stage.write(('!trigd ' + str(self.trigger_step) + '\r').encode())
                    # fire one trigger pulse for camera frame readout
                    self.serial_stage.write('!trig 1\r'.encode())  # enable global trigger
                    self.serial_stage.write('!trigm 102\r!trigger\r'.encode()) # fire first trigger manually for camera exposure onset (Hamamatsu)
                    self.serial_stage.write('!trigm 7\r'.encode())  # reset trigger mode
                    # flush all buffers
                    self.serial_stage.reset_input_buffer()
                    self.serial_stage.reset_output_buffer()
                    self.signal_log.emit("stage setup():ok\n")
                except Exception as e:
                    self.signal_log.emit("error in stage worker setup():" + str(e) + "\n")
        else:
            self.signal_log.emit("Please activate stage first\n")

    @QtCore.pyqtSlot()
    def scan(self):
        if self.serial_stage is not None:
            if config.stages['type'] == 'MHW':
                try:
                    self.signal_log.emit("scanning started\n")
                    for i in range(self.ncycles):
                        if self.scan_mode == 'linear':
                            self.serial_stage.write(('!moa x ' + str(self.stop_pos) + '\r').encode())
                            status = self.serial_stage.read(size=1).decode('utf-8')
                            self.serial_stage.write(('!moa x ' + str(self.start_pos) + '\r').encode())
                            status = self.serial_stage.read(size=1).decode('utf-8')
                        elif self.scan_mode == 'discrete':
                            total_dist_mm = abs(self.stop_pos - self.start_pos)
                            n_intervals_per_scan = round(total_dist_mm / self.trigger_step)
                            # forward scan, n steps
                            for j in range(n_intervals_per_scan):
                                self.serial_stage.write(('!mor x ' + str(self.trigger_step) + '\r').encode())
                                status = self.serial_stage.read(size=1).decode('utf-8')
                            # backward scan, n steps
                            for j in range(n_intervals_per_scan):
                                self.serial_stage.write(('!mor x -' + str(self.trigger_step) + '\r').encode())
                                status = self.serial_stage.read(size=1).decode('utf-8')
                        else:
                            self.signal_log.emit("Unknown scan mode: must be linear or discrete.\n")
                    self.signal_log.emit("scanning finished\n")
                except Exception as e:
                    self.signal_log.emit("error in stage thread run():" + str(e) + "\n")
        else:
            self.signal_log.emit("Please activate stage first\n")
        self.finished.emit()

class CameraFrameGrabbingThread(QThread):
    """
    Grab images from the camera and save them into list.
    """
    signal_log = pyqtSignal(str)
    signal_GUI = pyqtSignal()
    signal_save_data = pyqtSignal(object)
    signal_display_image = pyqtSignal(object)

    def __init__(self, camera_window, saving_thread=None):
        super().__init__()
        self.camera_window = camera_window
        self.saving_thread = saving_thread
        self.signal_log.connect(self.camera_window.log_update)
        self.signal_GUI.connect(self.camera_window.button_acquire_reset)
        self.signal_display_image.connect(self.camera_window.display_image)
        self.gui_update_interval_s = 1.0

        if self.saving_thread is not None:
            self.signal_save_data.connect(self.saving_thread.append_new_data)
        self.n_frames_to_grab = None
        self.n_frames_grabbed = None

    def setup(self, n_frames_to_grab):
        self.n_frames_to_grab = n_frames_to_grab
        self.n_frames_grabbed = 0

    def __del__(self):
        self.wait()

    def run(self):
        if not self.camera_window.simulation_mode:
            self.camera_window.cam_handle.startAcquisition()
        self.signal_log.emit("Camera started\n")
        start_time = time.time()
        while self.camera_window.cam_running and (self.n_frames_grabbed < self.n_frames_to_grab):
            if self.camera_window.simulation_mode:
                self.n_frames_grabbed += 1
                sim_image_16bit = np.random.randint(100, 200,
                                                    size=self.cam_window.cam_image_dims[0]*self.cam_window.cam_image_dims[0],
                                                    dtype='uint16')
                frame_data = [sim_image_16bit]
                self.signal_save_data.emit(frame_data)
                self.signal_display_image.emit(np.reshape(frame_data, self.cam_window.cam_image_dims))
            else:
                [frames, dims] = self.camera_window.cam_handle.getFrames()
                self.n_frames_grabbed += len(frames)
                if len(frames) > 0:
                    frame_data = []
                    for frame in frames:
                        frame_data.append(frame.getData())
                    self.signal_save_data.emit(frame_data)
                    time_stamp = time.time()
                    if (time_stamp - start_time) >= self.gui_update_interval_s:
                        start_time = time.time()
                        self.signal_display_image.emit(np.reshape(frame_data[0], dims))
        # Clean up after the main cycle is done
        if not self.camera_window.simulation_mode:
            self.camera_window.cam_handle.stopAcquisition()

        self.camera_window.cam_running = False
        # self.signal_log.emit("Captured:" + str(self.n_frames_grabbed) + " frames \n")
        # self.signal_log.emit("FPS: " + "{:4.1f}".format(self.n_frames_grabbed / (end_time - start_time)) + "\n")
        self.signal_GUI.emit()


class SavingStacksThread(QThread):
    """
    Save stacks to files
    """
    signal_log = pyqtSignal(str)
    signal_GUI = pyqtSignal()

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.frames_to_save = None
        self.frames_per_stack = None
        self.n_angles = None
        self.frames_saved = None
        self.stack_counter = None
        self.angle_counter = None
        self.bdv_writer = None
        self.stack = None
        self.cam_image_dims = (None, None)
        self.frameQueue = deque([])
        self.signal_log.connect(self.main_window.log_update)
        self.signal_GUI.connect(self.main_window.button_acquire_reset)

    def __del__(self):
        self.wait()

    def setup(self, frames_to_save, frames_per_stack, n_angles):
        self.frames_to_save = frames_to_save
        self.frames_per_stack = frames_per_stack
        self.n_angles = n_angles
        self.frames_saved = 0
        self.stack_counter = 0
        self.angle_counter = 0
        self.cam_image_dims = self.main_window.cam_window.cam_image_dims
        self.stack = np.empty((frames_per_stack, self.cam_image_dims[0], self.cam_image_dims[1]), 'uint16')

    def append_new_data(self, obj_list):
        if len(obj_list) > 0:
            self.frameQueue.extend(obj_list)
        else:
            pass

    def run(self):
        self.main_window.file_save_running = True
        if self.main_window.file_format == "HDF5":
            self.bdv_writer = npy2bdv.BdvWriter(self.main_window.file_path + '.h5',
                                                nangles=self.n_angles,
                                                subsamp=((1, 1, 1),))
        elif self.main_window.file_format == "TIFF":
            pass

        while (self.frames_saved < self.frames_to_save) and not self.main_window.abort_pressed:
            if len(self.frameQueue) >= self.frames_per_stack:
                for iframe in range(self.frames_per_stack):
                    plane = self.frameQueue.popleft()
                    self.stack[iframe, :, :] = np.reshape(plane, self.cam_image_dims)
                    self.frames_saved += 1
                # print("stack#" + str(self.stack_counter))
                # print("frames_saved:" + str(self.frames_saved))
                # print("queue length:" + str(len(self.frameQueue)))
                self.signal_log.emit(".")
                if self.main_window.file_format == "HDF5":
                    z_anisotropy = self.main_window.spinbox_pixel_z_um.value() / \
                                   self.main_window.spinbox_pixel_xy_um.value()
                    affine_matrix = np.array(((1.0, 0.0, 0.0, 0.0),
                                              (0.0, 1.0, -z_anisotropy, 0.0),
                                              (0.0, 0.0, 1.0, 0.0)))
                    voxel_size = (config.microscope['pixel_size_um'],
                                  config.microscope['pixel_size_um'],
                                  self.main_window.spinbox_pixel_z_um.value())
                    self.bdv_writer.append_view(self.stack,
                                                time=int(self.stack_counter / self.n_angles),
                                                angle=self.angle_counter,
                                                m_affine=affine_matrix,
                                                name_affine="unshearing transformation",
                                                calibration=(1, 1, 1),
                                                voxel_size_xyz=voxel_size,
                                                exposure_time=self.main_window.cam_exposure_ms
                                                )
                elif self.main_window.file_format == "TIFF":
                    file_name = self.main_window.file_path + \
                                "_t{:05d}a{:01d}.tiff".format(self.stack_counter, self.angle_counter)
                    tifffile.imsave(file_name, self.stack)
                else:
                    self.signal_log.emit("unknown format:" + self.main_window.file_format + "\n")

                self.stack_counter += 1
                self.angle_counter = (self.angle_counter + 1) % self.n_angles
            else:
                self.msleep(10)
        # clean-up:
        if self.main_window.file_format == "HDF5":
            self.bdv_writer.write_xml_file(ntimes=int(self.stack_counter / self.n_angles),
                                           camera_name="Hamamatsu OrcaFlash 4.3")
            self.bdv_writer.close()
        elif self.main_window.file_format == "TIFF":
            pass
        self.frameQueue.clear()
        self.main_window.file_save_running = False
        self.signal_log.emit("Saved " + str(self.frames_saved) + " images in "
                             + str(self.stack_counter) + " stacks \n")
        self.signal_GUI.emit()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
