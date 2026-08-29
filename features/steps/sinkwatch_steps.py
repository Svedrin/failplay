# -*- coding: utf-8 -*-
"""
Step definitions for sinkwatch.feature.

There's no PulseAudio in this sandbox, and even with one, the double-variant
property wrapping and the peer-to-peer socket hop its real DBus interface
uses aren't easily reproducible from a test harness. So besides the shared
"is DBus even reachable" scenarios (see dbus_availability_steps.py, which
exercise SinkWatchdog's real guard clauses against a real - if PulseAudio-less
- session bus), everything here drives SinkWatchdog through an injected fake
standing in for a live connection to PulseAudio's Core1 API (sinkwatch._PulseCore),
exercising SinkWatchdog's own resolve/react logic rather than the wire format.
"""

from behave import given, when, then

from _helpers import parse_names
from sinkwatch import SinkWatchdog


class FakePulseCore:
    """ Stands in for sinkwatch._PulseCore: just sinks()/fallback_sink()/
        watch_removed()/close(), plus a test-only remove() to simulate a
        sink going away. """

    def __init__(self, sinks, default=None):
        self._sinks    = dict(sinks)  # {path: name}
        self._default  = default
        self._callback = None
        self.closed    = False

    def sinks(self):
        return dict(self._sinks)

    def fallback_sink(self):
        return self._default

    def watch_removed(self, callback):
        self._callback = callback
        return True

    def remove(self, path):
        del self._sinks[path]
        if self._callback is not None:
            self._callback(path)

    def close(self):
        self.closed = True


def _sink_path(name):
    return "/org/pulseaudio/core1/sink/%s" % name


def _create_watchdog(context, sink_name=None):
    core = getattr(context, "fake_core", None)
    connect = (lambda: core) if core is not None else None
    context.sink_gone_events = []
    context.watchdog = SinkWatchdog(sink_name=sink_name, connect=connect)
    context.watchdog.sig_sink_gone.connect(lambda: context.sink_gone_events.append(True))
    context.add_cleanup(context.watchdog.close)


# ── Given: a fake PulseAudio ──────────────────────────────────────────────

@given(u'a fake PulseAudio with sinks {spec}')
def step_impl(context, spec):
    names = parse_names(spec)
    context.sink_paths = {name: _sink_path(name) for name in names}
    context.fake_core = FakePulseCore({path: name for name, path in context.sink_paths.items()})


@given(u'the default sink is "{name}"')
def step_impl(context, name):
    context.fake_core._default = context.sink_paths[name]


# ── When/Given: creating the watchdog ─────────────────────────────────────

@when(u'I create a sink watchdog')
def step_impl(context):
    _create_watchdog(context)


@given(u'a sink watchdog has been created')
def step_impl(context):
    _create_watchdog(context)


@when(u'I create a sink watchdog configured for "{name}"')
def step_impl(context, name):
    _create_watchdog(context, sink_name=name)


# ── When: sink removal ────────────────────────────────────────────────────

@when(u'"{name}" is removed')
def step_impl(context, name):
    context.fake_core.remove(context.sink_paths[name])


# ── Then ───────────────────────────────────────────────────────────────────

@then(u'the sink watchdog should be active')
def step_impl(context):
    assert context.watchdog.active, "Expected the sink watchdog to be active"


@then(u'the sink watchdog should not be active')
def step_impl(context):
    assert not context.watchdog.active, "Expected the sink watchdog to stay inactive"


@then(u'it should be watching "{name}"')
def step_impl(context, name):
    expected = context.sink_paths[name]
    assert context.watchdog.target_path == expected, (
        "Expected the watchdog to be watching %r (%r), got %r"
        % (name, expected, context.watchdog.target_path)
    )


@then(u'the sink watchdog should report the sink gone')
def step_impl(context):
    assert context.sink_gone_events, "Expected sig_sink_gone to have fired"


@then(u'the sink watchdog should not report the sink gone')
def step_impl(context):
    assert not context.sink_gone_events, "Expected sig_sink_gone not to have fired"
