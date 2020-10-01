# daoSPIM
**D**ual-view **a**daptive **o**ptics **s**elected **p**lane **i**llumination **m**icroscope makes multiview light-sheet microscopy compatible with microfluidic devices, by correcting optical aberrations with a deformable mirror (DM). Its unique optical design allows correcting aberrations in two arms with a single DM simultaneously.
![Optical layout: chamber](/wiki/images/ChamberOpticalLayout.png)

## Hardware overview
The [Wiki](https://github.com/nvladimus/daoSPIM/wiki) page provides a high-level system overview. 

The [/wiki](./wiki) folder contains implementation details:
* [BOM](./wiki/BOM.xlsx)
* [CAD](./wiki/custom_parts_cad) files for custom-made mechanical parts
* [PCB](./wiki/arm_switcher) design files for arm switcher board

## Microscope control software
The microscope is controlled via [GUI program](./microscope_control) which links together:
- camera (Hamamatsu Orca Flash4.3)
- stage (ASI MS-2000)
- light-sheet generator (based on NI PCIe-6321 DAQ board and arm switcher)
- deformable mirror (ImagineOptics Mirao52e)
- electro-tunable lens (Optotune EL-16-40-TC-VIS-5D-C)

DM is optimized in a separate Jupyter [notebook](./dm_optimization/) using a fluorescent bead image. The resulting DM command can be loaded in the GUI  [program](./microscope_control) and used thereafter.
