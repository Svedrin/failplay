# -*- coding: utf-8 -*-
"""
Shared "is DBus even reachable" Given steps, used by both mpris.feature and
sinkwatch.feature: both modules have a HAVE_QTDBUS flag and a QDBusConnection
reference that get monkeypatched here to simulate DBus (or QtDBus itself)
being unavailable, without touching the process-wide (and, once established,
permanently cached) Qt session bus connection. "a real DBus session bus is
available" just relies on the @dbus tag hook in environment.py having started
a private session bus for the feature.
"""

import os

from behave import given

import mpris as mpris_module
import sinkwatch as sinkwatch_module

_TARGET_MODULES = (mpris_module, sinkwatch_module)


@given(u'the DBus session bus is unreachable')
def step_impl(context):
    class _DisconnectedBus:
        def isConnected(self):
            return False

    class _FakeQDBusConnection:
        @staticmethod
        def sessionBus():
            return _DisconnectedBus()

    originals = {module: module.QDBusConnection for module in _TARGET_MODULES}
    for module in _TARGET_MODULES:
        module.QDBusConnection = _FakeQDBusConnection

    def _restore():
        for module, original in originals.items():
            module.QDBusConnection = original
    context.add_cleanup(_restore)


@given(u'the QtDBus module is unavailable')
def step_impl(context):
    originals = {module: module.HAVE_QTDBUS for module in _TARGET_MODULES}
    for module in _TARGET_MODULES:
        module.HAVE_QTDBUS = False

    def _restore():
        for module, original in originals.items():
            module.HAVE_QTDBUS = original
    context.add_cleanup(_restore)


@given(u'a real DBus session bus is available')
def step_impl(context):
    assert os.environ.get("DBUS_SESSION_BUS_ADDRESS"), (
        "No DBUS_SESSION_BUS_ADDRESS set - expected the @dbus tag hook in "
        "environment.py to have started a private session bus for this feature."
    )
