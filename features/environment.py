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
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "steps"))

from PyQt5.QtWidgets import QApplication
from _helpers import pump_qt_events  # noqa: F401  (re-exported for steps that import it from here)

_qapp = None


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
