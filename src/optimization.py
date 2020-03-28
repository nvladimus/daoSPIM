"""
Optimizer of deformable mirror shape, with GUI frontend.
by @nvladimus
"""

import numpy as np
import time
import scipy
from scipy.ndimage.filters import gaussian_filter
import scipy.optimize as opt
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import pyqtSignal


class SpgdOptimizer(QtCore.QObject):
    def __init__(self, camera, def_mirror):
        self.camera = camera
        self.def_mirror = def_mirror

def normL2(x):
    """L2 norm of array"""
    norm = np.sqrt(np.sum(x ** 2))
    return norm


def shannonEnt(x):
    """Normalized shannon entropy of a 2D array"""
    norm = normL2(x)
    xf = x.flatten()
    if (norm > 0):
        x_nonZero = xf[np.abs(xf) > 0]
        entropy = np.sum(np.abs(x_nonZero) / norm * np.log2(np.abs(x_nonZero) / norm))
        entropy = -2 * entropy / (x.shape[0] * x.shape[1])
    else:
        entropy = 0
    return entropy


def metric_shannon_DCT(img):
    """Shannon entropy of discreet cosyne transform, 2D"""
    from scipy.fftpack import dct
    if img.shape[1] > 0:
        img_dct1D = dct(img)
        img_dct2D = dct(img_dct1D)
        m = shannonEnt(img_dct2D)
    else:
        print('Error in metricShannonDCT(): image is not 2D')
        m = None
    return m


def metric_r_power_integral(img, integration_radius=20, power=2):
    """Metric of PSF quality based on integration of image(r) x r^2 over a circle of defined radius. 
    From Vorontsov, Shmalgausen, 1985 book. For best accuracy, img dimensions should be odd, with peak at the center.
    Parameters:
        img, a 2D image with PSF peak at the center
        integration_radius, for the circle of integration, default 20.
        background_subtract, value of camera offset (0 by default)
        """
    h, w = img.shape[0], img.shape[1]
    if np.min(img.shape) < 2 * integration_radius:
        raise ValueError("Radius too large for image size")
    else:
        # center = [int(w / 2), int(h / 2)]
        # center of mass center, does not tolerate > 1 beads in FOV!
        bg = np.percentile(img, 99)
        roi_binary = np.zeros(img.shape)
        roi_binary[img > bg] = 1
        cmass = scipy.ndimage.measurements.center_of_mass(roi_binary)
        x_center, y_center = cmass[1], cmass[0]
        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x + 0.5 - x_center) ** 2 + (y + 0.5 - y_center) ** 2)
        mask = (dist_from_center <= integration_radius).astype(int)
        metric = np.sum(img * mask * (dist_from_center ** power)) / np.sum(mask)
    return metric


def metric_MSE_gaussian(roi, peak_estimate='max', radius_sigmas=6.0, debug_mode=False):
    """
    Fit the blob in roi with a 2D Gaussian function and compute mean squared error (MSE)
    between roi and Gaussian fit.
    Parameters
    ----------
    roi, a 2D numpy array of normalized intensity values within [0,1]
    radius_sigmas, the radius of circle inside which SEM is calculated, in the units of Gaussian sigmas.
    """
    x = np.linspace(0, roi.shape[1] - 1, roi.shape[1]) + 0.5
    y = np.linspace(0, roi.shape[0] - 1, roi.shape[0]) + 0.5
    x, y = np.meshgrid(x, y)
    xcenter, ycenter, sigmaX, sigmaY, amp, offset = get_FWHM_gaussian_fit(roi, peak_estimate, debug_mode)
    mask_radius = 0.5 * (sigmaX + sigmaY) * radius_sigmas
    mask = create_circle_mask_non_concentric(roi, mask_radius, (ycenter, xcenter))
    gauss = twoD_gaussian_equal_sigmas((x, y), xcenter, ycenter, 0.5*(sigmaX + sigmaY), amp, offset).reshape(roi.shape)
    mse = np.sum(((gauss - roi) * mask)**2)/np.sum(mask)
    return mse


def metric_MAE_gaussian(roi, peak_estimate='max', radius_sigmas=6.0, debug_mode=False):
    """
    Fit the blob in roi with a 2D Gaussian function and compute mean absolute error (MAE)
    between roi and Gaussian fit.
    Parameters
    ----------
    roi, a 2D numpy array of normalized intensity values within [0,1]
    radius_sigmas, the radius of circle inside which SEM is calculated, in the units of Gaussian sigmas.
    """
    x = np.linspace(0, roi.shape[1] - 1, roi.shape[1]) + 0.5
    y = np.linspace(0, roi.shape[0] - 1, roi.shape[0]) + 0.5
    x, y = np.meshgrid(x, y)
    xcenter, ycenter, sigmaX, sigmaY, amp, offset = get_FWHM_gaussian_fit(roi, peak_estimate=peak_estimate, debug_mode=debug_mode)
    mask_radius = 0.5 * (sigmaX + sigmaY) * radius_sigmas
    mask = create_circle_mask_non_concentric(roi, mask_radius, (ycenter, xcenter))
    gauss = twoD_gaussian_equal_sigmas((x, y), xcenter, ycenter, 0.5*(sigmaX + sigmaY), amp, offset).reshape(roi.shape)
    mae = np.sum(np.abs((gauss - roi) * mask))/np.sum(mask)
    return mae


def twoD_gaussian_equal_sigmas(x_y, xo, yo, sigma, amplitude, offset):
    """"Compute FWHM using 2D Gaussian fit."""
    xo = float(xo)
    yo = float(yo)
    x, y = x_y
    g = offset + amplitude * np.exp(-(((x - xo) ** 2) / (2 * sigma ** 2) + ((y - yo) ** 2) / (2 * sigma ** 2)))
    return g.ravel()


def twoD_GaussianScaledAmp(x_y, xo, yo, sigma_x, sigma_y, amplitude, offset):
    """"Compute FWHM using 2D Gaussian fit."""
    xo = float(xo)
    yo = float(yo)
    x, y = x_y
    g = offset + amplitude * np.exp(- (((x - xo) ** 2) / (2 * sigma_x ** 2) + ((y - yo) ** 2) / (2 * sigma_y ** 2)))
    return g.ravel()


def get_FWHM_gaussian_fit(img, peak_estimate='max', debug_mode=False):
    """Get FWHM of a blob by 2D gaussian fitting. Requires normalization of image intensity to [0,1].
    Parameters
        peak_estimate: str
        if 'max', use the image maximum for gaussian origin guess, if 'center' use image center.
    Returns
        (xcenter, ycenter, sigmaX, sigmaY) in pixels.
    """
    x = np.linspace(0, img.shape[1] - 1, img.shape[1]) + 0.5
    y = np.linspace(0, img.shape[0] - 1, img.shape[0]) + 0.5
    x, y = np.meshgrid(x, y)
    # estimate the center position
    if peak_estimate == 'max':
        # use only center of the roi
        x_start, y_start = int(img.shape[1] * 0.25), int(img.shape[0] * 0.25)
        x_stop, y_stop = int(img.shape[1] * 0.75), int(img.shape[0] * 0.75)
        peak_val = img[y_start:y_stop, x_start:x_stop].max()
        max_ind_array = np.where(img[y_start:y_stop, x_start:x_stop] == peak_val)
        (y_peak, x_peak) = max_ind_array[0][0] + y_start, max_ind_array[1][0] + x_start
    elif peak_estimate == 'center':
        (y_peak, x_peak) = img.shape[0]/2, img.shape[1]/2
    else:
        print('Peak estimation method unknown\n')
    # Parameters: xpos, ypos, sigmaX, sigmaY
    initial_guess = (x_peak, y_peak, 1, 1, 1, 0)
    popt, pcov = opt.curve_fit(twoD_GaussianScaledAmp, (x, y),
                               img.ravel(), p0=initial_guess,
                               bounds=((img.shape[1] * 0.05, img.shape[0] * 0.05,
                                        0.1, 0.1,  # min sigmas
                                        0.8, -0.2),  # min amp, offset
                                       (img.shape[1] * 0.8, img.shape[0] * 0.8,
                                        img.shape[1] / 6., img.shape[0] / 6.,  # max sigmas
                                        1.2, 0.2)))  # max amp, offset
    xcenter, ycenter, sigmaX, sigmaY, amp, offset = popt
    if debug_mode:
        print('Fitted values: xcenter, ycenter, sigmaX, sigmaY, amp, offset:')
        print("{0:2.3f}".format(xcenter) + ',  ' + "{0:2.3f}".format(ycenter)
              + ",  {0:2.3f}".format(sigmaX) + ",  {0:2.3f}".format(sigmaY)
              + ",  {0:2.3f}".format(amp) + ",  {0:2.3f}".format(offset))
    return xcenter, ycenter, sigmaX, sigmaY, amp, offset


def sigma2fwhm(sigma):
    """Convert Gaussian sigma to FWHM:
        Parameters
            sigma: float
        Returns
            fwhm
        """
    return 4.0 * sigma * np.sqrt(-0.5 * np.log(0.5))


def metric_MSE_vs_simulated_PSF(img, metric_settings, scaling=100):
    """Mean square error of experimental PSF image vs simulated PSF image. Dimensions of images must match. 
    PSF maxima must be at the image center, +/- 1 px off center.
    Computed inside a circular region (diameter = img size)
    Parameters:
    img, test image, 2D ndarray
    img_simulated, simulated PSF image, 2D ndarray
    scaling: metric multiplication factor, to keep various metric comparable.
    Returns:
    mean square error between two images
    """
    img_simulated = metric_settings.ideal_PSF
    assert img.shape == img_simulated.shape, "Error: dimensions of two images must be equal"
    img_scaled = normalize_roi(img)
    # normalize simulated PSF differently, because it's noise-free:
    bg = np.percentile(img_simulated, 10)
    img_simulated_scaled = np.clip((img_simulated - bg) / (img_simulated.max() - bg), 0, 1)
    mask = create_circle_mask(img, np.min(img.shape) / 2.)
    diff2 = (mask * (img_scaled - img_simulated_scaled)) ** 2
    ave_diff2 = diff2.sum() / mask.sum() * scaling
    return ave_diff2


def normalize_roi(roi, bg_percentile=50.0, debug_mode=False):
    """
    Normalize input image (roi) to [0,1] between the defined (low) percentile and the maximum.

    Parameters
    ----------
    roi, ndrray of image (ROI)
    metric_settings, named tuple

    Returns
    ----------
    roi_normalized, ndarray of normalized ROI
    """
    assert len(roi.shape) == 2, "Error: ROI captured by camera must be 2D."
    bg = np.percentile(roi, bg_percentile)
    peak = roi.max()
    roi_normalized = (roi - bg)/(peak - bg)
    roi_normalized = np.clip(roi_normalized, 0, 1)
    if debug_mode:
        print('normalize_roi() values (low_percentile, background, peak):'
              + str(bg_percentile) + ',  ' + "{0:2.3f}".format(bg) + ',  ' + "{0:2.3f}".format(peak))
    return roi_normalized


def get_metric(roi, metric_settings):
    """
    Parameters
    ----------
    roi: array_like (2-d)
        Image for which metric must be computed.
    metric_settings: named tuple
        Parameters of the metric to compute.

    Returns
    ----------
    float64, metric of the input image.

    """
    assert len(roi.shape) == 2, "Error: ROI captured by camera must be 2D."
    if metric_settings.normalize_brightness:
        roi_normalized = normalize_roi(roi)
    else:
        roi_normalized = roi.astype(np.float64)

    if metric_settings.method1 == 'shannonDCT':
        m1 = metric_shannon_DCT(roi_normalized)
    elif metric_settings.method1 == 'FWHMxy':
        _, _, sigmaX, sigmaY, _, _ = get_FWHM_gaussian_fit(roi_normalized, peak_estimate=metric_settings.peak_estimate)
        fwhm_x, fwhm_y = sigma2fwhm(sigmaX), sigma2fwhm(sigmaY)
        m1 = metric_settings.weights_fwhm_xy[0] * fwhm_x + metric_settings.weights_fwhm_xy[1] * fwhm_y
    elif metric_settings.method1 == 'R2Integral':
        m1 = metric_r_power_integral(roi_normalized,
                                     integration_radius=metric_settings.r2_integration_radius,
                                     power=2)
    elif metric_settings.method1 == 'R4Integral':
        m1 = metric_r_power_integral(roi_normalized,
                                     integration_radius=metric_settings.r2_integration_radius,
                                     power=4)
    elif metric_settings.method1 == 'MSE_simulated':
        if metric_settings.ideal_PSF is None:
            raise ValueError("Error in snapROIGetMetric(): simulated image not available")
        else:
            assert roi_normalized.shape == metric_settings.ideal_PSF.shape, \
                "Error: ROI size must match ideal PSF image size"
            m1 = metric_MSE_vs_simulated_PSF(roi_normalized, metric_settings)
    else:
        raise ValueError('method1 metric name unknown')

    # add second metric, the result will be linear combination of 2 metrics:
    if metric_settings.method2 is None:
        m2 = 0
    elif metric_settings.method2 == 'MSE_simulated':
        assert roi_normalized.shape == metric_settings.ideal_PSF.shape, \
            "Error: ROI size must match ideal PSF image size"
        m2 = metric_MSE_vs_simulated_PSF(roi_normalized, metric_settings)
    elif metric_settings.method2 == 'R2Integral':
        m2 = metric_r_power_integral(roi_normalized,
                                     integration_radius=metric_settings.r2_integration_radius,
                                     power=2)
    elif metric_settings.method2 == 'MSE_gaussian':
        m2 = metric_MSE_gaussian(roi_normalized, peak_estimate=metric_settings.peak_estimate, radius_sigmas=5)
    elif metric_settings.method2 == 'MAE_gaussian':
        m2 = metric_MAE_gaussian(roi_normalized, peak_estimate=metric_settings.peak_estimate, radius_sigmas=5)
    else:
        raise ValueError('method2 metric name unknown')
    m = metric_settings.weights_method12[0] * m1 + metric_settings.weights_method12[1] * m2
    return m


def create_circle_mask(roi, radius):
    """
    Create binary circular mask inside square ROI, concentric to ROI.
    Parameters
    ----------
    roi: 2d ndarray, input image.
    radius: float64, mask radius.
    Returns
    -------
    ndarray of the mask (zeros and ones).
    """
    h, w = roi.shape[0], roi.shape[1]
    assert len(roi.shape) == 2, "Error: ROI must be a 2d array."
    if np.min(roi.shape) < 2 * radius:
        raise ValueError("Mask radius too large for ROI size")
    else:
        center = [int(w / 2), int(h / 2)]
        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x + 0.5 - center[0]) ** 2
                                   + (y + 0.5 - center[1]) ** 2)
        mask = (dist_from_center <= radius).astype(int)
    return mask


def create_circle_mask_non_concentric(roi, radius, center_yx):
    """
    Create binary circular mask inside square ROI, with a center at the specified position.
    Parameters
    ----------
    roi: 2d ndarray, input image.
    radius: float64, mask radius.
    center_yx: 2-element array-like of center coordinates, in pixels. First pixel position is (0.5, 0.5).
    Returns
    -------
    ndarray of the mask (zeros and ones).
    """
    assert len(center_yx) == 2, "Error: center coordinates must have 2 elements"
    assert len(roi.shape) == 2, "Error: ROI must be a 2d array."
    h, w = roi.shape[0], roi.shape[1]
    center_y_px, center_x_px = center_yx[0], center_yx[1]
    if (center_x_px < radius) or (center_y_px < radius) or (h - center_y_px < radius) or (w - center_x_px < radius):
        print("Mask radius (" + str(int(radius)) + ") too large for ROI size, will use maximum allowed radius")
        radius = min([radius, center_x_px, center_y_px, h - center_y_px, w - center_x_px])
    y, x = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((x + 0.5 - center_x_px) ** 2
                               + (y + 0.5 - center_y_px) ** 2)
    mask = (dist_from_center <= radius).astype(int)
    return mask


def snap_image(mmc=None, cam_handle=None):
    """"Get full-frame image from the camera
    Parameters
    ----------
    :param mmc: object
        Instance of MicroManager class. Deprecated, none by default.
    :param cam_handle: object
        Camera handle.
    Returns
    ----------
    image, a 2-d numpy array.
    """
    if mmc is not None:
        mmc.snapImage()
        image = mmc.getImage()
    elif cam_handle is not None:
        cam_handle.startAcquisition()
        [frames, dims] = cam_handle.getFrames()
        cam_handle.stopAcquisition()
        if len(frames) > 0:
            image = np.reshape(frames[0].getData().astype(np.uint16), dims)
        else:
            raise ValueError("Error in snap_image(): empty camera buffer\n")
    else:
        raise ValueError("Error in snap_image(): MM instance or camera handle must be defined.\n")

    return image


def get_roi(image, roi_center, roi_size, tracking=None, simulation_settings=None):
    """
    Parameters
    ----------
    :param image: ndarray
        full-frame camera image
    :param roi_center: tuple of int
        2-element tuple
    :param roi_size: tuple of int
        2-element tuple
    :param tracking: str or None
        algorithm for intensity peak tracking, 'xy', 'mass', or None.
    :param simulation_settings:
        namedtuple containing simulation parameters.
    Returns
    ----------
    (roi, roi_center): tuple
        roi, array-like 2D ROI.
        roi_center, (2,) tuple of center coordinates
         """
    assert len(roi_size) == 2, "Error: ROI must be 2D."
    if (simulation_settings is not None) and simulation_settings.on:
        roi = simulate_roi(roi_size, simulation_settings)
        roi_center_new = roi_center
    else:
        # note that image axes are in (y,x) order
        roi_old = image[int(roi_center[1] - roi_size[1] / 2): int(roi_center[1] + roi_size[1] / 2),
                        int(roi_center[0] - roi_size[0] / 2): int(roi_center[0] + roi_size[0] / 2)]
        if tracking is None:
            roi = roi_old
            x_peak = int(roi_center[0])
            y_peak = int(roi_center[1])
        elif tracking == 'xy':
            roi_old_denoised = gaussian_filter(roi_old, sigma=1)
            peak_val = roi_old_denoised.max()
            max_ind_array = np.where(roi_old_denoised == peak_val)
            (y_peak, x_peak) = max_ind_array[0][0], max_ind_array[1][0]
            x_peak += roi_center[0] - roi_size[0] / 2
            y_peak += roi_center[1] - roi_size[1] / 2
            roi = image[int(y_peak - roi_size[1] / 2): int(y_peak + roi_size[1] / 2),
                        int(x_peak - roi_size[0] / 2): int(x_peak + roi_size[0] / 2)]
        elif tracking == 'mass':
            bg = np.percentile(roi_old, 99)
            roi_binary = np.zeros(roi_old.shape)
            roi_binary[roi_old > bg] = 1
            cmass = scipy.ndimage.measurements.center_of_mass(roi_binary)
            x_peak = round(cmass[1]) + roi_center[0] - roi_size[0] / 2
            y_peak = round(cmass[0]) + roi_center[1] - roi_size[1] / 2
            roi = image[int(y_peak - roi_size[1] / 2): int(y_peak + roi_size[1] / 2),
                  int(x_peak - roi_size[0] / 2): int(x_peak + roi_size[0] / 2)]
        else:
            raise ValueError('Error: \'tracking\' argument unknown.')
        roi_center_new = (x_peak, y_peak)

    return roi, roi_center_new


def simulate_roi(roi_size, simulation_settings):
    """Simulate a ROI taken by the camera, with a bright gaussian spot in the center and random noise.
    :param roi_size: (2,) tuple of the ROI dimensions
    :param simulation_settings: named tuple
        structure-like named tuple containing the simulation papameters:
        .blob_fwhm_px: float, full width at half maximum (px)
        .snr: float, signal-to-noise ratio
        .center_offset_px: float, offset from center (px)

    :return: 2-dimensional ndarray, the simulated ROI image.
    """
    rs = np.random.RandomState()
    signal_amp = 1.0 + 0.2 * (2 * rs.rand() - 1)
    cam_offset = 100.
    amp_scaling = 1000.
    sigma_noise = signal_amp / simulation_settings.snr
    roi = rs.normal(0, sigma_noise, roi_size)
    x = np.linspace(0, roi_size[1] - 1, roi_size[1]) + 0.5
    y = np.linspace(0, roi_size[0] - 1, roi_size[0]) + 0.5
    x, y = np.meshgrid(x, y)
    x0, y0 = roi_size[1] / 2, roi_size[0] / 2
    if simulation_settings.center_offset_px > 0:
        x0 += simulation_settings.center_offset_px
        y0 -= simulation_settings.center_offset_px
    sigma_x = simulation_settings.blob_fwhm_px / (4 * np.sqrt(-0.5 * np.log(0.5)))
    sigma_y = sigma_x
    roi += signal_amp * np.exp(- (((x - x0) ** 2) / (2 * sigma_x ** 2) + ((y - y0) ** 2) / (2 * sigma_y ** 2)))
    roi *= amp_scaling
    roi += cam_offset
    return roi


def generate_actuator_mask(mask_type):
    if mask_type is None:
        mask = None
    elif mask_type == "outer_ring":
        actuator_IDs = np.array([1, 2, 3, 4, 5, 10, 11, 18, 19, 26, 27, 34, 35, 42, 43, 48, 49, 50, 51, 52]) - 1
        mask = np.zeros(52)
        mask[actuator_IDs] = 1
    elif mask_type == 'second_ring':
        actuator_IDs = np.array([6, 7, 8, 9, 17, 25, 33, 41, 12, 20, 28, 36, 44, 45, 46, 47]) - 1
        mask = np.zeros(52)
        mask[actuator_IDs] = 1
    else:
        mask = None
        print('Error: mask type is inknown \n')
    return mask


def wiggle_mirror_snap_rois_2views(cam_handle, defmirror, current_cmd, metric_settings,
                             run_settings, roi_center_left_view, roi_center_right_view, simulation):
    """Perturb current DM command randomly and update the command using Stochastic Parallel
    Gradient Descent.

    Parameters:
    """
    import ctypes as ct
    byref = ct.byref
    dm_trigger = ct.c_int32()
    dm_trigger.value = 0
    dm_status = ct.c_int32()
    dm_mask = generate_actuator_mask(run_settings.actuator_mask)
    delta_cmd_minus_array, delta_cmd_plus_array = generate_incremented_commands(current_cmd,
                                                                                run_settings.delta_cmd,
                                                                                dm_mask)
    # measure the gradient step
    if safe_voltage(delta_cmd_plus_array) and safe_voltage(delta_cmd_minus_array):
        if not simulation.on:
            defmirror.mro_applySmoothCommand(delta_cmd_plus_array.ctypes.data_as(ct.POINTER(ct.c_float)),
                                             dm_trigger, byref(dm_status))
            time.sleep(0.1)
            image = snap_image(cam_handle=cam_handle)
        else:
            image = np.random.rand(2048, 2048)
        roi_plus_Lv, __ = get_roi(image, roi_center_left_view,
                                  metric_settings.roi_size[0:2],
                                  metric_settings.tracking,
                                  simulation)

        roi_plus_Rv, __ = get_roi(image, roi_center_right_view,
                                  metric_settings.roi_size[0:2],
                                  metric_settings.tracking,
                                  simulation)
        if not simulation.on:
            defmirror.mro_applySmoothCommand(delta_cmd_minus_array.ctypes.data_as(ct.POINTER(ct.c_float)),
                                             dm_trigger, byref(dm_status))
            time.sleep(0.1)
            image = snap_image(cam_handle=cam_handle)
        else:
            image = np.random.rand(2048, 2048)

        roi_minus_Lv, __ = get_roi(image, roi_center_left_view,
                                metric_settings.roi_size[0:2],
                                metric_settings.tracking,
                                simulation)

        roi_minus_Rv, __ = get_roi(image, roi_center_right_view,
                                metric_settings.roi_size[0:2],
                                metric_settings.tracking,
                                simulation)
    else:
        raise ValueError('Voltage is outside of safe range. Skipped iteration.')

    delta_cmd_array = delta_cmd_plus_array - delta_cmd_minus_array
    return delta_cmd_array, roi_plus_Lv, roi_plus_Rv, roi_minus_Lv, roi_minus_Rv


def regularize_command(command, regularization, rate=0.25):
    """
    Parameters
    ---------------
    command: array_like
        Input command array.
    regularization: str or None
        Method of regularization, can be None, 'left_right_ave', 'radial_ave'
    rate: double, between [0, 0.5]
        Weight of averaging left/right for 'left_right_ave' method (default 0.25).
        Rate above 0.25 makes averaging between left and right faster:
        Right side commands of def. mirror: R_new = (1 - rate) * R_old + rate * R_old
        Left side commands of def. mirror: L_new = (1 - rate) * L_old + rate * L_old
    Returns
    ---------------
    array_like
        Regularized (averaged) command
    """
    actuatorIDsLeft = np.arange(0, 26)  # left side of DM, as pictured in the manual.
    actuatorIDsRight = np.array([49, 50, 51, 52,
                                 43, 44, 45, 46, 47, 48,
                                 35, 36, 37, 38, 39, 40, 41, 42,
                                 27, 28, 29, 30, 31, 32, 33, 34]) - 1  # right side of DM, mirror version of left side
    actuatorIDsRadiallySymmetricToLeft = np.array([52, 51, 50, 49,
                                                   48, 47, 46, 45, 44, 43,
                                                   42, 41, 40, 39, 38, 37, 36, 35,
                                                   34, 33, 32, 31, 30, 29, 28, 27]) - 1
    regularized_command = np.zeros(command.shape)
    if regularization is None:
        regularized_command = command
    elif regularization == 'left_right_ave':
        regularized_command[actuatorIDsRight] = (1 - rate) * command[actuatorIDsRight] \
                                                + rate * command[actuatorIDsLeft]
        regularized_command[actuatorIDsLeft] = (1 - rate) * command[actuatorIDsLeft] \
                                               + rate * command[actuatorIDsRight]
    elif regularization == 'radial_ave':
        regularized_command[actuatorIDsLeft] = 0.5 * (
                command[actuatorIDsLeft] + command[actuatorIDsRadiallySymmetricToLeft])
        regularized_command[actuatorIDsRadiallySymmetricToLeft] = regularized_command[actuatorIDsLeft]
    else:
        raise ValueError("argument regularization is unknown!")
    return regularized_command


def generate_incremented_commands(current_cmd, delta_cmd, actuator_mask):
    """

    Parameters
    ----------
    current_cmd: (array-like)
    delta_cmd: (float)
    actuator_mask: (array-like), contains 1 for actuators to be optimized, and 0 for all others.

    Returns
    -------

    """
    random_signs = np.sign(np.random.binomial(1, 0.5, size=len(current_cmd)) - 0.5)
    if actuator_mask is None:
        delta_cmd_plus_array = current_cmd + delta_cmd * random_signs
        delta_cmd_minus_array = current_cmd - delta_cmd * random_signs
    else:
        delta_cmd_plus_array = current_cmd + delta_cmd * random_signs * actuator_mask
        delta_cmd_minus_array = current_cmd - delta_cmd * random_signs * actuator_mask
    return delta_cmd_minus_array, delta_cmd_plus_array


def safe_voltage(cmd):
    """returns 1 if command data in the safe zone, between -1 and 1 Volt for individual actuators, and < 25 Volt sum of absolute values, \
     returns 0 if unsafe"""
    if cmd.min() >= -1.0 and cmd.max() <= 1.0 and np.sum(np.abs(cmd)) < 25.0:
        return 1
    else:
        return 0
