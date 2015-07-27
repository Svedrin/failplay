#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

"""
 *  Copyright (C) 2012, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 *
 *  This code is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This package is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
"""

from _ffmpeg import Decoder as LowLevelDecoder, Resampler, \
                    DecodeError, FileError, ResampleError, \
                    get_bytes_per_sample, get_sample_fmt_name, \
                    AV_SAMPLE_FMT_NONE, \
                    AV_SAMPLE_FMT_U8,  \
                    AV_SAMPLE_FMT_S16, \
                    AV_SAMPLE_FMT_S32, \
                    AV_SAMPLE_FMT_FLT, \
                    AV_SAMPLE_FMT_DBL, \
                    AV_SAMPLE_FMT_U8P,  \
                    AV_SAMPLE_FMT_S16P, \
                    AV_SAMPLE_FMT_S32P, \
                    AV_SAMPLE_FMT_FLTP, \
                    AV_SAMPLE_FMT_DBLP, \
                    AV_SAMPLE_FMT_NB,   \
                    AV_CH_LAYOUT_STEREO,   \
                    AV_CH_LAYOUT_2POINT1,  \
                    AV_CH_LAYOUT_2_1,      \
                    AV_CH_LAYOUT_SURROUND, \
                    AV_CH_LAYOUT_2_2,      \
                    AV_CH_LAYOUT_QUAD,     \
                    AV_CH_LAYOUT_STEREO_DOWNMIX


class Decoder(object):
    """ Python wrapper around the low level C module decoder.

            Decoder(fpath)

        It is used the same way as the C module:
        >>> import ao
        >>> pcm = ao.AudioDevice()
        >>> decoder = ffmpeg.Decoder('/path/to/some/file.ogg')
        >>> for chunk in decoder.read():
        ...     pcm.play( chunk )

        In contrast to the low level Decoder, this class's read() method makes
        sure to always return the requested number of bytes (except at EOF),
        even if that requires multiple low level read() calls.

        In addition to the properties that retrive information from the Decoder,
        the `position' property calculates the player's position in the file from
        the amount of bytes already retrieved using the read() method.
    """

    def __init__(self, fpath, want_samplerate=44100, want_samplefmt=AV_SAMPLE_FMT_S16):
        self._decoder = LowLevelDecoder(fpath.encode("utf-8"))
        self._buffer  = [""] * (self.channels if self.is_planar else 1)
        self._readbytes = 0

        if self.samplerate != want_samplerate or self.samplefmt != want_samplefmt:
            self.resampler = Resampler( output_rate=want_samplerate, input_rate=self.samplerate,
                output_sample_format=want_samplefmt, input_sample_format=self.samplefmt )
        else:
            self.resampler = None

    channels   = property( lambda self: self._decoder.get_channels(),   doc="The number of channels in the input stream." )
    channel_layout = property( lambda self: self._decoder.get_channel_layout(), doc="The channel layout of the input stream." )
    bitrate    = property( lambda self: self._decoder.get_bitrate(),    doc="The bitrate of the input channels." )
    duration   = property( lambda self: self._decoder.get_duration(),   doc="The length of the input stream in seconds." )
    path       = property( lambda self: self._decoder.get_path(),       doc="The input file path." )
    metadata   = property( lambda self: self._decoder.get_metadata(),   doc="Metadata from the input file's tags." )
    codec      = property( lambda self: self._decoder.get_codec(),      doc="The name of the codec used for the stream.")
    samplerate = property( lambda self: self._decoder.get_samplerate(), doc="The sample rate of the input stream." )
    samplefmt  = property( lambda self: self._decoder.get_samplefmt(),  doc="The sample format of the input stream." )

    @property
    def is_planar(self):
        return self.samplefmt in (AV_SAMPLE_FMT_U8P, AV_SAMPLE_FMT_S16P, AV_SAMPLE_FMT_S32P, AV_SAMPLE_FMT_FLTP, AV_SAMPLE_FMT_DBLP)

    @property
    def position(self):
        """ The player's position in the file in seconds. """
        # the  "* 2" should be "* self.channels", but since we always return mono
        # copied to stereo, mono bytes get counted twice, so it evens out.
        # this mono stuff sucks horribly...
        return self._readbytes / float(self.samplerate * 2 * get_bytes_per_sample(self.samplefmt))

    def read(self, bytes=4096):
        """ Get chunks of exactly ``bytes`` length. """
        while True:
            while len(self._buffer[0]) < bytes:
                try:
                    data = self._decoder.read()
                    if self.channels == 1:
                        # TODO: hartes Gepfusche
                        data = (data[0], data[0])
                    if self.resampler is not None:
                        data = self.resampler.resample(data)
                except StopIteration:
                    if self._buffer:
                        yield tuple(self._buffer)
                    raise StopIteration
                except DecodeError, err:
                    # Ignore DecodeErrors at the very beginning of the file
                    if self._readbytes or self.duration == 0:
                        raise err
                    else:
                        print "Ignoring DecodeError %s in file %s" % (err.message, self.path)
                else:
                    for idx, channeldata in enumerate(data):
                        self._buffer[idx] += channeldata
                        self._readbytes += len(channeldata)

            ret = []
            for idx, channeldata in enumerate(self._buffer):
                ret.append(channeldata[:bytes])
                self._buffer[idx] = channeldata[bytes:]

            yield tuple(ret)

    def dump_format(self):
        """ Dump input file format information to stdout. """
        self._decoder.dump_format()
