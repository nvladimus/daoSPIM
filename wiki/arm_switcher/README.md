# Arm switcher
This is a small Teensy-powered PCB that counts camera pulses and adds a user-defined voltage bias to the input signal after every *N* pulses. Designed to allow fast switching of light-sheet excitation laser (galvo) between left and right arms, to run in synch with camera. The software-based solution (eg in Python) would be too slow, hence this board.

![PCB](./images/arm_switcher.svg)

## Inputs
* camera exposure pulses *Trig_in* (digital)
* galvo voltage *g_in* (analog) that makes a swipe motion for light sheet generation.

## Output
* analog signal *g_in + V0* (during first *N* camera pulses), *g_in + V1* (during next *N* pulses), then *g_in + V0* again, etc. 
* (for debugging) analog bias voltage alone: *V0* or *V1* .

## User-defined parameters:
   - camera pulse count *N* (>=1)
   - bias voltage *V0, V1* (-5 to +5 V)


## Setting parameters
Parameters are set via serial communication (baud rate 9600):
```
?ver #get the firmware version
n 10 #set switching period to 10 trigger pulses
?n #read the switching period
reset #reset the counter
v0 -0.45 #set voltage0 bias, [Volt]
v1 0.32 #set voltage1 bias, [Volt]
```

## Bill of materials
[Parts list](BOM.xlsx)