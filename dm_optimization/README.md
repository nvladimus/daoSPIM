## Deformable mirror shape optimization 
[![Python 3.6](https://img.shields.io/badge/python-3.6-blue.svg)](https://www.python.org/downloads/release/python-360/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

### Software requirements
- Python 3.6, x64 (e.g. Anaconda)
- (optional) create and activate [local environment](/microscope_control#installation)
- Hamamatsu DCAM drivers
- Mirao52e dll drivers (x64)

### Hardware requirements
- PC with OS Windows 7/10
- camera Hamamatsu Orca4.3
- deformable mirror Mirao52e

### Sample requirements
- fluorescent bead resistant to bleaching,
- initial SNR is relatively high (ideally >10),
- only one fluorescent bead is present in the ROI, in both views,
- the bead is illuminated in wide-field or defocused light sheet mode. Using thin light sheet is discouraged to avoid light sheet walking off the bead (non-specific variation of the metric).

### Algorithm peculiarities
- the image metric is minimized;
- the gain grows in inverse proportion to the (decreasing) metric;
- the initial gain should be relatively small to avoid divergence (hopping on big bumps of the gradient);
- the algorithm tracks the position of a bead within the ROI and adjusts the ROI position if the bead drifts over time;
- the shape of DM is averaged between left and right halfs of the aperture, to add stability.

### Disclaimer
This notebook execution depends on particular hardware configuration and experimental conditions, and cannot be exactly reproduced. It was run several times after the original experiment in simulation mode to make the presentation more clear, so the cells are not numbered consecutively.