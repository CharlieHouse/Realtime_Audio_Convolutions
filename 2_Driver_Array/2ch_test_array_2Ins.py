"""
________________________________________________
Dan Wallace (dw-ngcm)
2 channel modification for testing:

27 DRIVER GDP ARRAY CONVOLUTION ENGINE
University of Southampton
Institute of Sound and Vibration Research

Programmed by Charlie House - July 2018
Contact: c.house@soton.ac.uk
________________________________________________
This script takes a pair of mono input signals (defined on lines 36 and 37)
and convolves them each with 27 FIR filters to generate the signals for the
loudspeaker array. The FIR filters are stored in a pair of .mat files (one for
the listener left ear and one for the listener right ear, defined on lines
41 and 42), and when imported become dictionary objects. The key for each
filter is accessed in a for-loop on lines 52 and 53 - you will need to adjust
the exact details of this for loop to match how your filters are named.

The convolution is performed using the frequency domain overlap/save method for
maximum efficiency. The overlap samples are stored in the matrix conv_overlap,
which is indexed by samples in the first dimension and by convolution streams
in the second. The maximum number of simultaneous convolutions is defined in
line 38 by no_conv_streams, and defines the number of seperate overlap columns
this matrix needs to have.

GUIZero (a wrapper for TKInter) is used to generate a GUI for the end-user,
which enables the user to easily adjust the master output level (which defaults
 to 0) and to enable or disable the output stream.

NOTE: the final frame of the audio hasn't been zero padded to fill out the
frame, so this script may throw an error when it reaches the final frame and
attempts to index outside the bounds of the matrix. This is easily fixed,
but I haven't got around to it yet.

"""
##### IMPORTS #####
import sys
import os
import numpy as np
import pyaudio
import wave
import scipy.io as sio
import scipy.signal as sig

sys.path.append('../') # adds in guizero path
from guizero import App,PushButton,Slider,Text,CheckBox
from tkinter import filedialog

# Audio device selection
def selectDeviceIndex():
    '''Prints a list of audio devices to the screen and requests user input'''
    p = pyaudio.PyAudio()                   # initialise PyAudio
    n_devices = p.get_device_count()        # get number of devices exposed
    for dev in range(n_devices):            # receive info from each device
        info = p.get_device_info_by_index(dev)
        name = info['name']
        outCh = info['maxOutputChannels']
        print('{}: {} with {} output channels'.format(dev, name, outCh))
    print('')
    go = True
    while go:                               # Catch loop for input
        try:                                # Try validation to catch bad types
            selection = int(input('Select device: '))
            if selection < n_devices and selection >=0 : # catch invalid nos
                go = False
            else:
                print('Choose Again')
        except ValueError :
            print('Choose Again')
    return selection

def browseForFile(msg):
    '''Opens a file browser window with title message 'msg' as argument
    Returns path to chosen file.
    '''
    currdir = os.getcwd()
    tempdir = filedialog.askopenfile(initialdir=currdir, title=msg, filetypes = (('Array Config Files','*.cfg'),('all files','*.*')))
    return tempdir

def readConfigFile():
    file = browseForFile('Select Config File')
    if file.name[-3:] == 'cfg': # first validation
        lines = file.readlines()
        valid = [line for line in lines if line[0]!='#']
        ins = [line.strip() for line in valid if line.strip()[-3:] == 'wav']
        filters = [line.strip() for line in valid if line.strip()[-3:] == 'mat']
        assert len(ins) == len(filters)    # should be one to one mapping
        return ins, filters
##### <<<<<<<<< VARIABLES >>>>>>>>> #####

audio_gainL = 0     # Initial Gain
audio_gainR = 0
fs = 48000
output_index = selectDeviceIndex() # get output card from user
ins,filters = readConfigFile()

##### <<<<<<<<< LOAD AUDIO DATA >>>>>>>>> #####

# Main Audio Track
wf1 = wave.open(ins[0], 'rb')
wf2 = wave.open(ins[1], 'rb')

# Load IR Data
l_contents = sio.loadmat(filters[0])
r_contents = sio.loadmat(filters[1])

output_channels = 2
frame_size = 2048
no_conv_streams = output_channels*2  # two input audio streams


# Calculate FFT of IRs to Increase Performance in Callback Loop
L = 2048 + frame_size - 1 # linear convolution length
N = 1<<(L-1).bit_length()   # Get next power of 2 greater than L

fft_irs = np.array(np.zeros((2,output_channels,N),'complex'))
for i in range(1,output_channels+1):
    fft_irs[0,i-1,:] = np.fft.fft(np.squeeze(l_contents['L1_{}'.format(str(i).zfill(2))]),N)  # Load Dict of IRs into a Numpy Array
    fft_irs[1,i-1,:] = np.fft.fft(np.squeeze(r_contents['R1_{}'.format(str(i).zfill(2))]),N)  # Load Dict of IRs into a Numpy Array


# Set Initial Convolution Overlaps to 0
conv_overlap = np.zeros((frame_size,no_conv_streams))


##### <<<<<<<<< FUNCTION DEFS >>>>>>>>> #####

# MAIN CALLBACK FUNCTION
def playingCallback(in_data, frame_count, time_info, status):
    data_bytes1 = wf1.readframes(frame_count)
    data_bytes2 = wf2.readframes(frame_count)

    if len(data_bytes1) == 0 or len(data_bytes2) == 0:  # loop at end of wav
        wf1.rewind()
        wf2.rewind()

    # pre=create output buffer
    audio_frame_left = np.zeros(frame_size,)
    audio_frame_right = np.zeros(frame_size,)

    # read in data
    tempFrameLeft = np.frombuffer(data_bytes1,dtype=np.int16) # Convert Bytes to Numpy Array
    tempFrameRight =  np.frombuffer(data_bytes2,dtype=np.int16)

    # push data into audio frame
    audio_frame_left[:len(tempFrameLeft)] = tempFrameLeft
    audio_frame_right[:len(tempFrameRight)] = tempFrameRight

    # <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<< AUDIO SIGNAL PROCESSING GOES IN HERE >>>>>>>>>>>>>>>>>>>>>>>>>>>

    # Do Convolution
    output=[]
    for i in range(1,output_channels+1):   # Loop over all loudspeakers & convolve 2 input signals

        audio_left = ch_realtime_convolution(audio_frame_left,fft_irs[0,i-1,:],i) * audio_gainL/100
        audio_right = ch_realtime_convolution(audio_frame_right,fft_irs[1,i-1,:],2+i) * audio_gainR/100

        output_frame = audio_left + audio_right   # Sum contributions from both input signals to loudspeaker i
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


def change_gainL():
    global audio_gainL
    audio_gainL = slider_gainL.value/100

def change_gainR():
    global audio_gainR
    audio_gainR = slider_gainR.value/100



##### <<<<<<<<< SETUP AUDIO STREAM >>>>>>>>> #####
p = pyaudio.PyAudio()

stream = p.open(format = pyaudio.paInt16,
                channels = output_channels,
                rate = fs,
                output = True,
                stream_callback=playingCallback,
                output_device_index=output_index,
                frames_per_buffer=frame_size)
stream.stop_stream()


##### <<<<<<<<< CONFIGURE GUI >>>>>>>>> #####
playback_app = App(title="Playback App")
play_button = PushButton(playback_app,command=push_play,text="Start Playback")
play_button = PushButton(playback_app,command=push_stop,text="Stop Playback")
annotation = Text(playback_app,text="Adjust Input 1 Volume",size=20)
slider_gainL = Slider(playback_app,command=change_gainL)
annotation = Text(playback_app,text="Adjust Input 2 Volume",size=20)
slider_gainR = Slider(playback_app,command=change_gainR)

playback_app.display()
# after window closed, close the stream to free up audio device
stream.close()
