
import sys
import ao

pcm = ao.AudioDevice("pulse")

# svn checkout http://pyzic.googlecode.com/svn/trunk/libsndfile-ctypes/libsndfilectypes


import struct
import numpy as np
from libsndfilectypes.libsndfile import SndFile

sndf = SndFile(sys.argv[-1])

while(True):
	data, succ = sndf.read(4096, np.int16)
	datastr = ""
	for viech in data:
		datastr += struct.pack( "<hh", viech[0], viech[1] )
	pcm.play(datastr)

