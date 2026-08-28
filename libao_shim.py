"""
Drop-in replacement for the parts of python3-pyao's `ao` module that
failaudio.py / sndtest.py actually use: AudioDevice(driver_name, bits=,
rate=, channels=) and AudioDevice.play(bytes).

Why: the packaged python3-pyao 0.82 C extension parses the buffer given
to AudioDevice.play() with the "y#"/"s#" format code without defining
PY_SSIZE_T_CLEAN. Since Python 3.10 that makes CPython raise
SystemError: PY_SSIZE_T_CLEAN macro must be defined for '#' formats
instead of just warning, and PyQt aborts the whole process when that
exception surfaces from inside a QThread - so every playback attempt
kills failaudio outright. Upstream (https://github.com/tynn/PyAO) hasn't
fixed it as of 2026-08, and there's no newer Debian package either.

Rather than patch/replace the installed system package, this talks to
libao directly via ctypes, exposing just enough of the same API that
failaudio.py and sndtest.py don't need to change beyond their `import
ao` line. Swap that import back to `import ao` once pyao ships a real
fix.
"""

import ctypes
import ctypes.util

_libname = ctypes.util.find_library("ao") or "libao.so.4"
_libao = ctypes.CDLL(_libname)

_libao.ao_initialize.argtypes = []
_libao.ao_initialize.restype = None

_libao.ao_driver_id.argtypes = [ctypes.c_char_p]
_libao.ao_driver_id.restype = ctypes.c_int

_libao.ao_open_live.restype = ctypes.c_void_p

_libao.ao_play.restype = ctypes.c_int

_libao.ao_close.argtypes = [ctypes.c_void_p]
_libao.ao_close.restype = ctypes.c_int


class _SampleFormat(ctypes.Structure):
    _fields_ = [
        ("bits", ctypes.c_int),
        ("rate", ctypes.c_int),
        ("channels", ctypes.c_int),
        ("byte_format", ctypes.c_int),
        ("matrix", ctypes.c_char_p),
    ]


_libao.ao_open_live.argtypes = [ctypes.c_int, ctypes.POINTER(_SampleFormat), ctypes.c_void_p]
_libao.ao_play.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]

_initialized = False


class AOError(Exception):
    pass


def _ensure_initialized():
    global _initialized
    if not _initialized:
        _libao.ao_initialize()
        _initialized = True


class AudioDevice:
    """ Matches ao.AudioDevice's constructor/play() as used by this codebase. """

    def __init__(self, driver_name, bits=16, rate=44100, channels=2, byte_format=1, matrix=None):
        _ensure_initialized()

        driver_id = _libao.ao_driver_id(driver_name.encode())
        if driver_id < 0:
            raise AOError("No such driver: %r" % (driver_name,))

        fmt = _SampleFormat(
            bits=bits,
            rate=rate,
            channels=channels,
            byte_format=byte_format,
            matrix=matrix.encode() if matrix else None,
        )

        self._dev = _libao.ao_open_live(driver_id, ctypes.byref(fmt), None)
        if not self._dev:
            raise AOError("Error opening device.")

    def play(self, data):
        if not _libao.ao_play(self._dev, data, len(data)):
            raise AOError("Error playing samples")

    def close(self):
        if getattr(self, "_dev", None):
            _libao.ao_close(self._dev)
            self._dev = None

    def __del__(self):
        self.close()
