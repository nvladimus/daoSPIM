## daoSPIM control
The software provides GUI for microscope control:
- advanced camera control (input and output triggers, acq. modes), 
- light sheet generation via galvo scanning (NI DAQmx task configuration)
- stage scanning (with TTL pulses at defined spatial intervals)
- deformable mirror control (loading and applying commands from file)
- electrotunable lens control (manual offsetting the ETL power)
- streaming images into HDF5 file (Fiji/BigDataViewer flavor) at high speed (currently up to 60Hz)

Python 3.6

## Hardware requirements
 - PC with Windows 10, 64 bit.
 - camera Hamamatsu Orca Flash4.3.
 - NI DAQmx PCIe board with at least 2 AO channels for galvo and laser modulation (e.g. PCIe-6321).
 - XY stage from ASI (MS-2000 controller).
 - ETL Optotune EL-16-40-TC-VIS-5D-C.
 - deformable mirror ImagineOptics Mirao52e.

### Installation 
(optional) Create and activate local environment from the command line, to keep things tidy
```
C:\Users\user\daoSPIM> cd microscope_control
C:\Users\user\daoSPIM> python -m venv venv
C:\Users\user\daoSPIM> venv\Scripts\activate.bat
(venv) C:\Users\user\daoSPIM>
```
Install dependencies 
```
pip install --upgrade pip
pip install -r requirements.txt
```
Launch the program
```
python dao_spim_control.py
```

### GUI overview
![GUI](./images/GUI0.png)

### Design principle
The code is still in development, but the author tried to keep it maximally modular and reusable. Each device is represented by a single file with GUI, controller and configuration code, independent from other devices. The main program file `dao_spim_control.py` connects these modules into a system. The GUI building is simplified by using a local library [widget.py](./src/widget.py) which takes care of PyQt5 low-level code.
See [device_template.py](./src/device_template.py) for example. 

The module files for these and other devices are independently available at [kekse](https://github.com/nvladimus/kekse) repo.

The camera control code was adapted from H.Babcock's [storm-control](https://github.com/ZhuangLab/storm-control/tree/master/storm_control/sc_hardware/hamamatsu) software.

