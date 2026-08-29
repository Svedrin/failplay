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
Optional MPRIS2 (https://specifications.freedesktop.org/mpris-spec/latest/) support.

FailPlay's whole design is "it plays until it's done, there's no pause/skip/seek", so
most of the MPRIS control surface doesn't apply. We advertise that honestly: every
Can* capability is False except CanControl and CanQuit, and Play/Pause/Next/Previous/
Seek/SetPosition/OpenUri are accepted but ignored. The one control we actually wire up
is Stop (and Quit), which exits the process - that's the whole point of this module,
since it lets desktop shells (KDE's lock screen media widget, etc.) show what's
currently playing and offer a working stop button.

This is entirely optional: if the session bus isn't reachable (no DBus running, no
display, whatever), MPRISInterface just leaves `.active` False and does nothing. Callers
don't need to check anything up front, and playback keeps working without it.
"""

from pathlib import Path

from PyQt5.QtCore import (
    QObject, pyqtProperty, pyqtSlot, Q_CLASSINFO, QVariant, QMetaType, QTimer,
)

try:
    from PyQt5.QtDBus import (
        QDBusAbstractAdaptor, QDBusConnection, QDBusMessage, QDBusObjectPath,
    )
    HAVE_QTDBUS = True
except ImportError:
    HAVE_QTDBUS = False


MPRIS_PATH   = "/org/mpris/MediaPlayer2"
IFACE_ROOT   = "org.mpris.MediaPlayer2"
IFACE_PLAYER = "org.mpris.MediaPlayer2.Player"
IFACE_PROPS  = "org.freedesktop.DBus.Properties"


def _as_int64(value):
    """ Force a python int into a genuine 64-bit variant (mpris:length/Position are 'x'). """
    variant = QVariant(value)
    variant.convert(QMetaType.LongLong)
    return variant


def _as_strlist(value):
    """ Force a list of strings into a real 'as', not an array of variants. """
    variant = QVariant(value)
    variant.convert(QMetaType.QStringList)
    return variant


def _file_uri(path):
    try:
        return Path(path).resolve().as_uri()
    except (ValueError, OSError):
        return "file://" + path


class _RootAdaptor(QDBusAbstractAdaptor):
    """ org.mpris.MediaPlayer2 - the player-application-wide bits. """

    Q_CLASSINFO("D-Bus Interface", IFACE_ROOT)

    def __init__(self, mpris):
        QDBusAbstractAdaptor.__init__(self, mpris)
        self.mpris = mpris

    @pyqtProperty(bool)
    def CanQuit(self):
        return True

    @pyqtProperty(bool)
    def CanRaise(self):
        return False

    @pyqtProperty(bool)
    def CanSetFullscreen(self):
        return False

    @pyqtProperty(bool)
    def Fullscreen(self):
        return False

    @pyqtProperty(bool)
    def HasTrackList(self):
        return False

    @pyqtProperty(str)
    def Identity(self):
        return self.mpris.identity

    @pyqtProperty(str)
    def DesktopEntry(self):
        return ""

    @pyqtProperty('QStringList')
    def SupportedUriSchemes(self):
        return []

    @pyqtProperty('QStringList')
    def SupportedMimeTypes(self):
        return []

    @pyqtSlot()
    def Raise(self):
        pass  # No window to raise from here; ignored.

    @pyqtSlot()
    def Quit(self):
        self.mpris.request_quit()


class _PlayerAdaptor(QDBusAbstractAdaptor):
    """ org.mpris.MediaPlayer2.Player - transport controls and now-playing metadata. """

    Q_CLASSINFO("D-Bus Interface", IFACE_PLAYER)

    def __init__(self, mpris):
        QDBusAbstractAdaptor.__init__(self, mpris)
        self.mpris = mpris

    @pyqtProperty(str)
    def PlaybackStatus(self):
        return self.mpris.playback_status

    @pyqtProperty(str)
    def LoopStatus(self):
        return "None"

    @pyqtProperty(float)
    def Rate(self):
        return 1.0

    @pyqtProperty(bool)
    def Shuffle(self):
        return False

    @pyqtProperty('QVariantMap')
    def Metadata(self):
        return self.mpris.metadata

    @pyqtProperty(float)
    def Volume(self):
        return 1.0

    @pyqtProperty('qlonglong')
    def Position(self):
        return self.mpris.position_us

    @pyqtProperty(float)
    def MinimumRate(self):
        return 1.0

    @pyqtProperty(float)
    def MaximumRate(self):
        return 1.0

    @pyqtProperty(bool)
    def CanGoNext(self):
        return False

    @pyqtProperty(bool)
    def CanGoPrevious(self):
        return False

    @pyqtProperty(bool)
    def CanPlay(self):
        return False

    @pyqtProperty(bool)
    def CanPause(self):
        return False

    @pyqtProperty(bool)
    def CanSeek(self):
        return False

    @pyqtProperty(bool)
    def CanControl(self):
        return True

    # FailPlay has no pause/skip/seek, so these are accepted (clients are allowed to
    # call them regardless of the Can* flags above) but simply ignored.
    @pyqtSlot()
    def Next(self):
        pass

    @pyqtSlot()
    def Previous(self):
        pass

    @pyqtSlot()
    def Pause(self):
        pass

    @pyqtSlot()
    def PlayPause(self):
        pass

    @pyqtSlot()
    def Play(self):
        pass

    @pyqtSlot('qlonglong')
    def Seek(self, offset_us):
        pass

    @pyqtSlot('QDBusObjectPath', 'qlonglong')
    def SetPosition(self, track_id, position_us):
        pass

    @pyqtSlot(str)
    def OpenUri(self, uri):
        pass

    # Stop is the one command that actually does something: it exits the process.
    @pyqtSlot()
    def Stop(self):
        self.mpris.request_quit()


class MPRISInterface(QObject):
    """
    Bridges a failaudio Player/Source pair onto the session bus as an MPRIS2 player.

    `identity` is the display name (e.g. "FailPlay"); it's also lowercased to build
    the DBus service name org.mpris.MediaPlayer2.<identity>. `quit_callback` is called
    (in addition to Player.stop()) whenever an MPRIS client asks us to Stop or Quit -
    it's the caller's job to actually tear down the process/window from there.

    If the session bus can't be reached, or QtDBus isn't available at all, this becomes
    an inert no-op: `.active` stays False and nothing else needs to check for that.
    """

    def __init__(self, identity, player, quit_callback):
        QObject.__init__(self)
        self.identity      = identity
        self.player        = player
        self.quit_callback = quit_callback
        self.active        = False
        self.bus           = None

        self._status    = "Stopped"
        self._source    = None
        self._track_num = 0

        if not HAVE_QTDBUS:
            return

        bus = QDBusConnection.sessionBus()
        if not bus.isConnected():
            return

        if not bus.registerObject(MPRIS_PATH, self):
            return

        service_name = "org.mpris.MediaPlayer2.%s" % identity.lower()
        if not bus.registerService(service_name):
            # Another instance is already running; MPRIS allows/expects a unique
            # per-instance suffix in that case.
            import os
            service_name = "%s.instance%d" % (service_name, os.getpid())
            if not bus.registerService(service_name):
                bus.unregisterObject(MPRIS_PATH)
                return

        self.bus          = bus
        self.service_name = service_name

        # Keep references so the adaptors aren't garbage-collected out from under us.
        self._root_adaptor   = _RootAdaptor(self)
        self._player_adaptor = _PlayerAdaptor(self)

        player.sig_started.connect(self._on_started)
        player.sig_stopped.connect(self._on_stopped)
        player.sig_position_normal.connect(self._on_position_normal)
        player.sig_position_trans.connect(self._on_position_trans)

        self.active = True

    def close(self):
        """ Release the bus name/object, if we ever claimed one. """
        if self.bus is not None:
            self.bus.unregisterObject(MPRIS_PATH)
            self.bus.unregisterService(self.service_name)
            self.bus = None
        self.active = False

    # -- state used by the adaptors --

    @property
    def playback_status(self):
        return self._status

    @property
    def position_us(self):
        if self._source is None:
            return 0
        return int(self._source.pos * 1000000)

    @property
    def metadata(self):
        if self._source is None:
            return {}
        source = self._source
        meta = {
            "mpris:trackid": QVariant(QDBusObjectPath("%s/Track/%d" % (MPRIS_PATH, self._track_num))),
            "mpris:length":  _as_int64(int(source.duration * 1000000)),
            "xesam:title":   source.title,
            "xesam:url":     _file_uri(source.path),
        }
        tags = getattr(source.fd, "metadata", None) or {}
        artist = tags.get("artist")
        if artist:
            meta["xesam:artist"] = _as_strlist([artist])
        album = tags.get("album")
        if album:
            meta["xesam:album"] = album
        return meta

    # -- Player signal handlers --

    def _emit_changed(self, iface, props):
        if not self.active:
            return
        msg = QDBusMessage.createSignal(MPRIS_PATH, IFACE_PROPS, "PropertiesChanged")
        msg << iface
        msg << QVariant({key: QVariant(val) for key, val in props.items()})
        msg << QVariant([])
        self.bus.send(msg)

    def _on_started(self, source):
        self._source     = source
        self._status     = "Playing"
        self._track_num += 1
        self._emit_changed(IFACE_PLAYER, {
            "PlaybackStatus": self._status,
            "Metadata":       self.metadata,
        })

    def _on_stopped(self, msg):
        self._status = "Stopped"
        self._emit_changed(IFACE_PLAYER, {"PlaybackStatus": self._status})

    def _on_position_normal(self, source, data):
        self._source = source

    def _on_position_trans(self, prev, source, fac, prevdata, srcdata):
        self._source = source

    def request_quit(self):
        # Deferred by one event loop tick so QtDBus gets a chance to send the method
        # reply before we tear the process down - otherwise the calling client sees
        # the connection drop instead of a clean reply.
        QTimer.singleShot(0, self._do_quit)

    def _do_quit(self):
        self.player.stop()
        self.quit_callback()
