# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import ffmpeg
import ao

pcm = ao.AudioDevice("pulse")

rdr = ffmpeg.Decoder(sys.argv[-1])

from numpy import sqrt
from time import time
from numpy import array
import struct
from scipy import fft
import audioop


from OpenGL.GL   import *
from OpenGL.GLUT import *

class OglRenderer( object ):
    def __init__( self, source, duration, width=1024, height=768 ):
        self.source   = source
        self.duration = duration
        self.width    = width
        self.height   = height

        self.points = []

        glutInit( sys.argv )
        glutInitDisplayMode( GLUT_DOUBLE )

        self.window = glutCreateWindow( "fft!" )
        glutReshapeWindow( width, height )

        glutIdleFunc( self.idle )

        self.framecount = 0


    def display( self ):
        glClearColor( 1.0, 1.0, 1.0, 1.0 )
        glClear( GL_COLOR_BUFFER_BIT )
        glColor3f( 0.0, 0.0, 0.0 )

        glMatrixMode( GL_PROJECTION )
        glLoadIdentity()
        glOrtho( 0, self.width, 0, self.height, -1, 1 )

        glColor3f( 0.0, 0.0, 0.0 )

        nbpoints = len(self.points) - 1

        glColor3f( 0.9, 0.3, 0.2 )
        glLineWidth(3);
        glBegin( GL_LINE_STRIP )
        glColor3f( 0.9, 0.3, 0.2 )
        for idx, pnt in enumerate(self.points):
            glVertex2i( int(idx / float(nbpoints) * self.width), int(pnt * self.height) )
        glColor3f( 0.9, 0.3, 0.2 )
        glEnd()

        glutSwapBuffers()

        self.framecount +=1


    def idle(self):
        try:
            chunk = self.source.next()
        except StopIteration:
            print "Frames:   %d"  % self.framecount
            print "Duration: %ds" % self.duration
            print "FPS:      %d"  % (self.framecount / self.duration)
            sys.exit(0)

        pcm.play( chunk )

        # Join the two streams into a single mono stream and convert it to a numpy array
        mono = audioop.tomono(chunk, 2, 0.5, 0.5)
        data = []
        while mono:
            data.append( struct.unpack("<h", mono[:2])[0] )
            mono = mono[2:]

        mono = array(data)

        # Perform a Fast Fourier Transform and scale the result
        # http://stackoverflow.com/questions/604453/analyze-audio-using-fast-fourier-transform

        # Increasing the length of the input stream will yield a more detailed graph.
        y = fft(mono[:64])
        n = 64. #len(mono)

        # Calculate the frequencies according to the FFT coefficients. They aren't being displayed
        # in this example, so it's commented out.
        #freqstep = self.source.samplerate / n
        #freq    = array(range(n/2)) * freqstep

        # Calculate the power as the absolute of the FFT coefficients scaled by 2**16 (arbitrarily).
        power   = sqrt(abs(y[1:(n/2)]) / float(2**16))

        self.points = power
        self.display()




renderer = OglRenderer(rdr.read(), rdr.duration)

glutMainLoop()
