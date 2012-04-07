#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from _ffmpeg import Decoder as LowLevelDecoder, DecodeError

class Decoder(object):
    """ Python wrapper around the low level C module decoder.

            Decoder(fpath, errignore=True)

        It is used the same way as the C module:
        >>> import ao
        >>> pcm = ao.AudioDevice()
        >>> decoder = ffmpeg.Decoder('/path/to/some/file.ogg')
        >>> for chunk in decoder.read():
        ...     pcm.play( chunk )

        In contrast to the low level Decoder, this class's read() method makes
        sure to always return the requested number of bytes (except at EOF),
        even if that requires multiple low level read() calls. Furthermore,
        DecodeErrors are ignored by default because some broken files cause them
        unnecessarily. This can be disabled by setting errignore=False, in which
        case all DecodeErrors will be raised.
    """

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
        """ Dump input file format information to stdout. """
        self._decoder.dump_format()
