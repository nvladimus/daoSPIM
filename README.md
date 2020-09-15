# daoSPIM
**D**ual-view **a**daptive **o**ptics **s**elected **p**lane **i**llumination **m**icroscope makes multiview light-sheet microscopy compatible with microfluidic devices, by correcting optical aberrations with a deformable mirror (DM). Its unique optical design allows correcting aberrations in two arms with a single DM simultaneously.
![Optical layout: chamber](file:///images/ChamberOpticalLayout.png)

## Wiki
The Wiki pages describe microscope implementation:
* Optical and mechanical design 
* BOM
* CAD files for custom-made mechanical parts
* electronic wiring diagram 
* PCB design files for signal mixer (switching light-sheet between the arms)

## Microscope control software
The microscope is controlled via GUI program (Python Qt5) which links together:
- camera (Hamamatsu Orca Flash4.3)
- stage (ASI TE2000)
- light-sheet generator (based on NI PCIe-6321 DAQ board and a custom signal mixer)
- deformable mirror (ImagineOptics Mirao52e)
- electro-tunable lens (Optotune EL-16-40-TC-VIS-5D-C)

## DM optimization
DM is optimized in a separate Jupyter notebook. The light sheet is generated using the GUI program, and DM is optimized iteratively on a single bead image.
