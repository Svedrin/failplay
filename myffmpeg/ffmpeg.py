#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from _ffmpeg import Decoder as LowLevelDecoder, DecodeError, Resampler

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

        In addition to the properties that retrive information from the Decoder,
        the `position' property calculates the player's position in the file from
        the amount of bytes already retrieved using the read() method.
    """

    def __init__(self, fpath, errignore=True):
        self._decoder = LowLevelDecoder(fpath)
        self._buffer  = ""
        self._errignore = errignore
        self._readbytes = 0

    channels   = property( lambda self: self._decoder.get_channels(),   doc="The number of channels in the input stream." )
    bitrate    = property( lambda self: self._decoder.get_bitrate(),    doc="The bitrate of the input channels." )
    duration   = property( lambda self: self._decoder.get_duration(),   doc="The length of the input stream in seconds." )
    path       = property( lambda self: self._decoder.get_path(),       doc="The input file path." )
    metadata   = property( lambda self: self._decoder.get_metadata(),   doc="Metadata from the input file's tags." )
    codec      = property( lambda self: self._decoder.get_codec(),      doc="The name of the codec used for the stream.")
    samplerate = property( lambda self: self._decoder.get_samplerate(), doc="The sample rate of the input stream." )

    @property
    def position(self):
        """ The player's position in the file in seconds. """
        return self._readbytes / float(self.samplerate * self.channels * 16 / 8)

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
                    if not self._errignore:
                        raise err

            ret = self._buffer[:bytes]
            self._buffer = self._buffer[bytes:]
            self._readbytes += bytes
            yield ret

    def dump_format(self):
        """ Dump input file format information to stdout. """
        self._decoder.dump_format()
