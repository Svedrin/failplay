#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

"""
 *  Copyright (C) 2012, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 *
 *  This code is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
"""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote
from queue import Queue, Empty

from PyQt5.QtCore import QTimer


AUDIO_EXTENSIONS = frozenset({
    '.mp3', '.flac', '.ogg', '.opus', '.m4a',
    '.wav', '.aac', '.wma', '.ape', '.mpc',
})


# ─────────────────────────────────────────────────────────────────────────────
# Single-page HTML/CSS/JS frontend
# ─────────────────────────────────────────────────────────────────────────────
HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>failplay</title>
<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:     #141414;
  --bg2:    #1e1e1e;
  --bg3:    #2a2a2a;
  --fg:     #c8c8c8;
  --accent: #00b4cc;
  --dim:    #5a5a5a;
  --border: #333;
  --active: #00ffcc;
  --queue:  #ffaa44;
}

html, body {
  height: 100%;
  background: var(--bg);
  color: var(--fg);
  font-family: 'Courier New', Courier, monospace;
  font-size: 13px;
  overflow: hidden;
}

body { display: flex; flex-direction: column; }

/* ── header ─────────────────────────────────────────── */
#header {
  background: var(--bg3);
  border-bottom: 1px solid var(--border);
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
#header .logo   { color: var(--dim); user-select: none; }
#header .bullet { color: var(--dim); }
#now-playing    { color: var(--accent); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

/* ── main layout ─────────────────────────────────────── */
#main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* ── library panel ───────────────────────────────────── */
#lib-panel {
  width: 42%;
  min-width: 180px;
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

#breadcrumb {
  padding: 5px 8px;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex-shrink: 0;
  font-size: 12px;
}
.crumb       { color: var(--accent); cursor: pointer; }
.crumb:hover { text-decoration: underline; }
.sep         { color: var(--dim); margin: 0 2px; }

#lib-entries { overflow-y: auto; flex: 1; }

.lib-entry {
  padding: 3px 8px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  user-select: none;
}
.lib-entry:hover { background: var(--bg3); }
.lib-entry.dir   { color: var(--accent); }
.lib-entry.dir::before  { content: '▸ '; }
.lib-entry.file::before { content: '\u00a0\u00a0 '; }

/* ── playlist panel ──────────────────────────────────── */
#pl-panel    { flex: 1; overflow-y: auto; }

#pl-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

#pl-table tr               { border-bottom: 1px solid var(--border); }
#pl-table tr:hover         { background: var(--bg3); }
#pl-table tr.current       { background: #003040; color: var(--accent); }
#pl-table tr.current:hover { background: #004050; }

#pl-table td { padding: 3px 5px; vertical-align: middle; overflow: hidden; }

.td-cur     { width: 1.2em; text-align: center; color: var(--accent); flex-shrink: 0; }
.td-title   { width: 100%; text-overflow: ellipsis; white-space: nowrap; }
.td-flags   { width: 5em;  white-space: nowrap; color: var(--dim); text-align: right; }
.td-flags .qpos { color: var(--queue); }
.td-actions { width: 6.5em; white-space: nowrap; text-align: right; }

/* ── tab bar (mobile only) ───────────────────────────── */
#tab-bar {
  display: none;
  flex-shrink: 0;
  background: var(--bg2);
  border-bottom: 1px solid var(--border);
}
#tab-bar button {
  flex: 1;
  padding: 11px;
  border: none;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  color: var(--dim);
  font-size: 13px;
  font-family: inherit;
  background: none;
  cursor: pointer;
}
#tab-bar button.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}

/* ── responsive ──────────────────────────────────────── */
@media (max-width: 700px) {
  #tab-bar      { display: flex; }
  #main         { flex-direction: column; }
  #lib-panel    { width: 100%; min-width: 0; border-right: none; }

  #main.tab-library  #pl-panel  { display: none; }
  #main.tab-playlist #lib-panel { display: none; }

  .lib-entry    { min-height: 44px; display: flex; align-items: center; }
  #pl-table td  { padding: 8px 5px; }
  .td-actions button { min-height: 34px; padding: 4px 8px; }
}

/* ── buttons ─────────────────────────────────────────── */
button {
  background: none;
  border: 1px solid var(--border);
  color: var(--dim);
  cursor: pointer;
  padding: 1px 4px;
  font-family: inherit;
  font-size: 11px;
  border-radius: 2px;
  line-height: 1.4;
}
button:hover         { border-color: var(--fg); color: var(--fg); }
button.active        { color: var(--active); border-color: var(--active); }
button + button      { margin-left: 2px; }
</style>
</head>
<body>

<div id="header">
  <span class="logo">failplay</span>
  <span class="bullet">&#9632;</span>
  <span id="now-playing">&mdash;</span>
</div>

<nav id="tab-bar">
  <button data-tab="playlist">Playlist</button>
  <button data-tab="library">Library</button>
</nav>

<div id="main">
  <div id="lib-panel">
    <div id="breadcrumb"></div>
    <div id="lib-entries"></div>
  </div>
  <div id="pl-panel">
    <table id="pl-table"><tbody id="pl-body"></tbody></table>
  </div>
</div>

<script>
'use strict';

// ── Tiny reactive wrapper ─────────────────────────────────────────────────────
//
// Wraps a plain object so that assigning any property batches a single
// render pass via queueMicrotask — the same mental model as Alpine's reactivity:
// mutate state, DOM follows automatically.

function reactive(obj) {
    let pending = false;
    return new Proxy(obj, {
        set(target, key, value) {
            target[key] = value;
            if (!pending && typeof target.render === 'function') {
                pending = true;
                queueMicrotask(() => { pending = false; target.render(); });
            }
            return true;
        }
    });
}

// ── HTML escape ───────────────────────────────────────────────────────────────
function esc(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// ── App component ─────────────────────────────────────────────────────────────
//
// Mirrors Alpine's component model:
//
//   reactive(App())   ≈  <div x-data="App()">
//   init()            ≈  x-init
//   computed getters  ≈  Alpine magic properties / $computed
//   action methods    ≈  x-on:click / @click handlers
//   render() / $*()   ≈  Alpine's reactive DOM updates

function App() {
    let _libReady = false;  // closure var — not part of reactive state

    return {

        // ── state (x-data) ────────────────────────────
        playlist:        [],
        library:         [],
        libPath:         '',
        libStack:        [],
        libraryRootName: '',
        tab:             'playlist',

        // ── lifecycle (x-init) ────────────────────────
        init() {
            // Wire up event delegation once (not per render)
            document.getElementById('pl-body')
                .addEventListener('click', ev => this._playlistClick(ev));
            document.getElementById('lib-entries')
                .addEventListener('click', ev => this._libraryClick(ev));
            document.getElementById('breadcrumb')
                .addEventListener('click', ev => this._breadcrumbClick(ev));
            document.getElementById('tab-bar')
                .addEventListener('click', ev => {
                    const btn = ev.target.closest('button[data-tab]');
                    if (btn) this.switchTab(btn.dataset.tab);
                });

            // SSE stream: server pushes state on every change
            const es = new EventSource('/events');
            es.onmessage = ev => {
                Object.assign(this, JSON.parse(ev.data));   // batch-renders once
                if (!_libReady) { _libReady = true; this.browse(''); }
            };
            es.onerror = () => console.warn('failplay: SSE connection lost');
        },

        // ── computed (Alpine @computed / getter) ──────
        get nowPlaying() {
            return this.playlist.find(t => t.current) || null;
        },

        // ── actions ───────────────────────────────────
        browse(path) {
            fetch('/api/library?path=' + encodeURIComponent(path))
                .then(r => r.json())
                .then(entries => {
                    this.library = entries;   // triggers render
                    this.libPath = path;
                });
        },

        navigateTo(path) {
            this.libStack = [...this.libStack, { name: path.split('/').pop(), path }];
            this.browse(path);
        },

        navigateToIdx(idx) {
            this.libStack = this.libStack.slice(0, idx + 1);
            this.browse(this.libStack[idx].path);
        },

        switchTab(name) {
            this.tab = name;
        },

        navigateRoot() {
            this.libStack = [];
            this.browse('');
        },

        enqueue(path) {
            fetch('/api/enqueue', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ path }),
            });
        },

        dequeue(path) {
            fetch('/api/dequeue', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ path }),
            });
        },

        toggleRepeat(path) {
            fetch('/api/repeat', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ path }),
            });
        },

        toggleStopAfter(path) {
            fetch('/api/stopafter', {
                method:  'POST',
                headers: { 'Content-Type': 'application/json' },
                body:    JSON.stringify({ path }),
            });
        },

        // ── event delegation (keeps render() output clean) ─
        _playlistClick(ev) {
            const btn = ev.target.closest('button[data-action]');
            if (!btn) return;
            ev.stopPropagation();
            const idx  = parseInt(btn.closest('tr').dataset.idx, 10);
            const path = this.playlist[idx]?.path;
            if (!path) return;
            const a = btn.dataset.action;
            if      (a === 'enqueue')   this.enqueue(path);
            else if (a === 'dequeue')   this.dequeue(path);
            else if (a === 'repeat')    this.toggleRepeat(path);
            else if (a === 'stopafter') this.toggleStopAfter(path);
        },

        _libraryClick(ev) {
            const el  = ev.target.closest('[data-idx]');
            if (!el) return;
            const item = this.library[parseInt(el.dataset.idx, 10)];
            if (!item) return;
            if (item.is_dir) this.navigateTo(item.path);
            else             this.enqueue(item.path);
        },

        _breadcrumbClick(ev) {
            const el  = ev.target.closest('[data-idx]');
            if (!el) return;
            const idx = parseInt(el.dataset.idx, 10);
            if (idx === -1) this.navigateRoot();
            else            this.navigateToIdx(idx);
        },

        // ── render (Alpine DOM reactivity) ────────────
        //
        // Called automatically whenever a state property is assigned.
        // Sub-renders are split by region so each is easy to follow.

        render() {
            this.$tabs();
            this.$nowPlaying();
            this.$playlist();
            this.$library();
        },

        $tabs() {
            document.getElementById('main').className = 'tab-' + this.tab;
            document.querySelectorAll('#tab-bar button[data-tab]').forEach(btn => {
                btn.classList.toggle('active', btn.dataset.tab === this.tab);
            });
        },

        $nowPlaying() {
            const t = this.nowPlaying;
            document.getElementById('now-playing').textContent = t ? t.title : '\u2014';
        },

        $playlist() {
            document.getElementById('pl-body').innerHTML = this.playlist.map((t, i) => `
<tr class="${t.current ? 'current' : ''}" data-idx="${i}">
  <td class="td-cur">${t.current ? '&#9658;' : ''}</td>
  <td class="td-title">${esc(t.title)}</td>
  <td class="td-flags">\
${t.repeat    ? '<span title="Repeat">\u267b</span>'     : ''}\
${t.stopafter ? '<span title="Stop after">\u25fe</span>' : ''}\
${t.queue_pos ? `<span class="qpos" title="Queue position">${t.queue_pos}</span>` : ''}</td>
  <td class="td-actions">
    ${t.queue_pos
        ? `<button data-action="dequeue" title="Dequeue">\u2212</button>`
        : `<button data-action="enqueue" title="Enqueue next">+</button>`}
    <button data-action="repeat"    title="Repeat"      class="${t.repeat    ? 'active' : ''}">\u267b</button>
    <button data-action="stopafter" title="Stop after"  class="${t.stopafter ? 'active' : ''}">\u25fe</button>
  </td>
</tr>`).join('');
        },

        $library() {
            const rootName = esc(this.libraryRootName || '~');
            document.getElementById('breadcrumb').innerHTML =
                `<span class="crumb" data-idx="-1">${rootName}</span>` +
                this.libStack.map((e, i) =>
                    `<span class="sep">/</span>` +
                    `<span class="crumb" data-idx="${i}">${esc(e.name)}</span>`
                ).join('');

            document.getElementById('lib-entries').innerHTML =
                this.library.map((e, i) =>
                    `<div class="lib-entry ${e.is_dir ? 'dir' : 'file'}" data-idx="${i}">${esc(e.name)}</div>`
                ).join('');
        },
    };
}

const app = reactive(App());
document.addEventListener('DOMContentLoaded', () => app.init());
</script>
</body>
</html>
"""


# ─────────────────────────────────────────────────────────────────────────────
# Web server
# ─────────────────────────────────────────────────────────────────────────────

class WebServer:
    """
    Minimal HTTP server that exposes failplay's playlist and library over a
    browser-based UI.  Mutations are dispatched to the Qt main thread via a
    command queue drained by a QTimer, so Qt model methods are always called
    from the correct thread.  State is pushed to connected browsers via SSE.
    """

    def __init__(self, playlist, player, librarydir, port=8080):
        self.playlist   = playlist
        self.player     = player
        self.librarydir = os.path.normpath(librarydir)
        self.port       = port

        self._sse_clients = []
        self._sse_lock    = threading.Lock()
        self._cmd_queue   = Queue()

        # Drain mutation commands on the Qt main thread every 50 ms.
        self._drain_timer = QTimer()
        self._drain_timer.timeout.connect(self._drain_commands)
        self._drain_timer.start(50)

        # Any signal that changes visible state triggers a broadcast.
        playlist.sig_datachg.connect(lambda *_: self._broadcast())
        playlist.sig_append.connect( lambda *_: self._broadcast())
        playlist.sig_remove.connect( lambda *_: self._broadcast())
        playlist.sig_enqueue.connect(lambda *_: self._broadcast())
        playlist.sig_dequeue.connect(lambda *_: self._broadcast())
        player.sig_started.connect(  lambda *_: self._broadcast())

        self._server = ThreadingHTTPServer(('', port), self._make_handler())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    def start(self):
        self._thread.start()
        print(f"Web interface: http://localhost:{self.port}/")

    # ── Qt-thread helpers ─────────────────────────────────────────────────────

    def _drain_commands(self):
        """Called on the Qt main thread; executes queued playlist mutations."""
        while True:
            try:
                fn = self._cmd_queue.get_nowait()
                try:
                    fn()
                except Exception as exc:
                    print(f"[web] mutation error: {exc}")
            except Empty:
                break

    def _dispatch(self, fn):
        """Queue fn() to run on the Qt main thread (thread-safe)."""
        self._cmd_queue.put(fn)

    def _broadcast(self):
        """Push current state to every SSE client. Safe from any thread."""
        payload = json.dumps(self._get_state())
        with self._sse_lock:
            for q in self._sse_clients:
                q.put(payload)

    # ── State / library helpers ───────────────────────────────────────────────

    def _get_state(self):
        pl = self.playlist
        queue_pos = {}
        for i, path in enumerate(pl.jmpqueue):
            queue_pos.setdefault(path, i + 1)

        return {
            'playlist': [
                {
                    'path':      path,
                    'title':     pl._parse_title(path),
                    'current':   i == pl.current,
                    'repeat':    i == pl.repeat,
                    'stopafter': i == pl.stopafter,
                    'queue_pos': queue_pos.get(path, 0),
                }
                for i, path in enumerate(pl.playlist)
            ],
            'libraryRootName': os.path.basename(self.librarydir) or self.librarydir,
        }

    def _get_library(self, dirpath):
        entries = []
        try:
            for name in sorted(os.listdir(dirpath), key=str.lower):
                full = os.path.join(dirpath, name)
                if os.path.isdir(full):
                    entries.append({'name': name, 'path': full, 'is_dir': True})
                elif os.path.splitext(name)[1].lower() in AUDIO_EXTENSIONS:
                    entries.append({'name': name, 'path': full, 'is_dir': False})
        except PermissionError:
            pass
        return entries

    # ── Request handler ───────────────────────────────────────────────────────

    def _make_handler(self):
        server = self

        class Handler(BaseHTTPRequestHandler):

            def do_GET(self):
                parsed = urlparse(self.path)

                if parsed.path == '/':
                    body = HTML.encode()
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', len(body))
                    self.end_headers()
                    self.wfile.write(body)

                elif parsed.path == '/api/state':
                    self._json(server._get_state())

                elif parsed.path == '/api/library':
                    qs       = parse_qs(parsed.query)
                    rel      = unquote(qs.get('path', [''])[0])
                    absroot  = server.librarydir

                    if rel and os.path.isabs(rel):
                        fullpath = os.path.normpath(rel)
                    elif rel:
                        fullpath = os.path.normpath(os.path.join(absroot, rel))
                    else:
                        fullpath = absroot

                    # Prevent path traversal outside the library root.
                    if fullpath != absroot and not fullpath.startswith(absroot + os.sep):
                        self.send_error(403)
                        return

                    self._json(server._get_library(fullpath))

                elif parsed.path == '/events':
                    self._sse()

                else:
                    self.send_error(404)

            def do_POST(self):
                parsed = urlparse(self.path)
                length = int(self.headers.get('Content-Length', 0))
                try:
                    body = json.loads(self.rfile.read(length)) if length else {}
                except json.JSONDecodeError:
                    self.send_error(400)
                    return

                path = body.get('path', '').strip()
                if not path:
                    self.send_error(400)
                    return

                if parsed.path == '/api/enqueue':
                    def _enqueue(p=path):
                        server.playlist.append(p)
                        server.playlist.enqueue(p)
                    server._dispatch(_enqueue)
                    self._json({'ok': True})

                elif parsed.path == '/api/repeat':
                    def _repeat(p=path):
                        if p in server.playlist:
                            server.playlist.toggleRepeat(p)
                    server._dispatch(_repeat)
                    self._json({'ok': True})

                elif parsed.path == '/api/dequeue':
                    def _dequeue(p=path):
                        server.playlist.dequeue(p)
                    server._dispatch(_dequeue)
                    self._json({'ok': True})

                elif parsed.path == '/api/stopafter':
                    def _stopafter(p=path):
                        if p in server.playlist:
                            server.playlist.toggleStopAfter(p)
                    server._dispatch(_stopafter)
                    self._json({'ok': True})

                else:
                    self.send_error(404)

            def _sse(self):
                q = Queue()
                with server._sse_lock:
                    server._sse_clients.append(q)

                self.send_response(200)
                self.send_header('Content-Type',      'text/event-stream')
                self.send_header('Cache-Control',     'no-cache')
                self.send_header('X-Accel-Buffering', 'no')
                self.end_headers()

                # Immediately send the current state so the page is populated
                # before the first mutation arrives.
                initial = json.dumps(server._get_state())
                try:
                    self.wfile.write(f'data: {initial}\n\n'.encode())
                    self.wfile.flush()
                    while True:
                        try:
                            payload = q.get(timeout=15)
                            line    = f'data: {payload}\n\n'
                        except Empty:
                            line    = ': heartbeat\n\n'   # keep connection alive
                        self.wfile.write(line.encode())
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass
                finally:
                    with server._sse_lock:
                        server._sse_clients.remove(q)

            def _json(self, data):
                body = json.dumps(data).encode()
                self.send_response(200)
                self.send_header('Content-Type',   'application/json')
                self.send_header('Content-Length', len(body))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, fmt, *args):
                pass  # suppress per-request logs

        return Handler
