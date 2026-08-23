# -*- coding: utf-8 -*-
import os

from behave import given, when, then

from failaudio import Playlist
from _helpers import parse_names, track_path, create_track_file  # noqa: F401 (Quoted registered as side effect)


# ── Given: building playlists ────────────────────────────────────────────

@given(u'an empty playlist')
def step_impl(context):
    context.playlist = Playlist()


@given(u'a playlist with the tracks {tracks}')
def step_impl(context, tracks):
    context.playlist = Playlist()
    for name in parse_names(tracks):
        context.playlist.append(create_track_file(context, name))


@given(u'"{name:Quoted}" is enqueued')
def step_impl(context, name):
    context.playlist.enqueue(track_path(context, name))


@given(u'"{name:Quoted}" is set to repeat')
def step_impl(context, name):
    context.playlist.toggleRepeat(track_path(context, name))


@given(u'"{name:Quoted}" is set to stop after')
def step_impl(context, name):
    context.playlist.toggleStopAfter(track_path(context, name))


@given(u'track "{name:Quoted}" is missing from disk')
def step_impl(context, name):
    path = track_path(context, name)
    if os.path.exists(path):
        os.remove(path)


@given(u'the playlist is currently playing "{name:Quoted}"')
def step_impl(context, name):
    path = track_path(context, name)
    pl = context.playlist
    for _ in range(len(pl.playlist) + 1):
        pl.next()
        if pl.current is not None and pl.playlist[pl.current] == path:
            return
    raise AssertionError('Could not advance the playlist to "%s"' % name)


@given(u'a pls file "{fname:Quoted}" containing the tracks {tracks}')
def step_impl(context, fname, tracks):
    names = parse_names(tracks)
    lines = ["[playlist]"]
    for i, name in enumerate(names, start=1):
        path = create_track_file(context, name)
        lines.append("File%d=%s" % (i, path))
        lines.append("Title%d=%s" % (i, os.path.splitext(name)[0]))
        lines.append("")
    lines.append("NumberOfEntries=%d" % len(names))
    lines.append("Version=2")
    fpath = context.pls_files.setdefault(fname, os.path.join(context.tmpdir, fname))
    with open(fpath, "w", encoding="utf-8") as fd:
        fd.write("\n".join(lines) + "\n")


# ── When: mutating the playlist ──────────────────────────────────────────

@when(u'I append "{name:Quoted}" to the playlist')
def step_impl(context, name):
    context.playlist.append(create_track_file(context, name))


@when(u'I insert "{name:Quoted}" at position {index:d}')
def step_impl(context, name, index):
    context.playlist.insert(index, create_track_file(context, name))


@when(u'I remove "{name:Quoted}" from the playlist')
def step_impl(context, name):
    context.playlist.remove(track_path(context, name))


@when(u'I move "{name:Quoted}" to position {index:d}')
def step_impl(context, name, index):
    context.playlist.move(index, track_path(context, name))


@when(u'I enqueue "{name:Quoted}"')
def step_impl(context, name):
    context.playlist.enqueue(create_track_file(context, name))


@when(u'I dequeue "{name:Quoted}"')
def step_impl(context, name):
    context.playlist.dequeue(track_path(context, name))


@when(u'I toggle the queue for "{name:Quoted}"')
def step_impl(context, name):
    context.playlist.toggleQueue(track_path(context, name))


@when(u'I toggle repeat for "{name:Quoted}"')
def step_impl(context, name):
    context.playlist.toggleRepeat(track_path(context, name))


@when(u'I toggle stop-after for "{name:Quoted}"')
def step_impl(context, name):
    context.playlist.toggleStopAfter(track_path(context, name))


@when(u'I clear the queue')
def step_impl(context):
    context.playlist.clear_queue()


@when(u'I randomize the queue')
def step_impl(context):
    context.playlist.randomize()


@when(u'I advance to the next track')
def step_impl(context):
    context.stop_message = None
    try:
        context.playlist.next()
    except StopIteration as exc:
        context.stop_message = str(exc)


@when(u'I peek the next track')
def step_impl(context):
    context.peeked = context.playlist.peek_next()


@when(u'I save the playlist to "{fname:Quoted}"')
def step_impl(context, fname):
    fpath = context.pls_files.setdefault(fname, os.path.join(context.tmpdir, fname))
    context.playlist.writepls(fpath)


@when(u'I load the playlist from "{fname:Quoted}"')
def step_impl(context, fname):
    if context.playlist is None:
        context.playlist = Playlist()
    fpath = context.pls_files.setdefault(fname, os.path.join(context.tmpdir, fname))
    context.playlist.loadpls(fpath)


@when(u'I load a fresh playlist from "{fname:Quoted}"')
def step_impl(context, fname):
    fpath = context.pls_files.setdefault(fname, os.path.join(context.tmpdir, fname))
    context.playlist = Playlist().loadpls(fpath)


# ── Then: playlist / queue contents ──────────────────────────────────────

def _assert_order(context, tracks):
    expected = [track_path(context, name) for name in parse_names(tracks)]
    assert context.playlist.playlist == expected, \
        "expected %r, got %r" % (expected, context.playlist.playlist)


@then(u'the playlist should contain, in order: {tracks}')
def step_impl(context, tracks):
    _assert_order(context, tracks)


@then(u'the playlist should contain {n:d} track')
@then(u'the playlist should contain {n:d} tracks')
def step_impl(context, n):
    assert len(context.playlist) == n, \
        "expected %d tracks, got %d" % (n, len(context.playlist))


@then(u'track "{name:Quoted}" should be in the playlist')
def step_impl(context, name):
    assert track_path(context, name) in context.playlist


@then(u'track "{name:Quoted}" should not be in the playlist')
def step_impl(context, name):
    assert track_path(context, name) not in context.playlist


@then(u'the title of "{name:Quoted}" should be "{title:Quoted}"')
def step_impl(context, name, title):
    assert context.playlist._parse_title(track_path(context, name)) == title


@then(u'the queue should be empty')
def step_impl(context):
    assert context.playlist.jmpqueue == [], "queue was %r" % (context.playlist.jmpqueue,)


@then(u'the queue should contain, in order: {tracks}')
def step_impl(context, tracks):
    expected = [track_path(context, name) for name in parse_names(tracks)]
    assert context.playlist.jmpqueue == expected, \
        "expected %r, got %r" % (expected, context.playlist.jmpqueue)


@then(u'the queue should contain {tracks} in any order')
def step_impl(context, tracks):
    expected = {track_path(context, name) for name in parse_names(tracks)}
    actual = set(context.playlist.jmpqueue)
    assert actual == expected, "expected %r, got %r" % (expected, actual)
    assert len(context.playlist.jmpqueue) == len(expected), \
        "queue has duplicates: %r" % (context.playlist.jmpqueue,)


@then(u'"{name:Quoted}" should be enqueued')
def step_impl(context, name):
    assert track_path(context, name) in context.playlist.jmpqueue


@then(u'"{name:Quoted}" should not be enqueued')
def step_impl(context, name):
    assert track_path(context, name) not in context.playlist.jmpqueue


@then(u'"{name:Quoted}" should be at queue position {pos:d}')
def step_impl(context, name, pos):
    idx = context.playlist.jmpqueue.index(track_path(context, name))
    assert idx + 1 == pos, "expected position %d, got %d" % (pos, idx + 1)


# ── Then: repeat / stopafter / current ───────────────────────────────────

@then(u'"{name:Quoted}" should be marked as repeat')
def step_impl(context, name):
    pl = context.playlist
    assert pl.repeat is not None and pl.playlist[pl.repeat] == track_path(context, name)


@then(u'"{name:Quoted}" should not be marked as repeat')
def step_impl(context, name):
    pl = context.playlist
    assert pl.repeat is None or pl.playlist[pl.repeat] != track_path(context, name)


@then(u'no track should be marked as repeat')
def step_impl(context):
    assert context.playlist.repeat is None


@then(u'"{name:Quoted}" should be marked as stop-after')
def step_impl(context, name):
    pl = context.playlist
    assert pl.stopafter is not None and pl.playlist[pl.stopafter] == track_path(context, name)


@then(u'no track should be marked as stop-after')
def step_impl(context):
    assert context.playlist.stopafter is None


@then(u'the current track should be "{name:Quoted}"')
def step_impl(context, name):
    pl = context.playlist
    assert pl.current is not None, "there is no current track"
    assert pl.playlist[pl.current] == track_path(context, name)


@then(u'there should be no current track')
def step_impl(context):
    assert context.playlist.current is None


@then(u'the peeked track should be "{name:Quoted}"')
def step_impl(context, name):
    assert context.peeked == track_path(context, name)


@then(u'there should be no peeked track')
def step_impl(context):
    assert context.peeked is None


@then(u'playback should stop with a message mentioning "{text:Quoted}"')
def step_impl(context, text):
    assert context.stop_message is not None, "playback did not stop"
    assert text in context.stop_message, \
        "expected %r in stop message, got %r" % (text, context.stop_message)


# ── Then: misc ────────────────────────────────────────────────────────────

@then(u'the playlist should be dirty')
def step_impl(context):
    assert context.playlist.dirty


@then(u'the playlist should not be dirty')
def step_impl(context):
    assert not context.playlist.dirty


@then(u'a backup file "{fname:Quoted}" should exist')
def step_impl(context, fname):
    fpath = context.pls_files.get(fname, os.path.join(context.tmpdir, fname))
    assert os.path.exists(fpath), "%s does not exist" % fpath
