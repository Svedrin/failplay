# -*- coding: utf-8 -*-
import json
import os
import socket
import time
from types import SimpleNamespace
from urllib.parse import quote, urlparse

import requests
from behave import given, when, then

from failweb import WebServer
from _helpers import (
    parse_names, track_path, create_track_file, register_path,
    resolve_placeholders, pump_qt_events,
)


# ── Given: library + server setup ────────────────────────────────────────

@given(u'a music library containing the files {tracks}')
def step_impl(context, tracks):
    for name in parse_names(tracks):
        create_track_file(context, name)


@given(u'the music library has a subdirectory "{dirname:Quoted}"')
def step_impl(context, dirname):
    subdir = os.path.join(context.tmpdir, dirname)
    os.makedirs(subdir, exist_ok=True)
    register_path(context, dirname, subdir)


@given(u'the music library has a subdirectory "{dirname:Quoted}" containing the files {tracks}')
def step_impl(context, dirname, tracks):
    subdir = os.path.join(context.tmpdir, dirname)
    os.makedirs(subdir, exist_ok=True)
    register_path(context, dirname, subdir)
    for name in parse_names(tracks):
        path = os.path.join(subdir, name)
        open(path, "wb").close()
        register_path(context, name, path)


@given(u'the web server is running')
def step_impl(context):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    fake_player = SimpleNamespace(sig_started=SimpleNamespace(connect=lambda *a, **k: None))
    context.webserver = WebServer(context.playlist, fake_player, context.tmpdir, port)
    context.webserver.start()
    context.base_url = "http://127.0.0.1:%d" % port

    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            requests.get(context.base_url + "/", timeout=0.2)
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.02)


def _wait_for_dispatch(context):
    pump_qt_events(context, lambda: context.webserver._cmd_queue.empty())


# ── When: HTTP calls ──────────────────────────────────────────────────────

@when(u'I GET "{route:Quoted}"')
def step_impl(context, route):
    url = context.base_url + resolve_placeholders(context, route, quote_fn=quote)
    context.response = requests.get(url, timeout=5)


@when(u'I open the event stream at "{route:Quoted}"')
def step_impl(context, route):
    """ requests/urllib3 can't stream this: the server replies with plain
        HTTP/1.0 and no Content-Length (by design, it's an infinite SSE
        stream), and urllib3 falls back to reading the whole body until the
        connection closes before yielding anything -- which never happens
        here. So this reads the first "data: ...\\n\\n" event off a raw
        socket instead, then walks away without waiting for the stream to
        end. """
    parsed = urlparse(context.base_url)
    sock = socket.create_connection((parsed.hostname, parsed.port), timeout=5)
    sock.settimeout(5)
    request = "GET %s HTTP/1.1\r\nHost: %s\r\nConnection: close\r\n\r\n" % (route, parsed.hostname)
    sock.sendall(request.encode())

    buf = b""
    try:
        while b"\r\n\r\n" not in buf or b"\n\n" not in buf.split(b"\r\n\r\n", 1)[1]:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    finally:
        sock.close()

    head, _, rest = buf.partition(b"\r\n\r\n")
    status_line = head.split(b"\r\n", 1)[0].decode()
    context.response = SimpleNamespace(status_code=int(status_line.split()[1]))

    context.sse_event = None
    for line in rest.decode("utf-8").split("\n"):
        if line.startswith("data: "):
            context.sse_event = json.loads(line[len("data: "):])
            break


@when(u'I POST "{route:Quoted}"')
def step_impl(context, route):
    context.response = requests.post(context.base_url + route, timeout=5)
    _wait_for_dispatch(context)


@when(u'I POST "{route:Quoted}" with JSON body {body}')
def step_impl(context, route, body):
    resolved = resolve_placeholders(context, body)
    payload = json.loads(resolved) if resolved.strip() else {}
    context.response = requests.post(context.base_url + route, json=payload, timeout=5)
    _wait_for_dispatch(context)


@when(u'I POST "{route:Quoted}" with raw body "{body:Quoted}"')
def step_impl(context, route, body):
    context.response = requests.post(
        context.base_url + route,
        data=body.encode("utf-8"),
        headers={"Content-Type": "text/plain"},
        timeout=5,
    )
    _wait_for_dispatch(context)


# ── Then: HTTP response assertions ───────────────────────────────────────

@then(u'the response status should be {code:d}')
def step_impl(context, code):
    assert context.response.status_code == code, \
        "expected status %d, got %d" % (code, context.response.status_code)


@then(u'the response content type should start with "{prefix:Quoted}"')
def step_impl(context, prefix):
    ctype = context.response.headers.get("Content-Type", "")
    assert ctype.startswith(prefix), "expected content type starting with %r, got %r" % (prefix, ctype)


def _assert_playlist_json_order(context, data, names):
    expected = [track_path(context, name) for name in names]
    actual = [entry["path"] for entry in data["playlist"]]
    assert actual == expected, "expected %r, got %r" % (expected, actual)


@then(u'the JSON response should list the tracks {tracks} in order')
def step_impl(context, tracks):
    _assert_playlist_json_order(context, context.response.json(), parse_names(tracks))


@then(u'the first SSE event should list the tracks {tracks} in order')
def step_impl(context, tracks):
    assert context.sse_event is not None, "did not receive an SSE event"
    _assert_playlist_json_order(context, context.sse_event, parse_names(tracks))


@then(u'the JSON response should be a list of entries named "{names:Quoted}"')
def step_impl(context, names):
    expected = [n.strip() for n in names.split(",")]
    actual = [entry["name"] for entry in context.response.json()]
    assert actual == expected, "expected %r, got %r" % (expected, actual)


@then(u'the JSON response should not contain an entry named "{name:Quoted}"')
def step_impl(context, name):
    actual = [entry["name"] for entry in context.response.json()]
    assert name not in actual, "%r unexpectedly present in %r" % (name, actual)


@then(u'the JSON response should contain a directory entry named "{name:Quoted}"')
def step_impl(context, name):
    entries = context.response.json()
    assert any(e["name"] == name and e["is_dir"] for e in entries), \
        "no directory entry named %r in %r" % (name, entries)
