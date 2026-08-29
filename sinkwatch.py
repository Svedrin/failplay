#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

"""
 *  Copyright (C) 2026, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 *
 *  This code is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
"""

"""
Optional: --stop-on-sink-disconnect makes fail{play,blaster} watch PulseAudio's
DBus interface for the sink they're playing through going away, and exit
automatically when it does. This is for setups like a Bluetooth speaker or a
USB DAC: when the device disappears, PulseAudio quietly reroutes playback to
whatever fallback sink is left (the laptop speakers, say) - usually the last
thing you want. Exiting instead gives the caller (a systemd unit, one of the
bt_fail*.sh wrapper scripts, ...) a clean signal to act on via the exit code.

Which sink counts as "the" sink: if PULSE_SINK names one explicitly (as set
via the [environment] config section, see failplay.conf), that one; otherwise
whatever PulseAudio's current default (fallback) sink is. This is resolved
once, when the watchdog is created - a later default-sink change is not
followed, since by then the new default isn't what's actually carrying our
audio.

Like mpris.py, this is entirely best-effort: if the session bus isn't
reachable, PulseAudio's DBus module isn't loaded, or the target sink can't be
found at all, SinkWatchdog just leaves `.active` False and nothing else needs
to check for that - playback keeps working exactly as if the feature didn't
exist.

PulseAudio's DBus API
(https://www.freedesktop.org/wiki/Software/PulseAudio/Documentation/Developer/Clients/DBus/Overview/)
lives on a *private* socket, not the session bus proper: the session bus only
carries a well-known name, org.PulseAudio1, whose Address property points at
that private socket, which we then talk to as a peer-to-peer DBus connection
(no service/bus names over there, just the one PulseAudio on the other end).
All property values on that private connection are, by design - a historical
mistake kept for compatibility - wrapped in an extra layer of DBus variant,
so reading any of them takes two unwraps, not the usual one.
"""

import itertools

from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot, QVariant

try:
    from PyQt5.QtDBus import QDBusConnection, QDBusInterface, QDBusObjectPath, QDBusVariant
    HAVE_QTDBUS = True
except ImportError:
    HAVE_QTDBUS = False


EX_UNAVAILABLE = 69  # sysexits.h: a service is unavailable - the sink is gone.

SERVER_LOOKUP_SERVICE = "org.PulseAudio1"
SERVER_LOOKUP_PATH    = "/org/pulseaudio/server_lookup1"
SERVER_LOOKUP_IFACE   = "org.PulseAudio.ServerLookup1"

CORE_PATH    = "/org/pulseaudio/core1"
CORE_IFACE   = "org.PulseAudio.Core1"
DEVICE_IFACE = "org.PulseAudio.Core1.Device"
PROPS_IFACE  = "org.freedesktop.DBus.Properties"

_conn_counter = itertools.count()


def _unwrap(value):
    """ Peel off QVariant/QDBusVariant layers until we hit a plain value.
        PulseAudio wraps every property value in an extra variant on top of
        the one DBus itself already uses for a Properties.Get reply. """
    for _ in range(4):  # two layers is normal; bail out rather than loop forever
        if isinstance(value, QVariant):
            value = value.value()
        elif HAVE_QTDBUS and isinstance(value, QDBusVariant):
            value = value.variant()
        else:
            break
    return value


def _path_str(path):
    return path.path() if isinstance(path, QDBusObjectPath) else str(path)


class _PulseCore(QObject):
    """ Thin wrapper around a live peer connection to PulseAudio's Core1 DBus object. """

    def __init__(self, bus, conn_name):
        QObject.__init__(self)
        self.bus       = bus
        self.conn_name = conn_name
        self._callback = None

    def _get(self, path, iface, prop):
        props = QDBusInterface("", path, PROPS_IFACE, self.bus)
        reply = props.call("Get", iface, prop)
        args = reply.arguments()
        return _unwrap(args[0]) if args else None

    def sinks(self):
        """ Return {object_path: name} for every sink PulseAudio currently knows. """
        paths = self._get(CORE_PATH, CORE_IFACE, "Sinks") or []
        result = {}
        for path in paths:
            path = _path_str(path)
            result[path] = self._get(path, DEVICE_IFACE, "Name")
        return result

    def fallback_sink(self):
        """ Return the object path of PulseAudio's current default sink, or None. """
        path = self._get(CORE_PATH, CORE_IFACE, "FallbackSink")
        if not path:
            return None
        path = _path_str(path)
        return path if path and path != "/" else None

    def watch_removed(self, callback):
        """ Call `callback(path)` (a plain string) whenever any sink is removed. """
        self._callback = callback
        return self.bus.connect("", CORE_PATH, CORE_IFACE, "SinkRemoved", self._on_removed)

    @pyqtSlot(QDBusObjectPath)
    def _on_removed(self, path):
        if self._callback is not None:
            self._callback(_path_str(path))

    def close(self):
        QDBusConnection.disconnectFromPeer(self.conn_name)


def _connect_pulse_core():
    """ Try to establish a private connection to PulseAudio's Core1 DBus API.
        Returns a _PulseCore, or None if it's unavailable for any reason. """
    if not HAVE_QTDBUS:
        return None

    session = QDBusConnection.sessionBus()
    if not session.isConnected():
        return None

    lookup = QDBusInterface(SERVER_LOOKUP_SERVICE, SERVER_LOOKUP_PATH, PROPS_IFACE, session)
    reply = lookup.call("Get", SERVER_LOOKUP_IFACE, "Address")
    args = reply.arguments()
    if not args:
        return None  # no owner for org.PulseAudio1 - PulseAudio's DBus module isn't loaded
    address = _unwrap(args[0])
    if not address:
        return None

    conn_name = "failplay-pulsecore-%d" % next(_conn_counter)
    bus = QDBusConnection.connectToPeer(address, conn_name)
    if not bus.isConnected():
        QDBusConnection.disconnectFromPeer(conn_name)
        return None

    return _PulseCore(bus, conn_name)


class SinkWatchdog(QObject):
    """ Resolves "the" current PulseAudio sink once, then watches for it going away. """

    sig_sink_gone = pyqtSignal()

    def __init__(self, sink_name=None, connect=None):
        QObject.__init__(self)
        self.active      = False
        self.sink_name   = sink_name
        self.target_path = None
        self._core       = None

        core = (connect or _connect_pulse_core)()
        if core is None:
            return

        target = self._resolve_target(core)
        if target is None or not core.watch_removed(self._on_sink_removed):
            core.close()
            return

        self._core       = core
        self.target_path = target
        self.active      = True

    def _resolve_target(self, core):
        if self.sink_name:
            for path, name in core.sinks().items():
                if name == self.sink_name:
                    return path
            return None
        return core.fallback_sink()

    def _on_sink_removed(self, path):
        if path == self.target_path:
            self.sig_sink_gone.emit()

    def close(self):
        if self._core is not None:
            self._core.close()
            self._core = None
        self.active = False
