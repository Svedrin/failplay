# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from __future__ import division

import sys
import ffmpeg
import ao

pcm = ao.AudioDevice("pulse")

rdr = ffmpeg.Decoder(sys.argv[-1])

from numpy import array, log10, sqrt
import struct
from scipy import fft
import audioop


from OpenGL import GL, GLUT

class OglRenderer( object ):
    def __init__( self, source, duration, width=250, height=100 ):
        self.source   = source
        self.duration = duration
        self.width    = width
        self.height   = height

        self.points = []

        GLUT.glutInit( sys.argv )
        GLUT.glutInitDisplayMode( GLUT.GLUT_DOUBLE )

        self.window = GLUT.glutCreateWindow( "fft!" )
        GLUT.glutReshapeWindow( width, height )

        GLUT.glutIdleFunc( self.idle )
        GLUT.glutDisplayFunc( self.display )

        self.framecount = 0


    def display( self ):
        GL.glClearColor( 1.0, 1.0, 1.0, 1.0 )
        GL.glClear( GL.GL_COLOR_BUFFER_BIT )

        GL.glMatrixMode( GL.GL_PROJECTION )
        GL.glLoadIdentity()
        GL.glOrtho( 0, self.width, 0, self.height, -1, 1 )

        GL.glLineWidth(3)
        GL.glBegin( GL.GL_LINE_STRIP )
        GL.glColor3f( 0.9, 0.3, 0.2 )
        plen = max(int(1 / float(self.width) * len(self.points)), 1)
        for x in xrange(self.width):
            pstart = int(x / self.width * len(self.points))
            prange = self.points[pstart:pstart + plen]
            # The log10(sqrt(prange) + 1.) part is totally ripped from Clementine. I don't
            # have any clue what it does, but it does make the thing look a whole lot nicer.
            # You do lose some detail because of it, though.
            # If you feel like explaining what the FHT::logSpectrum method defined in
            # <http://code.google.com/p/clementine-player/source/browse/src/core/fht.cpp>
            # actually does, drop me a mail at <i.am@svedr.in> - I'd appreciate it!
            GL.glVertex2i( x, int(max(log10(sqrt(prange) + 1.)) * self.height) )
        GL.glEnd()

        GLUT.glutSwapBuffers()

        self.framecount += 1


    def idle(self):
        try:
            chunk = self.source.next()
        except StopIteration:
            print "Frames:   %d"  % self.framecount
            print "Duration: %ds" % self.duration
            print "FPS:      %d"  % (self.framecount / self.duration)
            sys.exit(0)

        pcm.play( chunk[0] )

        if self.framecount % 3 != 0:
            self.display()
            return

        # Join the two streams into a single mono stream and convert it to a numpy array
        mono = audioop.tomono(chunk[0], 2, 0.5, 0.5)
        data = []
        while mono:
            data.append( struct.unpack("<h", mono[:2])[0] )
            mono = mono[2:]

        mono = array(data)

        # Perform a Fast Fourier Transform and scale the result
        # http://stackoverflow.com/questions/604453/analyze-audio-using-fast-fourier-transform

        # Increasing the length of the input stream will yield a more detailed graph.
        # Input is S16, so scale by 2**15 to get output coordinates in [0,1]
        y = fft(mono[:500] / float(2**15))
        n = 500 # len(mono)

        # Calculate the frequencies according to the FFT coefficients. They aren't being displayed
        # in this example, so it's commented out.
        #freqstep = self.source.samplerate / n
        #freq    = array(range(n/2)) * freqstep

        # The first half of the output array contains the fourier coefficients for our frequencies,
        # abs() calcs sqrt(i² + j²) to un-complex-numberfy them.
        self.points = abs(y[1:(n/2)])

        self.display()




renderer = OglRenderer(rdr.read(), rdr.duration)

GLUT.glutMainLoop()
