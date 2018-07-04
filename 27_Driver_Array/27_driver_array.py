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

audio_gain_left = 0
audio_gain_right = 0
fs = 48000
output_index = 2 #for DVS
input_index = 2
output_channels = 27
frame_size = 2048
no_conv_streams = 108

##### <<<<<<<<< LOAD AUDIO DATA >>>>>>>>> #####

# Main Audio Track
wf1 = wave.open("l1.wav", 'rb')
wf2 = wave.open("l2.wav", 'rb')
wf3 = wave.open("r1.wav", 'rb')
wf4 = wave.open("r2.wav", 'rb')

# Load IR Data
l1_ir_contents = sio.loadmat('l1_filters.mat')
l2_ir_contents = sio.loadmat('l2_filters.mat')
r1_ir_contents = sio.loadmat('r1_filters.mat')
r2_ir_contents = sio.loadmat('r2_filters.mat')


# Calculate FFT of IRs to Increase Performance in Callback Loop
L = 2048 + frame_size - 1 # linear convolution length
N = 1<<(L-1).bit_length()   # Get next power of 2 greater than L

fft_irs = np.array(np.zeros((4,27,N),'complex'))
for i in range(1,28):
    fft_irs[0,i-1,:] = np.fft.fft(np.squeeze(l1_ir_contents['L1_{}'.format(str(i).zfill(2))]),N)  # Load Dict of IRs into a Numpy Array
    fft_irs[1,i-1,:] = np.fft.fft(np.squeeze(l2_ir_contents['L2_{}'.format(str(i).zfill(2))]),N)  # Load Dict of IRs into a Numpy Array
    fft_irs[2,i-1,:] = np.fft.fft(np.squeeze(r1_ir_contents['R1_{}'.format(str(i).zfill(2))]),N)  # Load Dict of IRs into a Numpy Array
    fft_irs[3,i-1,:] = np.fft.fft(np.squeeze(r2_ir_contents['R2_{}'.format(str(i).zfill(2))]),N)  # Load Dict of IRs into a Numpy Array


# Set Initial Convolution Overlaps to 0
conv_overlap = np.zeros((frame_size,no_conv_streams))


##### <<<<<<<<< FUNCTION DEFS >>>>>>>>> #####

# MAIN CALLBACK FUNCTION
def playingCallback(in_data, frame_count, time_info, status):
    data_bytes1 = wf1.readframes(frame_count)  
    data_bytes2 = wf2.readframes(frame_count) 
    data_bytes3 = wf3.readframes(frame_count) 
    data_bytes4 = wf4.readframes(frame_count) 

    audio_frame_l1 = np.frombuffer(data_bytes1,dtype=np.int16)  # Convert Bytes to Numpy Array
    audio_frame_l2 = np.frombuffer(data_bytes2,dtype=np.int16)  # Convert Bytes to Numpy Array
    audio_frame_r1 = np.frombuffer(data_bytes3,dtype=np.int16)  # Convert Bytes to Numpy Array
    audio_frame_r2 = np.frombuffer(data_bytes4,dtype=np.int16)  # Convert Bytes to Numpy Array


    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AUDIO SIGNAL PROCESSING GOES IN HERE >>>>>>>>>>>>>>>>>>>>>>>>>>>

    # Do Convolution
    output=[]
    for i in range(1,28):

        audio_l1 = ch_realtime_convolution(audio_frame_l1,fft_irs[0,i-1,:],i) * audio_gain_left/100
        audio_l2 = ch_realtime_convolution(audio_frame_r1,fft_irs[1,i-1,:],27+i) * audio_gain_right/100
        audio_r1 = ch_realtime_convolution(audio_frame_l2,fft_irs[2,i-1,:],54+i) * audio_gain_left/100
        audio_r2 = ch_realtime_convolution(audio_frame_r2,fft_irs[3,i-1,:],81+i) * audio_gain_right/100

        output_frame = audio_l1 + audio_l2 + audio_r1 + audio_r2
        output.append(output_frame)
        
    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<  END OF AUDIO SIGNAL PROCESSING   >>>>>>>>>>>>>>>>>>>>>>>>>>>
    # Interleave Ouptuts 
    output = np.vstack(output).reshape((-1,), order='F')

    out_data = output.astype(np.int16)
    out_data = out_data.tobytes()
    return out_data, pyaudio.paContinue


# DSP FUNCTIONS
def ch_realtime_convolution(x,H,ind): # x1 is signal, h is IR, ind is an index value corresponding to which set of overlap data should be used (which conv stream this is)
    global N
    
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


def change_gain_left():
    global audio_gain_left
    audio_gain_left = slider_gain_left.value/100

def change_gain_right():
    global audio_gain_right
    audio_gain_right = slider_gain_right.value/100

##### <<<<<<<<< SETUP AUDIO STREAM >>>>>>>>> #####
p = pyaudio.PyAudio()

stream = p.open(format = pyaudio.paInt16, channels = output_channels, rate = fs, output = True, stream_callback=playingCallback,output_device_index=output_index,frames_per_buffer=frame_size)
stream.stop_stream()


##### <<<<<<<<< CONFIGURE GUI >>>>>>>>> #####
playback_app = App(title="Playback App")
play_button = PushButton(playback_app,command=push_play,text="Play the Tune")
play_button = PushButton(playback_app,command=push_stop,text="Stop the Tune")
annotation = Text(playback_app,text="Adjust the Volume",size=20)
slider_gain_left = Slider(playback_app,command=change_gain_left)
slider_gain_right = Slider(playback_app,command=change_gain_right)

playback_app.display()