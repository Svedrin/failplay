# -*- coding: utf-8 -*-
"""
Shared helpers used by both playlist_steps.py and web_steps.py.

Not a step module by itself (no @given/@when/@then decorators), but behave
imports every .py file under features/steps/ so this is a normal place for
plain helper functions to live.
"""

import os
import re
import time

import parse
from behave import register_type

NAME_RE = re.compile(r'"([^"]*)"')
PLACEHOLDER_RE = re.compile(r'<([^>]+)>')


@parse.with_pattern(r'[^"]+')
def _parse_quoted(text):
    """ A parse type for a `"{x}"`-style field that stops at the closing
        quote, so behave doesn't flag step texts differing only by a
        trailing literal (e.g. `...{route}"` vs `...{route}" with body`)
        as ambiguous. """
    return text


register_type(Quoted=_parse_quoted)


def parse_names(text):
    """ Turn `"a.mp3", "b.mp3"` into ["a.mp3", "b.mp3"]. """
    names = NAME_RE.findall(text)
    if not names:
        raise ValueError("Could not parse any quoted names out of: %r" % (text,))
    return names


def track_path(context, name):
    """ Return the absolute path registered for `name`, allocating one under
        the scenario's tmpdir if it doesn't exist yet. Does not touch disk. """
    return context.tracks.setdefault(name, os.path.join(context.tmpdir, name))


def create_track_file(context, name):
    """ Like track_path(), but also makes sure the file actually exists on disk. """
    path = track_path(context, name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "wb").close()
    return path


def register_path(context, name, path):
    """ Register an already-known path (e.g. a subdirectory) under `name`. """
    context.tracks[name] = path
    return path


def resolve_placeholders(context, text, quote_fn=None):
    """ Replace every <name> in `text` with the registered path for `name`. """
    def repl(match):
        value = track_path(context, match.group(1))
        return quote_fn(value) if quote_fn else value
    return PLACEHOLDER_RE.sub(repl, text)


def pump_qt_events(context, until, timeout=2.0, interval=0.02):
    """ Process the Qt event loop until until() is truthy or timeout elapses.

    WebServer only drains HTTP-triggered playlist mutations from a QTimer
    that fires every 50ms inside the Qt event loop; since tests don't run
    app.exec_(), events have to be pumped by hand for those mutations to
    actually happen before assertions run.
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        context.qapp.processEvents()
        if until():
            return True
        time.sleep(interval)
    return until()
