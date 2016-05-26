# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import sys
import ffmpeg

rdr = ffmpeg.Decoder(sys.argv[-1])
rdr.dump_format()
