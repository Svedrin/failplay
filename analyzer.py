# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from __future__ import division

from numpy import array, log10, sqrt
import struct
from scipy import fft
import audioop

from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui

class QFftAnalyzer( QtGui.QWidget ):
    def __init__( self, parent, columns=50 ):
        QtGui.QWidget.__init__(self, parent)
        self.points  = []
        self.columns = columns

    def paintEvent(self, evt):
        painter = QtGui.QPainter(self)
        painter.fillRect(evt.rect(), self.palette().color(QtGui.QPalette.Window))

        top    = evt.rect().top()
        left   = evt.rect().left()
        width  = evt.rect().width()
        height = evt.rect().height()
        plen = max(int(1 / float(width) * len(self.points)), 1)
        for x in xrange(width):
            pstart = int(x / width * len(self.points))
            prange = self.points[pstart:pstart + plen]
            thing = int(max(log10(sqrt(prange) + 1.)) * height)
            painter.drawLine( left + x, top + height, left + x, top + height - thing)

    def __call__(self, chunk):
        mono = audioop.tomono(chunk, 2, 0.5, 0.5)[:self.columns * 2 * 2 * 2]
        data = []
        while mono:
            data.append( struct.unpack("<h", mono[:2])[0] )
            mono = mono[2:]

        mono = array(data)
        #columns = min(len(mono) / 2, self.columns)
        y = fft(mono / float(2**15))

        self.points = abs(y[1:self.columns])
        self.update()
