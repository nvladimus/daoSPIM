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
from PyQt5.uic import loadUi
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
from functools import partial
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
        self.frame_queue = deque([])
        # tabs
        self.tabs = QtWidgets.QTabWidget()
        self.tab_expt = QtWidgets.QWidget()
        self.tab_camera = QtWidgets.QWidget()
        self.tab_stage = QtWidgets.QWidget()
        self.tab_lightsheet = QtWidgets.QWidget()
        self.tab_defm = QtWidgets.QWidget()
        self.tab_etl = QtWidgets.QWidget()

        # experiment control
        self.gui_expt = loadUi("gui/experiment.ui")
        # deformable mirror widgets
        self.dev_dm = def_mirror.DmController(logger_name=self.logger.name + '.DM')
        # light-sheet widget
        self.ls_generator = lsg.LightsheetGenerator()
        # stage widgets
        self.dev_stage = stage.MotionController(logger_name=self.logger.name + '.stage')
        self.gui_stage = loadUi("gui/stage_scanning.ui")
        # camera widgets
        self.dev_cam = cam.CamController(logger_name=self.logger.name + '.camera')
        # ETL widget
        self.dev_etl = etl.ETL_controller(logger_name=self.logger.name + '.ETL')
        self.button_exit = QtWidgets.QPushButton('Exit')

        # GUI layouts
        self.layout = QtWidgets.QVBoxLayout(self)
        self.tab_expt.layout = QtWidgets.QFormLayout()
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
        self.plane_order = 'interleaved'
        self.file_format = "HDF5"
        # Set up threads and signals
        self.thread_live_mode = QtCore.QThread()
        self.worker_live_mode = LiveImagingWorker(self, self.dev_cam)
        self.worker_live_mode.moveToThread(self.thread_live_mode)
        self.thread_live_mode.started.connect(self.worker_live_mode.update)
        self.worker_live_mode.sig_finished.connect(self.thread_live_mode.quit)

        self.thread_saving_files = QtCore.QThread()
        self.worker_saving = SavingStacksWorker(self, self.dev_cam, self.logger, self.frame_queue)
        self.worker_saving.moveToThread(self.thread_saving_files)
        self.thread_saving_files.started.connect(self.worker_saving.run)
        self.worker_saving.sig_finished.connect(self.thread_saving_files.quit)

        self.thread_frame_grabbing = QtCore.QThread()
        self.worker_grabbing = CameraFrameGrabbingWorker(self, self.dev_cam, self.logger)
        self.worker_grabbing.moveToThread(self.thread_frame_grabbing)
        self.thread_frame_grabbing.started.connect(self.worker_grabbing.run)
        self.worker_grabbing.sig_save_data.connect(self.append_new_data)
        self.worker_grabbing.sig_finished.connect(self.thread_frame_grabbing.quit)

        self.thread_stage_scanning = QtCore.QThread()
        self.worker_stage_scanning = StageScanningWorker(self, self.logger)
        self.worker_stage_scanning.moveToThread(self.thread_stage_scanning)
        self.thread_stage_scanning.started.connect(self.worker_stage_scanning.scan)
        self.worker_stage_scanning.finished.connect(self.thread_stage_scanning.quit)

    def initUI(self):
        self.setLocale(QtCore.QLocale(QtCore.QLocale.English, QtCore.QLocale.UnitedStates))
        self.setWindowTitle("Microscope control")
        self.move(50, 50)
        # set up Tabs
        self.tabs.addTab(self.tab_expt, "Experiment")
        self.tabs.addTab(self.tab_camera, "Camera")
        self.tabs.addTab(self.tab_stage, "Stage")
        self.tabs.addTab(self.tab_lightsheet, "Light sheet")
        self.tabs.addTab(self.tab_defm, "Def. mirror")
        self.tabs.addTab(self.tab_etl, "ETL")
        # Experiment tab
        self.tab_expt.layout.addWidget(self.gui_expt)
        self.tab_expt.setLayout(self.tab_expt.layout)
        self.gui_expt.button_save_folder.setText(get_dirname(config.saving['root_folder']))
        # DM tab
        self.tab_defm.layout.addWidget(self.dev_dm.gui)
        self.tab_defm.setLayout(self.tab_defm.layout)
        # ETL tab
        self.tab_etl.layout.addWidget(self.dev_etl.gui)
        self.tab_etl.setLayout(self.tab_etl.layout)
        # LIGHTSHEET tab
        self.tab_lightsheet.layout.addWidget(self.ls_generator.gui)
        self.tab_lightsheet.setLayout(self.tab_lightsheet.layout)
        # Stage tab
        self.gui_stage.spinbox_stage_step_x.setValue(config.scanning['step_x_um'])
        self.tab_stage.layout.addWidget(self.dev_stage.gui)
        self.tab_stage.layout.addWidget(self.gui_stage)
        self.tab_stage.setLayout(self.tab_stage.layout)
        # Camera tab
        self.tab_camera.layout.addWidget(self.dev_cam.gui)
        self.tab_camera.setLayout(self.tab_camera.layout)

        # CAMERA window
        self.cam_window = CameraWindow(self)
        self.cam_window.show()

        # global layout
        self.button_exit.setFixedWidth(120)
        self.layout.addWidget(self.tabs)
        self.layout.addWidget(self.button_exit)
        self.setLayout(self.layout)

        # Signals experiment control
        self.gui_expt.button_cam_acquire.clicked.connect(self.button_acquire_clicked)
        self.gui_expt.button_save_folder.clicked.connect(self.button_save_folder_clicked)
        self.gui_expt.spinbox_n_timepoints.valueChanged.connect(self.update_calculator)
        self.gui_expt.combo_plane_order.currentIndexChanged.connect(self.set_plane_order)
        self.button_exit.clicked.connect(self.button_exit_clicked)
        # Signals Camera control
        self.cam_window.button_cam_snap.clicked.connect(self.button_snap_clicked)
        self.cam_window.button_cam_live.clicked.connect(self.button_live_clicked)
        self.dev_cam.gui.params['Exposure, ms'].editingFinished.connect(self.update_calculator)
        # Signals Stage control
        self.gui_stage.button_stage_x_move_right.clicked.connect(partial(self.stage_move, direction=(-1, 0)))
        self.gui_stage.button_stage_x_move_left.clicked.connect(partial(self.stage_move, direction=(1,0)))
        self.gui_stage.button_stage_y_move_up.clicked.connect(partial(self.stage_move, direction=(0,-1)))
        self.gui_stage.button_stage_y_move_down.clicked.connect(partial(self.stage_move, direction=(0,1)))
        self.gui_stage.button_stage_pos_start.clicked.connect(self.stage_mark_start_pos)
        self.gui_stage.button_stage_pos_stop.clicked.connect(self.stage_mark_stop_pos)
        self.gui_stage.button_stage_start_scan.clicked.connect(self.start_scan)
        self.gui_stage.button_set_center.clicked.connect(self.stage_setup_scan_range)
        self.gui_stage.spinbox_stage_step_x.valueChanged.connect(self.update_calculator)
        self.gui_stage.spinbox_stage_range_x.valueChanged.connect(self.update_calculator)

    def start_scan(self):
        self.stage_setup_scan_range()
        self.worker_stage_scanning.setup(self.dev_stage, self.n_stacks_to_grab)
        self.thread_stage_scanning.start()

    def stage_setup_scan_range(self):
        if self.dev_stage.initialized:
            self.dev_stage.get_position()
            if self.gui_stage.checkbox_scan_around.isChecked():
                x_range = self.gui_stage.spinbox_stage_range_x.value()
                y_range = self.gui_stage.spinbox_stage_range_y.value()
                xstart = self.dev_stage.position_x_mm - 0.001*x_range / 2
                xstop  = self.dev_stage.position_x_mm + 0.001*x_range / 2
                if y_range > config.microscope['FOV_y_um']:
                    ystart = self.dev_stage.position_y_mm - 0.001*y_range / 2
                    ystop  = self.dev_stage.position_y_mm + 0.001*y_range / 2
                else:
                    ystart = ystop = self.dev_stage.position_y_mm
                self.dev_stage.set_scan_region(xstart, scan_boundary='x_start')
                self.dev_stage.set_scan_region(xstop, scan_boundary='x_stop')
                self.dev_stage.set_scan_region(ystart, scan_boundary='y_start')
                self.dev_stage.set_scan_region(ystop, scan_boundary='y_stop')
        else:
            self.logger.error("Please activate stage first")

    def stage_move(self, direction=(1, 1)):
        if self.dev_stage.initialized:
            self.dev_stage.get_position()
            pos_x, pos_y = self.dev_stage.position_x_mm, self.dev_stage.position_y_mm
            new_x = pos_x + direction[0] * 0.001 * self.gui_stage.spinbox_stage_move_step.value()
            new_y = pos_y + direction[1] * 0.001 * self.gui_stage.spinbox_stage_move_step.value()
            self.dev_stage.move_abs((new_x, new_y))
        else:
            self.logger.error("Please activate stage first")

    def stage_mark_start_pos(self):
        if self.dev_stage.initialized:
            self.dev_stage.get_position()
            pos = self.dev_stage.position_x_mm
            self.dev_stage.set_scan_region(pos, scan_boundary='x_start')
        else:
            self.logger.error("Please activate stage first")

    def stage_mark_stop_pos(self):
        if self.dev_stage.initialized:
            self.dev_stage.get_position()
            pos = self.dev_stage.position_x_mm
            self.dev_stage.set_scan_region(pos, scan_boundary='x_stop')
        else:
            self.logger.error("Please activate stage first")

    def set_plane_order(self):
        if self.gui_expt.combo_plane_order.currentIndex() == 0:
            self.plane_order = 'interleaved'
        else:
            self.plane_order = 'sequential'
        self.logger.debug(f"Index {self.gui_expt.combo_plane_order.currentIndex()}, Plane order: {self.plane_order}")

    def update_calculator(self):
        # speed = (stepX) / (timing between steps, trigger-coupled to exposure)
        if self.dev_cam.exposure_ms != 0:
            stage_speed_x = self.gui_stage.spinbox_stage_step_x.value() / self.dev_cam.exposure_ms
            self.gui_stage.spinbox_stage_speed_x.setValue(stage_speed_x)

        if self.gui_expt.spinbox_n_timepoints.value() != 0:
            self.gui_stage.spinbox_stage_n_cycles.setValue(self.gui_expt.spinbox_n_timepoints.value())

        # feed the trigger interval to the stage settings
        if self.dev_stage.initialized:
            stage_step_x_mm = 0.001 * self.gui_stage.spinbox_stage_step_x.value()
            self.dev_stage.set_trigger_intervals(stage_step_x_mm, trigger_axis='X')
            self.dev_stage.set_speed(stage_speed_x, axis='X')

        if self.gui_stage.spinbox_stage_speed_x.value() != 0:
            exposure_ms = self.gui_stage.spinbox_stage_step_x.value() / self.gui_stage.spinbox_stage_speed_x.value()
            if self.dev_cam is not None:
                self.dev_cam.set_exposure(exposure_ms)

        # n(trigger pulses, coupled to exposure) = (scan range) / (stepX)
        if self.gui_stage.spinbox_stage_step_x.value() != 0:
            n_triggers = int(self.gui_stage.spinbox_stage_range_x.value() / self.gui_stage.spinbox_stage_step_x.value())
            self.gui_expt.spinbox_frames_per_stack.setValue(n_triggers)

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
            self.n_frames_per_stack = int(self.gui_expt.spinbox_frames_per_stack.value())
            self.n_stacks_to_grab = int(self.gui_expt.spinbox_n_timepoints.value() * self.gui_expt.spinbox_nangles.value())
            self.n_frames_to_grab = self.n_stacks_to_grab * self.n_frames_per_stack
            self.n_angles = int(self.gui_expt.spinbox_nangles.value())
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
        if self.dev_cam.status == 'Running' and self.file_save_running:
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
        self.dir_path = self.root_folder + "/" + self.gui_expt.line_subfolder.text()
        i_dir = 0
        while os.path.exists(self.dir_path + f'_v{i_dir}'): i_dir += 1
        self.dir_path += f'_v{i_dir}'
        os.mkdir(self.dir_path)
        self.file_path = self.dir_path + "/" + self.gui_expt.line_prefix.text()
        self.logger.info("Experiment folder: " + self.dir_path)

    def button_acquire_reset(self):
        if (not self.dev_cam.status == 'Running') and (not self.file_save_running):
            self.gui_expt.button_cam_acquire.setText("Acquire and save")
            self.gui_expt.button_cam_acquire.setStyleSheet('QPushButton {color: black;}')
        if (not self.dev_cam.status == 'Running') and self.file_save_running:
            self.gui_expt.button_cam_acquire.setText("Saving...")
            self.gui_expt.button_cam_acquire.setStyleSheet('QPushButton {color: blue;}')
        if self.dev_cam.status == 'Running':
            self.gui_expt.button_cam_acquire.setText("Abort")
            self.gui_expt.button_cam_acquire.setStyleSheet('QPushButton {color: red;}')

    def button_save_folder_clicked(self):
        file_dialog = QtWidgets.QFileDialog()
        file_dialog.setFileMode(QtWidgets.QFileDialog.Directory)
        folder = file_dialog.getExistingDirectory(self, "Save to folder", self.root_folder)
        if folder:
            self.root_folder = folder
            self.gui_expt.button_save_folder.setText(get_dirname(folder))
            self.logger.info("Root folder for saving: " + self.root_folder)


    @QtCore.pyqtSlot(object)
    def append_new_data(self, obj_list):
        if len(obj_list) > 0:
            #self.logger.debug(f"received {len(obj_list)}")
            self.frame_queue.extend(obj_list)
        else:
            pass


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
            time.sleep(0.2) # Todo: Replace with QTimer!!!
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
                time.sleep(0.05) # Todo: replace with Timer!!!
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
    sig_update_GUI = pyqtSignal()
    sig_save_data = pyqtSignal(object)
    sig_display_image = pyqtSignal(object)
    sig_finished = pyqtSignal()

    def __init__(self, parent_window, camera, logger):
        super().__init__()
        self.parent_window = parent_window
        self.camera = camera
        self.logger = logger
        self.sig_update_GUI.connect(self.parent_window.button_acquire_reset)
        self.sig_display_image.connect(self.parent_window.display_image)
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
        gui_update_time = time.time()
        fps_count_time = gui_update_time
        while (self.camera.status == 'Running') and (self.n_frames_grabbed < self.n_frames_to_grab):
            if self.camera.config['simulation']:
                self.n_frames_grabbed += 1
                sim_image_16bit = np.random.randint(100, 200, size=2048 * 2048, dtype='uint16')
                frame_data = [sim_image_16bit]
                self.sig_save_data.emit(frame_data)
                self.sig_display_image.emit(np.reshape(frame_data, self.camera.config['image_shape']))
            else:
                [frames, dims] = self.camera.dev_handle.getFrames()
                self.n_frames_grabbed += len(frames)
                if len(frames) > 0:
                    frame_data = []
                    for frame in frames:
                        frame_data.append(frame.getData())
                    self.sig_save_data.emit(frame_data)
                    time_stamp = time.time()
                    if (time_stamp - gui_update_time) >= self.gui_update_interval_s:
                        gui_update_time = time.time()
                        self.sig_display_image.emit(np.reshape(frame_data[0], dims))
        # Clean up after the main cycle is done
        if not self.camera.config['simulation']:
            self.camera.dev_handle.stopAcquisition()
            self.logger.debug(f"camera finished, mean fps {self.n_frames_to_grab/(time.time() - fps_count_time):2.1f}")
        self.camera.status = 'Idle'
        self.sig_update_GUI.emit()
        self.sig_finished.emit()


class SavingStacksWorker(QtCore.QObject):
    """
    Save stacks to files
    """
    sig_update_GUI = pyqtSignal()
    sig_finished = pyqtSignal()

    def __init__(self, parent_window, camera, logger, frame_queue):
        super().__init__()
        self.parent_window = parent_window
        self.camera = camera
        self.logger = logger
        self.frame_queue = frame_queue
        self.frames_to_save = self.frames_per_stack = self.n_angles = self.frame_counter = None
        self.stack_counter = self.angle_counter = self.bdv_writer = self.stack = self.cam_image_height = None
        self.sig_update_GUI.connect(self.parent_window.button_acquire_reset)

    def setup(self, frames_to_save, frames_per_stack, n_angles, image_height):
        self.frames_to_save = frames_to_save
        self.frames_per_stack = frames_per_stack
        self.n_angles = n_angles
        self.frame_counter = 0
        self.stack_counter = 0
        self.angle_counter = -1
        self.planes_interleaved = True if self.parent_window.plane_order == "interleaved" else False
        self.cam_image_height = image_height
        self.stack = np.empty((frames_per_stack, self.cam_image_height, 2048), 'uint16')
        if self.parent_window.file_format == "HDF5":
            self.bdv_writer = npy2bdv.BdvWriter(self.parent_window.file_path + '.h5',
                                                nangles=self.n_angles)
            z_voxel_size = self.parent_window.gui_stage.spinbox_stage_step_x.value() / np.sqrt(2)
            z_anisotropy = z_voxel_size / config.microscope['pixel_size_um']
            self.affine_matrix = np.array(((1.0, 0.0, 0.0, 0.0),
                                      (0.0, 1.0, -z_anisotropy, 0.0),
                                      (0.0, 0.0, 1.0, 0.0)))
            self.voxel_size = (config.microscope['pixel_size_um'], config.microscope['pixel_size_um'], z_voxel_size)
        elif self.parent_window.file_format == "TIFF":
            raise ValueError("TIFF support is deprecated")

    @QtCore.pyqtSlot()
    def run(self):
        self.parent_window.file_save_running = True
        while not self.parent_window.abort_pressed and self.frame_counter < self.frames_to_save:
            if len(self.frame_queue) > 0:
                plane = np.reshape(self.frame_queue.popleft(), (self.cam_image_height, 2048))
                if not self.planes_interleaved:  # planes are from L,L,L,L..., R,R,R,.. views
                    if self.frame_counter % self.frames_per_stack == 0:  # begin new stack
                        time_index = int(self.stack_counter / self.n_angles)
                        plane_index_L = plane_index_R = -1
                        self.angle_counter = (self.angle_counter + 1) % self.n_angles
                        self.stack_counter += 1
                        #print(f"Started new stack, time {time_index}, angle {self.angle_counter}")
                        self.bdv_writer.append_view(None,
                                                    virtual_stack_dim=(self.frames_per_stack, plane.shape[0], plane.shape[1]),
                                                    time=time_index,
                                                    angle=self.angle_counter,
                                                    m_affine=self.affine_matrix,
                                                    name_affine="unshearing transformation",
                                                    voxel_size_xyz=self.voxel_size,
                                                    exposure_time=self.camera.exposure_ms
                                                    )
                else:  # planes interleaved, from L, R, L, R, .. views
                    if self.frame_counter % (self.n_angles * self.frames_per_stack) == 0:  # begin 2 new stacks
                        time_index = int(self.stack_counter / self.n_angles)
                        plane_index_L = plane_index_R = -1
                        self.stack_counter += 2
                        for i_angle in range(self.n_angles):
                            self.bdv_writer.append_view(None,
                                                        virtual_stack_dim=(self.frames_per_stack, plane.shape[0], plane.shape[1]),
                                                        time=time_index,
                                                        angle=i_angle,
                                                        m_affine=self.affine_matrix, name_affine="unshearing",
                                                        voxel_size_xyz=self.voxel_size,
                                                        exposure_time=self.camera.exposure_ms
                                                        )
                    self.angle_counter = self.frame_counter % self.n_angles
                if self.angle_counter % 2 == 0:
                    plane_index_L += 1
                    plane_index = plane_index_L
                else:
                    plane_index_R += 1
                    plane_index = plane_index_R
                # print(f"Plane shape: {plane.shape}, angle counter {self.angle_counter}, time index {time_index}")
                self.bdv_writer.append_plane(plane, plane_index=plane_index, time=time_index, angle=self.angle_counter)
                self.frame_counter += 1
            else:
                time.sleep(0.02)  # Todo: Replace with QTimer
        # clean-up:
        self.bdv_writer.write_xml_file(ntimes=int(self.stack_counter / self.n_angles), camera_name="OrcaFlash 4.3")
        self.bdv_writer.close()
        self.frame_queue.clear()
        self.parent_window.file_save_running = False
        self.logger.info(f"Saved {self.frame_counter} images in {self.stack_counter} stacks with {self.n_angles} angles")
        self.sig_update_GUI.emit()
        self.sig_finished.emit()


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    app.exec_()
