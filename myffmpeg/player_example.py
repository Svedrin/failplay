# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

# The most simple audio player in existance.

import sys
import ffmpeg
import ao

pcm = ao.AudioDevice("pulse")

rdr = ffmpeg.Decoder(sys.argv[-1])

for chunk in rdr.read():
    pcm.play( chunk[0] )
