import numpy as np
import PyDAQmx as pd
import ctypes as ct


def task_config(task, wf_duration_ms=50,
                   galvo_offset_V=0,
                   galvo_amplitude_V=1.0,
                   laser_amplitude_V=0.0,
                   galvo_inertia_ms=0.20):
    """Configuration and automatic restart of light-sheet generation DAQmx AO task.
    Channels:
        ao0, galvo
        ao1, laser
    Parameters:
        task, existing DAQmx AO task
        wf_duration_ms
        galvo_offset_V
        galvo_amplitude_V
        laser_amplitude_V.
        galvo_inertia_ms, delay in laser onset after galvo, to accomodate galvo inertia.
    """
    task.StopTask()
    sampleRate_Hz = 20000
    samples_per_ch = np.int(sampleRate_Hz/1000. * wf_duration_ms)
    task.CfgSampClkTiming("", sampleRate_Hz, pd.DAQmx_Val_Rising, pd.DAQmx_Val_FiniteSamps, samples_per_ch)

    task.CfgDigEdgeStartTrig("/Dev1/PFI0", pd.DAQmx_Val_Rising)
    task.SetTrigAttribute(pd.DAQmx_StartTrig_Retriggerable, True)
    
    # generate galvo AO waveform
    wf_galvo = np.zeros(samples_per_ch)
    wf_sawtooth = np.linspace(-galvo_amplitude_V/2.0, galvo_amplitude_V/2.0, samples_per_ch-2)
    # note that the last value of waveform should be zero or galvo_offset_V constant
    wf_galvo[1:-1] = wf_sawtooth
    wf_galvo = wf_galvo + galvo_offset_V
    # generate laser ON/OFF waveform
    wf_laser = np.zeros(samples_per_ch)
    laser_delay_samples = int(sampleRate_Hz/1000. * galvo_inertia_ms)
    wf_laser[laser_delay_samples:-1] = laser_amplitude_V  # laser wf must end with zero for safety reasons.
    # combine
    wform2D = np.column_stack((wf_galvo,wf_laser))
    # write to buffer
    samples_per_ch_ct = ct.c_int32()
    samples_per_ch_ct.value = samples_per_ch
    task.WriteAnalogF64(samples_per_ch, False, 10, pd.DAQmx_Val_GroupByScanNumber,
                        wform2D, ct.byref(samples_per_ch_ct), None)
    # restart the task
    task.StartTask()
