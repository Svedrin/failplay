"""
Picks a working `ao`-module-compatible backend.

The packaged python3-pyao is preferred when it works, but on some Debian
releases (bookworm and older: pyao <= 0.82+ds1-5) its AudioDevice.play()
crashes the whole process instead of raising a catchable exception when
called from a QThread - see libao_shim.py's docstring for the full story.
That crash can't be detected by import success alone (the C extension
imports fine either way), so we actually probe it: open the "null" driver
and play a silent buffer through it. If that doesn't work, fall back to
the ctypes-based libao_shim.
"""

try:
    import ao as _backend

    _probe = _backend.AudioDevice("null")
    _probe.play(b"\x00\x00" * 100)
    _probe.close()
except Exception:
    import libao_shim as _backend

AudioDevice = _backend.AudioDevice
