#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jun 25 11:27:45 2018

@author: ch20g13
"""

##### IMPORTS #####
from guizero import App,PushButton,Slider,Text,CheckBox
import numpy as np
import pyaudio
import wave
import scipy.io as sio
import scipy.signal as sig
import pdb

##### <<<<<<<<< VARIABLES >>>>>>>>> #####

audio_gain = 0
fs = 44100
output_index = 1 #2 for DVS
input_index = 3
output_channels = 2
frame_size = 2048
conv_flag = 0
no_conv_streams = 2

##### <<<<<<<<< LOAD AUDIO DATA >>>>>>>>> #####


# IR
mat_contents = sio.loadmat('l1_filters.mat')
ir = np.squeeze(mat_contents['L1_01'])

# Zero Pad IR to Length of Frame
if np.size(ir) > frame_size:
    raise ValueError('Frame size is smaller than length of filter. Please increase frame_size.')
ir = np.pad(ir, (0, frame_size-np.size(ir)), 'constant')



# Set Initial Convolution Overlaps to 0
conv_overlap = np.zeros((np.size(ir),no_conv_streams))


##### <<<<<<<<< FUNCTION DEFS >>>>>>>>> #####

# MAIN CALLBACK FUNCTION
def playingCallback(in_data, frame_count, time_info, status):

    audio_frame = np.fromstring(in_data,dtype=np.int16)  # Convert Bytes to Numpy Array

    # Uninterleave Inputs
    audio_frame = [audio_frame[idx::2] for idx in range(2)]
    audio_frame_c1 = audio_frame[0]
    audio_frame_c2 = audio_frame[1]

    print(audio_frame_c2)

    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AUDIO SIGNAL PROCESSING GOES IN HERE >>>>>>>>>>>>>>>>>>>>>>>>>>>


    # Apply Gains
    audio_frame_c1 = audio_frame_c1 * audio_gain
    audio_frame_c2 = audio_frame_c2 * audio_gain


    audio_frame_c1 = ch_realtime_convolution(audio_frame_c1,ir,1)
    audio_frame_c2 = ch_realtime_convolution(audio_frame_c2,ir,2)




    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<  END OF AUDIO SIGNAL PROCESSING   >>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Interleave Ouptuts 
    output = (audio_frame_c1,audio_frame_c2)
    output = np.vstack(output).reshape((-1,), order='F')

    out_data = output.astype(np.int16)
    out_data = out_data.tobytes()
    return out_data, pyaudio.paContinue


# DSP FUNCTIONS
def ch_realtime_convolution(x,h,ind): # x1 is signal, h is IR, ind is an index value corresponding to which set of overlap data should be used (which conv stream this is)

    global conv_overlap

    L = np.size(h) + np.size(x) - 1 # linear convolution length
    N = 1<<(L-1).bit_length()   # Get next power of 2 greater than L
    H = np.fft.fft( h, N ) # Fourier transform of IR (zero pad to N freq bins)
    X = np.fft.fft( x, N ) # Fourier transform of audio (zero pad to N freq bins)
    Y = H * X
    y = np.real(np.fft.ifft(Y,N))   # Return to Time Domain
    
    # Add Overlap Data from Previous Block (select correct data_set using the index argument)
    y[0:np.size(x)] = y[0:np.size(x)] + np.squeeze(conv_overlap[:,ind-1])
    
    # Save New Overlap Data for Next Block (select correct data_set using the index argument)
    conv_overlap[:,ind-1] = y[np.size(x):]

    # Remove Overlap from This Block
    y = y[0:frame_size]

    return y



# GUI FUNCTIONS
def push_play():
    stream.start_stream()


def push_stop():
    stream.stop_stream()


def change_gain():
    global audio_gain
    audio_gain = slider_gain.value/100


##### <<<<<<<<< SETUP AUDIO STREAM >>>>>>>>> #####
p = pyaudio.PyAudio()

stream = p.open(format = pyaudio.paInt16, channels = output_channels, rate = fs, output = True, input = True, stream_callback=playingCallback,output_device_index=output_index, input_device_index = input_index, frames_per_buffer=frame_size)
stream.stop_stream()


##### <<<<<<<<< CONFIGURE GUI >>>>>>>>> #####
playback_app = App(title="Playback App")
play_button = PushButton(playback_app,command=push_play,text="Play the Tune")
play_button = PushButton(playback_app,command=push_stop,text="Stop the Tune")
annotation = Text(playback_app,text="Adjust the Volume",size=20)
slider_gain = Slider(playback_app,command=change_gain)

playback_app.display()