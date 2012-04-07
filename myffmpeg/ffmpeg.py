#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from _ffmpeg import Decoder as LowLevelDecoder, DecodeError

class Decoder(object):
    def __init__(self, fpath, errignore=True):
        self._decoder = LowLevelDecoder(fpath)
        self._buffer  = ""
        self.errignore = errignore

    channels   = property( lambda self: self._decoder.get_channels() )
    bitrate    = property( lambda self: self._decoder.get_bitrate() )
    duration   = property( lambda self: self._decoder.get_duration() )
    path       = property( lambda self: self._decoder.get_path() )
    metadata   = property( lambda self: self._decoder.get_metadata() )
    codec      = property( lambda self: self._decoder.get_codec() )
    samplerate = property( lambda self: self._decoder.get_samplerate() )

    def read(self, bytes=4096):
        """ Get chunks of exactly ``bytes`` length. """
        while True:
            while len(self._buffer) < bytes:
                try:
                    self._buffer += self._decoder.read()
                except StopIteration:
                    if self._buffer:
                        yield self._buffer
                    raise StopIteration
                except DecodeError, err:
                    if not self.errignore:
                        raise err

            ret = self._buffer[:bytes]
            self._buffer = self._buffer[bytes:]
            yield ret

    def dump_format(self):
        self._decoder.dump_format()
