# Arm switcher
This is a small Teensy-powered PCB that counts camera pulses and adds a custom voltage bias to the input galvo system after every *N* pulses.

![PCB](./images/arm_switcher-PCB.JPG)

## Inputs
* camera pulses (digital)
* galvo voltage *g* (analog)

## Outputs
* analog signal *g + A* (during first *N* camera pulses), *g + B* (during next *N* pulses), then *g + A* again, etc. This goes directly to galvo controller.
* analog bias voltage alone *A* or *B* (for debugging).

## User-defined parameters:
   - camera pulse count *N* (>=1)
   - bias voltage *A, B* (-5 to +5 V)


## Setting parameters
Parameters are set via serial communication (baud rate 9600):
```
?ver #get the firmware version
n 10 #set switching period to 10 trigger pulses
?n #read the switching period
reset #reset the counter
v0 -0.45 #set voltage0 bias
v1 0.32 #set voltage1 bias
```

## Bill of materials
[Parts list](BOM.xls)