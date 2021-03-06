"""
________________________________________________

27 DRIVER GDP ARRAY CONVOLUTION ENGINE
University of Southampton
Institute of Sound and Vibration Research

Programmed by Charlie House - July 2018
Contact: c.house@soton.ac.uk
________________________________________________
This script takes a pair of mono input signals (defined on lines 36 and 37) and convolves them each with 27 FIR filters to generate the signals for the
loudspeaker array. The FIR filters are stored in a pair of .mat files (one for the listener left ear and one for the listener right ear, defined on lines
41 and 42), and when imported become dictionary objects. The key for each filter is accessed in a for-loop on lines 52 and 53 - you will need to adjust
the exact details of this for loop to match how your filters are named.

The convolution is performed using the frequency domain overlap/save method for maximum efficiency. The overlap samples are stored in the matrix conv_overlap,
which is indexed by samples in the first dimension and by convolution streams in the second. The maximum number of simultaneous convolutions is defined in line
38 by no_conv_streams, and defines the numbe rof seperate overlap columns this matrix needs to have.

GUIZero (a wrapper for TKInter) is used to generate a GUI for the end-user, which enables the user to easily adjust the master output level (which defaults to 0)
and to enable or disable the output stream.

NOTE: the final frame of the audio hasn't been zero padded to fill out the frame, so this script may throw an error when it reaches the final frame and attempts
to index outside the bounds of the matrix. This is easily fixed, but I haven't got around to it yet.

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

audio_gain = 0     # Initial Gain
fs = 48000
output_index = 2    #2 for DVS
output_channels = 27
frame_size = 2048
no_conv_streams = 108

##### <<<<<<<<< LOAD AUDIO DATA >>>>>>>>> #####

# Main Audio Track
wf1 = wave.open("l1.wav", 'rb')
wf2 = wave.open("r1.wav", 'rb')

# Load IR Data
l_contents = sio.loadmat('l1_filters.mat')
r_contents = sio.loadmat('r1_filters.mat')


# Calculate FFT of IRs to Increase Performance in Callback Loop
L = 2048 + frame_size - 1 # linear convolution length
N = 1<<(L-1).bit_length()   # Get next power of 2 greater than L

fft_irs = np.array(np.zeros((2,27,N),'complex'))
for i in range(1,28):
    fft_irs[0,i-1,:] = np.fft.fft(np.squeeze(l_contents['L1_{}'.format(str(i).zfill(2))]),N)  # Load Dict of IRs into a Numpy Array
    fft_irs[1,i-1,:] = np.fft.fft(np.squeeze(r_contents['R1_{}'.format(str(i).zfill(2))]),N)  # Load Dict of IRs into a Numpy Array


# Set Initial Convolution Overlaps to 0
conv_overlap = np.zeros((frame_size,no_conv_streams))


##### <<<<<<<<< FUNCTION DEFS >>>>>>>>> #####

# MAIN CALLBACK FUNCTION
def playingCallback(in_data, frame_count, time_info, status):
    data_bytes1 = wf1.readframes(frame_count)  
    data_bytes2 = wf2.readframes(frame_count) 

    audio_frame_left = np.frombuffer(data_bytes1,dtype=np.int16)  # Convert Bytes to Numpy Array
    audio_frame_right = np.frombuffer(data_bytes2,dtype=np.int16)  # Convert Bytes to Numpy Array


    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AUDIO SIGNAL PROCESSING GOES IN HERE >>>>>>>>>>>>>>>>>>>>>>>>>>>

    # Do Convolution
    output=[]
    for i in range(1,28):   # Loop over all 27 loudspeakers & convolve 2 input signals

        audio_left = ch_realtime_convolution(audio_frame_left,fft_irs[0,i-1,:],i) * audio_gain/100
        audio_right = ch_realtime_convolution(audio_frame_right,fft_irs[1,i-1,:],27+i) * audio_gain/100

        output_frame = audio_left + audio_frame_right   # Sum contributions from both input signals to loudspeaker i
        output.append(output_frame)                     # Append to output vector
        
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


def change_gain():
    global audio_gain
    audio_gain = slider_gain.value/100



##### <<<<<<<<< SETUP AUDIO STREAM >>>>>>>>> #####
p = pyaudio.PyAudio()

stream = p.open(format = pyaudio.paInt16, channels = output_channels, rate = fs, output = True, stream_callback=playingCallback,output_device_index=output_index,frames_per_buffer=frame_size)
stream.stop_stream()


##### <<<<<<<<< CONFIGURE GUI >>>>>>>>> #####
playback_app = App(title="Playback App")
play_button = PushButton(playback_app,command=push_play,text="Start Playback")
play_button = PushButton(playback_app,command=push_stop,text="Stop Playback")
annotation = Text(playback_app,text="Adjust the Volume",size=20)
slider_gain = Slider(playback_app,command=change_gain)

playback_app.display()