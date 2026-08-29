# -*- coding: utf-8 -*-
"""
Step definitions for mpris.feature.

MPRISInterface is tested two ways:

- The "inactive" scenarios monkeypatch mpris.QDBusConnection / mpris.HAVE_QTDBUS
  directly, so they exercise the real guard clauses without touching the
  process-wide (and, once established, permanently cached) Qt session bus
  connection.
- The "active" scenarios talk to a real, private dbus-daemon (started once for
  the whole feature by environment.py's @dbus tag hook, since Qt caches the
  first sessionBus() connection attempt for the life of the process - a scenario
  that ran before any bus existed would poison every scenario after it). Calls
  against it go through the real `dbus-send` CLI as an out-of-process client,
  so the test actually exercises DBus wire marshalling rather than just poking
  at MPRISInterface's Python attributes.
"""

import os
import re
import subprocess
import time

from behave import given, when, then
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtDBus import QDBusConnection

import _helpers  # noqa: F401  (registers the "Quoted" parse type used below)
import mpris as mpris_module
from mpris import MPRISInterface

MPRIS_PATH   = mpris_module.MPRIS_PATH
IFACE_ROOT   = mpris_module.IFACE_ROOT
IFACE_PLAYER = mpris_module.IFACE_PLAYER

_VARIANT_RE = re.compile(r'variant\s+\S+\s+(?:"((?:[^"\\]|\\.)*)"|(\S+))')


class FakeSource:
    """ Stands in for failaudio.Source: just the attributes MPRISInterface reads. """

    def __init__(self, path, duration=123.456, artist=None, album=None):
        self.path     = path
        self.title    = os.path.basename(path).rsplit(".", 1)[0]
        self.duration = duration
        self.pos      = 0.0
        tags = {}
        if artist:
            tags["artist"] = artist
        if album:
            tags["album"] = album
        self.fd = type("FakeFd", (), {"metadata": tags})()


class FakePlayer(QObject):
    """ Stands in for failaudio.Player: just the signals and .stop() MPRISInterface uses. """

    sig_position_normal  = pyqtSignal(object, object)
    sig_position_trans   = pyqtSignal(object, object, float, object, object)
    sig_started          = pyqtSignal(object)
    sig_stopped          = pyqtSignal(str)

    def __init__(self):
        QObject.__init__(self)
        self.stop_called = False

    def stop(self):
        self.stop_called = True


def _dbus_send(context, dest, path, method, *typed_args, timeout=5.0):
    """ Run `dbus-send` as an out-of-process MPRIS client, pumping the Qt event
        loop while it's in flight so the in-process MPRISInterface can reply. """
    cmd = ["dbus-send", "--session", "--print-reply", "--dest=%s" % dest, path, method]
    cmd.extend(typed_args)
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    deadline = time.time() + timeout
    while proc.poll() is None and time.time() < deadline:
        context.qapp.processEvents()
        time.sleep(0.01)
    if proc.poll() is None:
        proc.kill()

    # A method call's own reply can arrive before deferred work it triggered
    # (e.g. Stop's QTimer.singleShot(0, ...)) has actually run - pump a bit
    # longer so callers can assert on that follow-up state right away.
    for _ in range(20):
        context.qapp.processEvents()
        time.sleep(0.01)

    out, _ = proc.communicate(timeout=2)
    return out


def _dbus_get_property(context, iface, prop):
    dest = context.mpris.service_name
    out = _dbus_send(
        context, dest, MPRIS_PATH, "org.freedesktop.DBus.Properties.Get",
        "string:%s" % iface, "string:%s" % prop,
    )
    match = _VARIANT_RE.search(out)
    assert match, "Could not parse a DBus property reply from: %r" % (out,)
    return match.group(1) if match.group(1) is not None else match.group(2)


def _create_interface(context, identity):
    player = FakePlayer()
    quit_calls = []
    iface = MPRISInterface(identity, player, lambda: quit_calls.append(True))
    context.add_cleanup(iface.close)
    context.mpris       = iface
    context.player       = player
    context.quit_calls   = quit_calls


# ── Given: bus/module availability ───────────────────────────────────────

@given(u'the DBus session bus is unreachable')
def step_impl(context):
    class _DisconnectedBus:
        def isConnected(self):
            return False

    class _FakeQDBusConnection:
        @staticmethod
        def sessionBus():
            return _DisconnectedBus()

    original = mpris_module.QDBusConnection
    mpris_module.QDBusConnection = _FakeQDBusConnection
    context.add_cleanup(lambda: setattr(mpris_module, "QDBusConnection", original))


@given(u'the QtDBus module is unavailable')
def step_impl(context):
    original = mpris_module.HAVE_QTDBUS
    mpris_module.HAVE_QTDBUS = False
    context.add_cleanup(lambda: setattr(mpris_module, "HAVE_QTDBUS", original))


@given(u'a real DBus session bus is available')
def step_impl(context):
    assert os.environ.get("DBUS_SESSION_BUS_ADDRESS"), (
        "No DBUS_SESSION_BUS_ADDRESS set - expected the @dbus tag hook in "
        "environment.py to have started a private session bus for this feature."
    )


# ── Given/When: creating interfaces ───────────────────────────────────────

@given(u'an MPRIS interface for "{identity}" is registered')
@when(u'I create an MPRIS interface for "{identity}"')
def step_impl(context, identity):
    _create_interface(context, identity)


@when(u'I create another MPRIS interface for "{identity}"')
def step_impl(context, identity):
    # A second real instance would be a second OS process, with its own
    # independent connection to the shared bus - object registration is
    # per-connection, so this is the part that would actually let a second
    # registerObject() at MPRIS_PATH succeed and reach the service-name
    # collision (and its per-pid suffix fallback) that this scenario is
    # about. Reusing this same process's cached sessionBus() connection
    # would instead collide on the object path itself, one step too early.
    address = os.environ["DBUS_SESSION_BUS_ADDRESS"]
    second_bus = QDBusConnection.connectToBus(address, "mpris_steps_second_connection")

    class _SecondConnection:
        @staticmethod
        def sessionBus():
            return second_bus

    original = mpris_module.QDBusConnection
    mpris_module.QDBusConnection = _SecondConnection
    try:
        _create_interface(context, identity)
    finally:
        mpris_module.QDBusConnection = original


# ── When: driving playback state ─────────────────────────────────────────

@given(u'the player starts playing "{filename:Quoted}"')
@when(u'the player starts playing "{filename:Quoted}"')
def step_impl(context, filename):
    context.player.sig_started.emit(FakeSource(filename))


@when(u'the player starts playing "{filename:Quoted}" by "{artist:Quoted}" from "{album:Quoted}"')
def step_impl(context, filename, artist, album):
    context.player.sig_started.emit(FakeSource(filename, artist=artist, album=album))


@when(u'the player stops')
def step_impl(context):
    context.player.sig_stopped.emit("test stop")


# ── When: calling over DBus ──────────────────────────────────────────────

@when(u'I call "{method}" on the DBus player interface')
def step_impl(context, method):
    _dbus_send(context, context.mpris.service_name, MPRIS_PATH, "%s.%s" % (IFACE_PLAYER, method))


@when(u'I call "{method}" on the DBus root interface')
def step_impl(context, method):
    _dbus_send(context, context.mpris.service_name, MPRIS_PATH, "%s.%s" % (IFACE_ROOT, method))


# ── Then: interface activity/identity ────────────────────────────────────

@then(u'the MPRIS interface should be active')
def step_impl(context):
    assert context.mpris.active, "Expected the MPRIS interface to be active"


@then(u'the MPRIS interface should not be active')
def step_impl(context):
    assert not context.mpris.active, "Expected the MPRIS interface to stay inactive"


@then(u'its DBus service name should be "{name}"')
def step_impl(context, name):
    assert context.mpris.service_name == name, (
        "Expected service name %r, got %r" % (name, context.mpris.service_name)
    )


@then(u'its DBus service name should not be "{name}"')
def step_impl(context, name):
    assert context.mpris.service_name != name, (
        "Expected a service name distinct from %r, got the same" % (name,)
    )


# ── Then: DBus properties ────────────────────────────────────────────────

@then(u'the DBus property "{iface}" "{prop}" should be "{expected}"')
def step_impl(context, iface, prop, expected):
    actual = _dbus_get_property(context, iface, prop)
    assert actual == expected, (
        "Expected %s.%s to be %r, got %r" % (iface, prop, expected, actual)
    )


@then(u'the DBus Metadata property should contain {field} "{expected}"')
def step_impl(context, field, expected):
    dest = context.mpris.service_name
    out = _dbus_send(
        context, dest, MPRIS_PATH, "org.freedesktop.DBus.Properties.Get",
        "string:%s" % IFACE_PLAYER, "string:Metadata",
    )
    needle = '"%s"' % expected
    assert needle in out, "Expected Metadata to contain %s %r, got: %s" % (field, expected, out)


# ── Then: side effects ───────────────────────────────────────────────────

@then(u'the player should have been stopped')
def step_impl(context):
    assert context.player.stop_called, "Expected player.stop() to have been called"


@then(u'the player should not have been stopped')
def step_impl(context):
    assert not context.player.stop_called, "Expected player.stop() not to have been called"


@then(u'the quit callback should have been called')
def step_impl(context):
    assert context.quit_calls, "Expected the quit callback to have been called"


@then(u'the quit callback should not have been called')
def step_impl(context):
    assert not context.quit_calls, "Expected the quit callback not to have been called"
