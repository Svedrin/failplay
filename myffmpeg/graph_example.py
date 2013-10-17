# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from __future__ import division

import sys
import ffmpeg

from numpy import sqrt
from time import time
from numpy import array
import struct
from scipy import fft
import audioop

from PIL import Image

width  = 1024
height = 768

source = ffmpeg.Decoder(sys.argv[-1])

image = Image.new("RGB", (width, height), "white")


print "reading infile..."
data = []
for chunk in source.read():
    mono = audioop.tomono(chunk[0], 2, 0.5, 0.5)
    while mono:
        data.append( struct.unpack("<h", mono[:2])[0] )
        mono = mono[2:]

print "done (len=%d). converting..." % len(data)

for x in xrange(width):
    monostart = int(x / width * len(data))
    monoend   = int((x + 1) / width * len(data))
    monorange = data[monostart:monoend]
    pixy = int(max(monorange) / 2**15 * height)
    for y in range(pixy):
        try:
            image.putpixel(( x, y ), 0)
        except IndexError, err:
            pass

print "done. saving..."
image.save("/tmp/test.jpg", "JPEG")

print "now go have a look at /tmp/test.jpg."
