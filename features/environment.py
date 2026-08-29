# -*- coding: utf-8 -*-
"""
behave environment hooks.

failaudio.Playlist is a QAbstractTableModel and failweb.WebServer relies on
a QTimer to drain HTTP-triggered mutations, so a QApplication has to exist
for the whole run. QT_QPA_PLATFORM=offscreen keeps that headless (no real
display needed in CI / sandboxes).
"""

import os
import shutil
import subprocess
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "steps"))

from PyQt5.QtWidgets import QApplication
from _helpers import pump_qt_events  # noqa: F401  (re-exported for steps that import it from here)

_qapp = None
_dbus_proc = None
_dbus_old_addr = None


def before_all(context):
    global _qapp
    _qapp = QApplication.instance() or QApplication([])
    context.qapp = _qapp


def before_scenario(context, scenario):
    context.tmpdir = tempfile.mkdtemp(prefix="failplay-behave-")
    context.tracks = {}
    context.pls_files = {}
    context.playlist = None
    context.webserver = None
    context.response = None
    context.sse_event = None
    context.stop_message = None
    context.peeked = "__unset__"
    context.extra_tmpdirs = []


def after_scenario(context, scenario):
    if context.webserver is not None:
        try:
            context.webserver._drain_timer.stop()
            context.webserver._server.shutdown()
            context.webserver._server.server_close()
        except Exception:
            pass
    shutil.rmtree(context.tmpdir, ignore_errors=True)
    for extra_tmpdir in context.extra_tmpdirs:
        shutil.rmtree(extra_tmpdir, ignore_errors=True)


def before_tag(context, tag):
    # mpris.feature is tagged @dbus at the feature level (not per-scenario): PyQt
    # caches the outcome of the first-ever QDBusConnection.sessionBus() call for
    # the life of the process, so the private bus has to exist before *any*
    # scenario in the feature gets a chance to establish that connection as
    # "disconnected" - which would poison every later scenario too.
    global _dbus_proc, _dbus_old_addr
    if tag == "dbus" and _dbus_proc is None:
        proc = subprocess.Popen(
            ["dbus-daemon", "--session", "--print-address", "--print-pid", "--nofork"],
            stdout=subprocess.PIPE, text=True,
        )
        addr = proc.stdout.readline().strip()
        if not addr:
            proc.terminate()
            raise RuntimeError("dbus-daemon did not print a session bus address")
        _dbus_old_addr = os.environ.get("DBUS_SESSION_BUS_ADDRESS")
        os.environ["DBUS_SESSION_BUS_ADDRESS"] = addr
        _dbus_proc = proc


def after_tag(context, tag):
    global _dbus_proc, _dbus_old_addr
    if tag == "dbus" and _dbus_proc is not None:
        _dbus_proc.terminate()
        try:
            _dbus_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            _dbus_proc.kill()
        _dbus_proc = None
        if _dbus_old_addr is None:
            os.environ.pop("DBUS_SESSION_BUS_ADDRESS", None)
        else:
            os.environ["DBUS_SESSION_BUS_ADDRESS"] = _dbus_old_addr
        _dbus_old_addr = None
