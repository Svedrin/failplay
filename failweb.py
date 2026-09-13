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
import mimetypes
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
  flex-shrink: 0;
  font-size: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}
#breadcrumb-crumbs {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  flex: 1;
}
.crumb       { color: var(--accent); cursor: pointer; }
.crumb:hover { text-decoration: underline; }
.sep         { color: var(--dim); margin: 0 2px; }
#btn-upload  { flex-shrink: 0; }

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

/* ── search bar (mobile only) ────────────────────────── */
#search-bar {
  display: none;
  flex-shrink: 0;
  padding: 6px 10px;
  background: var(--bg2);
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}
#search-bar input {
  width: 100%;
  background: var(--bg);
  border: 1px solid var(--border);
  color: var(--fg);
  font-family: inherit;
  font-size: 13px;
  padding: 7px 9px;
  border-radius: 3px;
}
#search-bar input::placeholder { color: var(--dim); }

/* ── now-playing panel (mobile only) ─────────────────── */
#now-panel {
  display: none;
  flex-direction: column;
  flex-shrink: 0;
  background: var(--bg2);
  border-top: 1px solid var(--border);
  padding: 10px 14px 6px;
}
#now-artist {
  text-align: center;
  color: var(--dim);
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
#now-title {
  text-align: center;
  color: var(--fg);
  font-size: 17px;
  margin: 2px 0 8px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
#now-fft {
  width: 100%;
  height: 64px;
  display: block;
}
#now-times {
  display: flex;
  justify-content: space-between;
  color: var(--dim);
  font-size: 12px;
  margin-top: 4px;
}

/* ── bottom icon bar (mobile only) ───────────────────── */
#bottom-bar {
  display: none;
  flex-shrink: 0;
  position: relative;
  background: var(--bg2);
  border-top: 1px solid var(--border);
  justify-content: space-around;
  padding: 2px 0;
}
#bottom-bar button {
  flex: 1;
  margin: 0 6px;
  border: none;
  background: none;
  color: var(--fg);
  font-size: 18px;
  padding: 8px;
}
#bottom-bar button:hover  { color: var(--accent); border: none; }
#bottom-bar button.active { color: var(--active); }

#mobile-menu {
  display: flex;
  flex-direction: column;
  position: absolute;
  right: 8px;
  bottom: 100%;
  margin-bottom: 6px;
  background: var(--bg3);
  border: 1px solid var(--border);
  border-radius: 4px;
  overflow: hidden;
  z-index: 10;
}
#mobile-menu[hidden] { display: none; }
#mobile-menu button {
  border: none;
  border-radius: 0;
  text-align: left;
  padding: 10px 16px;
  color: var(--fg);
  background: var(--bg3);
  white-space: nowrap;
}
#mobile-menu button:hover { background: var(--bg2); color: var(--accent); }

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

  #header       { display: none; }
  #search-bar   { display: flex; }
  #now-panel    { display: flex; }
  #bottom-bar   { display: flex; }
}

/* ── on-screen keyboard open (mobile only) ───────────────
   The search box is the only text input on this page, so focusing it is
   an exact signal that the keyboard is up. Hide the now-playing/FFT panel
   and bottom bar so #main (the list) can grow into that space -- see the
   body.kbd-open height handling in the script below for why this also
   stops the list from being scrolled out of view. */
body.kbd-open #now-panel,
body.kbd-open #bottom-bar {
  display: none;
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
  <button id="btn-randomize" title="Enqueue all unqueued tracks in random order" style="margin-left:auto">&#x1f500; randomize</button>
  <button id="btn-clearqueue" title="Remove all tracks from the queue">&#x2715; clear queue</button>
</div>

<nav id="tab-bar">
  <button data-tab="playlist">Playlist</button>
  <button data-tab="library">Library</button>
</nav>

<div id="main">
  <div id="lib-panel">
    <div id="breadcrumb">
      <span id="breadcrumb-crumbs"></span>
      <button id="btn-upload" type="button" title="Upload a file into the uploads folder" style="display:none">&#8679; upload</button>
    </div>
    <input type="file" id="upload-input" multiple hidden
           accept=".mp3,.flac,.ogg,.opus,.m4a,.wav,.aac,.wma,.ape,.mpc">
    <div id="lib-entries"></div>
  </div>
  <div id="pl-panel">
    <table id="pl-table"><tbody id="pl-body"></tbody></table>
  </div>
</div>

<div id="search-bar">
  <input type="search" id="search-input" placeholder="Search">
</div>

<div id="now-panel">
  <div id="now-artist">&nbsp;</div>
  <div id="now-title">&mdash;</div>
  <canvas id="now-fft"></canvas>
  <div id="now-times">
    <span id="now-elapsed">0:00</span>
    <span id="now-remaining">-0:00</span>
  </div>
</div>

<nav id="bottom-bar">
  <button id="btn-nav-back" title="Up one level">&#8249;</button>
  <button id="btn-stop-now" title="Stop after current track">&#9632;</button>
  <button id="btn-menu" title="More">&#9776;</button>
  <div id="mobile-menu" hidden>
    <button data-action="randomize">&#x1f500; Randomize</button>
    <button data-action="clearqueue">&#x2715; Clear queue</button>
  </div>
</nav>

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

// ── mm:ss formatting for the now-playing panel ─────────────────────────────────
function fmtTime(sec) {
    sec = Math.max(0, Math.floor(sec || 0));
    const m = Math.floor(sec / 60), s = sec % 60;
    return m + ':' + String(s).padStart(2, '0');
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
    let _libReady  = false;  // closure vars — not part of reactive state
    let _plRows    = [];     // rows currently rendered in the playlist table (post-search-filter)
    let _libRows   = [];     // ditto for the library listing

    // FFT visualizer state. Lives outside the reactive object because none
    // of it should ever trigger a DOM re-render by itself -- it's driven by
    // its own requestAnimationFrame loop instead.
    let _wasm        = null;   // {memory, samples_ptr, magnitudes_ptr, fft, ...}
    let _audioCtx    = null;
    let _bufCache    = new Map();   // path -> Promise<AudioBuffer>
    let _visPath     = undefined;   // path currently loaded/loading into _visBuffer
    let _visBuffer   = null;        // decoded AudioBuffer for _visPath, once ready
    let _visGen      = 0;           // invalidates in-flight decodes when the track changes
    let _posAnchorAt = 0;           // performance.now() when `now.position` was last received

    return {

        // ── state (x-data) ────────────────────────────
        playlist:        [],
        library:         [],
        libPath:         '',
        libStack:        [],
        libraryRootName: '',
        uploadsEnabled:  false,
        fftEnabled:      false,
        now:             null,   // {path, artist, title, position, duration} | null
        searchQuery:     '',
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
            document.getElementById('btn-randomize')
                .addEventListener('click', () => this.randomize());
            document.getElementById('btn-clearqueue')
                .addEventListener('click', () => this.clearQueue());
            document.getElementById('btn-upload')
                .addEventListener('click', () => document.getElementById('upload-input').click());
            document.getElementById('upload-input')
                .addEventListener('change', ev => {
                    this.uploadFiles(ev.target.files);
                    ev.target.value = '';
                });
            const searchInput = document.getElementById('search-input');
            searchInput.addEventListener('input', ev => { this.searchQuery = ev.target.value; });

            // On-screen keyboard: while the search box is focused, hide the
            // now-playing/FFT panel (body.kbd-open in the stylesheet) and
            // shrink the page to the actual visible viewport instead of the
            // full layout viewport. Without that second part, iOS in
            // particular leaves the layout viewport at full height and
            // scrolls the whole page up to keep the input visible above the
            // keyboard -- taking the list with it. Sizing the body to match
            // visualViewport removes the need for that scroll entirely.
            const vv = window.visualViewport;
            const applyViewportHeight = () => {
                document.body.style.height =
                    (vv && document.body.classList.contains('kbd-open')) ? vv.height + 'px' : '';
            };
            searchInput.addEventListener('focus', () => {
                document.body.classList.add('kbd-open');
                applyViewportHeight();
            });
            searchInput.addEventListener('blur', () => {
                document.body.classList.remove('kbd-open');
                applyViewportHeight();
                window.scrollTo(0, 0);
            });
            if (vv) vv.addEventListener('resize', applyViewportHeight);

            document.getElementById('btn-nav-back')
                .addEventListener('click', () => this.navBack());
            document.getElementById('btn-stop-now')
                .addEventListener('click', () => this.toggleStopAfterNow());
            document.getElementById('btn-menu')
                .addEventListener('click', () => {
                    const menu = document.getElementById('mobile-menu');
                    menu.hidden = !menu.hidden;
                });
            document.getElementById('mobile-menu')
                .addEventListener('click', ev => {
                    const btn = ev.target.closest('button[data-action]');
                    if (!btn) return;
                    if      (btn.dataset.action === 'randomize')  this.randomize();
                    else if (btn.dataset.action === 'clearqueue') this.clearQueue();
                    document.getElementById('mobile-menu').hidden = true;
                });

            // SSE stream: server pushes state on every change
            const es = new EventSource('/events');
            es.onmessage = ev => {
                const data = JSON.parse(ev.data);
                Object.assign(this, data);   // batch-renders once
                if (data.now) _posAnchorAt = performance.now();
                if (!_libReady) { _libReady = true; this.browse(''); }
            };
            es.onerror = () => console.warn('failplay: SSE connection lost');

            // FFT visualizer: load the wasm module and kick off its own
            // render loop, independent of the reactive state's render().
            this._loadWasm();
            requestAnimationFrame(() => this._visTick());
            // Some mobile browsers keep a fresh AudioContext suspended until
            // a user gesture; we never play audio through it, but resuming
            // costs nothing and sidesteps that entirely on iOS.
            document.addEventListener('touchstart', () => {
                if (_audioCtx && _audioCtx.state === 'suspended') _audioCtx.resume();
            }, { once: true });
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
            // The search box filters whichever list is on screen; carrying a
            // query over to the other tab would silently filter it by a term
            // that was never meant for it, so start fresh on every switch.
            this.searchQuery = '';
            document.getElementById('search-input').value = '';
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

        randomize() {
            fetch('/api/randomize', { method: 'POST' });
        },

        clearQueue() {
            fetch('/api/clearqueue', { method: 'POST' });
        },

        navBack() {
            if (this.libStack.length === 0) return;
            if (this.libStack.length === 1) this.navigateRoot();
            else this.navigateToIdx(this.libStack.length - 2);
        },

        toggleStopAfterNow() {
            if (this.now && this.now.path) this.toggleStopAfter(this.now.path);
        },

        uploadFiles(fileList) {
            Array.from(fileList).forEach(file => this.uploadFile(file));
        },

        uploadFile(file) {
            fetch('/api/upload?filename=' + encodeURIComponent(file.name), {
                method:  'POST',
                headers: { 'Content-Type': 'application/octet-stream' },
                body:    file,
            }).then(r => {
                if (r.ok) this.browse(this.libPath);
                else       alert(`Upload of "${file.name}" failed: ${r.status} ${r.statusText}`);
            });
        },

        // ── FFT visualizer ─────────────────────────────
        //
        // The server never touches the audio's frequency content -- it only
        // reports which file is playing and where. The browser fetches that
        // file itself, decodes it with the Web Audio API (no wasm needed for
        // that part, browsers already ship a fast native decoder), and runs
        // the actual FFT in a small wasm module (webfft/fft.c) purely so
        // that bit happens client-side too. Expect some drift from what's
        // really coming out of the speakers -- it's a visualization, not a
        // scope.

        async _loadWasm() {
            try {
                const resp = await fetch('/fft.wasm');
                if (!resp.ok) { console.warn('failplay: fft.wasm unavailable (run `make` to build it)'); return; }
                const bytes = await resp.arrayBuffer();
                const { instance } = await WebAssembly.instantiate(bytes, {});
                _wasm = instance.exports;
            } catch (err) {
                console.warn('failplay: failed to load fft.wasm', err);
            }
        },

        _ensureAudioCtx() {
            if (!_audioCtx) {
                const Ctx = window.AudioContext || window.webkitAudioContext;
                _audioCtx = new Ctx();
            }
            return _audioCtx;
        },

        _loadTrack(path) {
            if (_visPath === path) return;
            _visPath   = path;
            _visBuffer = null;
            const gen  = ++_visGen;
            if (!path) return;

            let pending = _bufCache.get(path);
            if (!pending) {
                pending = fetch('/api/stream?path=' + encodeURIComponent(path))
                    .then(r => r.arrayBuffer())
                    .then(ab => this._ensureAudioCtx().decodeAudioData(ab))
                    .catch(err => { console.warn('failplay: could not decode', path, err); return null; });
                if (_bufCache.size > 4) _bufCache.delete(_bufCache.keys().next().value);
                _bufCache.set(path, pending);
            }
            pending.then(buf => { if (gen === _visGen) _visBuffer = buf; });
        },

        _fftBars(position) {
            const N_BARS = 32;
            if (!_wasm || !_visBuffer) return new Array(N_BARS).fill(0);

            const buf  = _visBuffer;
            const sr   = buf.sampleRate;
            const size = Math.min(2048, _wasm.max_fft_size());
            const centerSample = Math.floor(position * sr);
            const start = Math.max(0, Math.min(Math.max(0, buf.length - size), centerSample - (size >> 1)));

            const samples = new Float32Array(_wasm.memory.buffer, _wasm.samples_ptr(), size);
            if (buf.length < size) {
                samples.fill(0);
            } else if (buf.numberOfChannels > 1) {
                const ch0 = buf.getChannelData(0), ch1 = buf.getChannelData(1);
                for (let i = 0; i < size; i++) samples[i] = 0.5 * (ch0[start + i] + ch1[start + i]);
            } else {
                samples.set(buf.getChannelData(0).subarray(start, start + size));
            }

            _wasm.fft(size);
            const mags = new Float32Array(_wasm.memory.buffer, _wasm.magnitudes_ptr(), size / 2);

            // Group the linearly-spaced FFT bins into log-spaced visual bars,
            // the same idea as the desktop LED visualizer (ledviz.py).
            const fMin = 40, fMax = Math.min(16000, sr / 2);
            const bars = new Array(N_BARS);
            for (let b = 0; b < N_BARS; b++) {
                const f0 = fMin * Math.pow(fMax / fMin, b / N_BARS);
                const f1 = fMin * Math.pow(fMax / fMin, (b + 1) / N_BARS);
                const lo = Math.max(1, Math.floor(f0 / sr * size));
                const hi = Math.min(mags.length, Math.max(lo + 1, Math.ceil(f1 / sr * size)));
                let m = 0;
                for (let i = lo; i < hi; i++) if (mags[i] > m) m = mags[i];
                bars[b] = m;
            }
            return bars;
        },

        _drawFft(bars) {
            const canvas = document.getElementById('now-fft');
            const dpr = window.devicePixelRatio || 1;
            const w = canvas.clientWidth, h = canvas.clientHeight;
            if (w === 0 || h === 0) return;
            if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
                canvas.width  = Math.round(w * dpr);
                canvas.height = Math.round(h * dpr);
            }
            const ctx = canvas.getContext('2d');
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
            ctx.clearRect(0, 0, w, h);
            ctx.fillStyle = '#8a8a8a';
            const n = bars.length, gap = 3;
            const bw = (w - gap * (n - 1)) / n;
            for (let i = 0; i < n; i++) {
                const bh = Math.max(2, bars[i] * h);
                ctx.fillRect(i * (bw + gap), h - bh, bw, bh);
            }
        },

        _visTick() {
            requestAnimationFrame(() => this._visTick());

            const n = this.now;
            if (!n || !n.path) {
                document.getElementById('now-artist').textContent    = ' ';
                document.getElementById('now-title').textContent     = '—';
                document.getElementById('now-elapsed').textContent   = '0:00';
                document.getElementById('now-remaining').textContent = '-0:00';
                this._drawFft(new Array(32).fill(0));
                return;
            }

            this._loadTrack(n.path);
            const elapsed  = (performance.now() - _posAnchorAt) / 1000;
            const position = Math.max(0, Math.min(n.duration || 0, n.position + elapsed));

            document.getElementById('now-artist').textContent    = n.artist || ' ';
            document.getElementById('now-title').textContent     = n.title  || '—';
            document.getElementById('now-elapsed').textContent   = fmtTime(position);
            document.getElementById('now-remaining').textContent = '-' + fmtTime((n.duration || 0) - position);
            this._drawFft(this._fftBars(position));
        },

        // ── event delegation (keeps render() output clean) ─
        _playlistClick(ev) {
            const btn = ev.target.closest('button[data-action]');
            if (!btn) return;
            ev.stopPropagation();
            const idx  = parseInt(btn.closest('tr').dataset.idx, 10);
            const path = _plRows[idx]?.path;
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
            const item = _libRows[parseInt(el.dataset.idx, 10)];
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
            const q = this.searchQuery.trim().toLowerCase();
            _plRows = q ? this.playlist.filter(t => t.title.toLowerCase().includes(q)) : this.playlist;
            document.getElementById('pl-body').innerHTML = _plRows.map((t, i) => `
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
            document.getElementById('breadcrumb-crumbs').innerHTML =
                `<span class="crumb" data-idx="-1">${rootName}</span>` +
                this.libStack.map((e, i) =>
                    `<span class="sep">/</span>` +
                    `<span class="crumb" data-idx="${i}">${esc(e.name)}</span>`
                ).join('');

            document.getElementById('btn-upload').style.display = this.uploadsEnabled ? '' : 'none';

            const q = this.searchQuery.trim().toLowerCase();
            _libRows = q ? this.library.filter(e => e.name.toLowerCase().includes(q)) : this.library;
            document.getElementById('lib-entries').innerHTML =
                _libRows.map((e, i) =>
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

    def __init__(self, playlist, player, librarydir, port=8080, uploaddir=None):
        self.playlist   = playlist
        self.player     = player
        self.librarydir = os.path.normpath(librarydir)
        self.port       = port

        # Uploads are disabled unless uploaddir is configured, and it must
        # live within librarydir (at any depth, including librarydir
        # itself) -- uploaded files may never end up outside the library.
        # The directory itself is created lazily on first upload.
        if uploaddir:
            normalized = os.path.normpath(uploaddir)
            within_library = normalized == self.librarydir or normalized.startswith(self.librarydir + os.sep)
        else:
            normalized = None
            within_library = False

        if within_library:
            self.uploaddir       = normalized
            self.uploads_enabled = True
        else:
            if uploaddir:
                print(f"[web] uploaddir {uploaddir!r} is not within the music library {self.librarydir!r}; uploads disabled")
            self.uploaddir       = None
            self.uploads_enabled = False

        self._sse_clients = []
        self._sse_lock    = threading.Lock()
        self._cmd_queue   = Queue()

        # Mobile UI: the currently-playing Source (or None), used to report
        # position/duration for the client-side FFT visualizer. Read directly
        # off the object like the desktop UI's progress bars do -- position
        # updates arrive via Qt signals on the GUI thread, same as here.
        self._now_source = None

        # The FFT itself is rendered by a wasm module in the browser (see
        # webfft/fft.c); we just hand out the compiled binary. Loaded once at
        # startup so `make` failures show up immediately instead of as a 404
        # deep in a browser devtools tab.
        wasm_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'webfft', 'fft.wasm')
        try:
            with open(wasm_path, 'rb') as f:
                self._fft_wasm = f.read()
        except OSError:
            self._fft_wasm = None
            print(f"[web] {wasm_path} not found; mobile FFT view will be disabled. Run `make` to build it.")

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

        # Position updates arrive far too often to broadcast on directly (once
        # per audio chunk); just remember the latest source and let a slow
        # periodic timer pick it up. The browser interpolates between ticks.
        player.sig_position_normal.connect(lambda src, data: self._set_now(src))
        player.sig_position_trans.connect(lambda prev, src, fac, pdata, sdata: self._set_now(src))
        player.sig_stopped.connect(lambda *_: self._set_now(None))

        self._position_timer = QTimer()
        self._position_timer.timeout.connect(lambda: self._now_source and self._broadcast())
        self._position_timer.start(500)

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

    def _set_now(self, source):
        """Record the Source currently being reported on (or None). Runs on
        the GUI thread via a Qt signal connection; doesn't broadcast by
        itself -- self._position_timer picks it up periodically."""
        self._now_source = source

    # ── State / library helpers ───────────────────────────────────────────────

    def _get_state(self):
        pl = self.playlist
        queue_pos = {}
        for i, path in enumerate(pl.jmpqueue):
            queue_pos.setdefault(path, i + 1)

        src = self._now_source
        if src is not None:
            title = src.title
            artist, _, track_title = title.partition(' - ')
            if not track_title:
                artist, track_title = '', title
            now = {
                'path':     src.path,
                'artist':   artist,
                'title':    track_title,
                'position': src.pos,
                'duration': src.duration,
            }
        else:
            now = None

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
            'uploadsEnabled':  self.uploads_enabled,
            'fftEnabled':      self._fft_wasm is not None,
            'now':             now,
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

    def _resolve_path(self, rel):
        """Resolve a client-supplied library-relative (or absolute) path,
        guarding against traversal outside librarydir. Returns the absolute
        path, or None if it's invalid or escapes the library."""
        absroot = self.librarydir
        if rel and os.path.isabs(rel):
            fullpath = os.path.normpath(rel)
        elif rel:
            fullpath = os.path.normpath(os.path.join(absroot, rel))
        else:
            fullpath = absroot

        if fullpath != absroot and not fullpath.startswith(absroot + os.sep):
            return None
        return fullpath

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
                    fullpath = server._resolve_path(rel)

                    if fullpath is None:
                        self.send_error(403)
                        return

                    self._json(server._get_library(fullpath))

                elif parsed.path == '/api/stream':
                    qs       = parse_qs(parsed.query)
                    rel      = unquote(qs.get('path', [''])[0])
                    fullpath = server._resolve_path(rel)

                    if fullpath is None:
                        self.send_error(403)
                        return
                    if not os.path.isfile(fullpath) or os.path.splitext(fullpath)[1].lower() not in AUDIO_EXTENSIONS:
                        self.send_error(404)
                        return

                    self._stream_file(fullpath)

                elif parsed.path == '/fft.wasm':
                    if server._fft_wasm is None:
                        self.send_error(404, "fft.wasm not built; run `make`")
                        return
                    self.send_response(200)
                    self.send_header('Content-Type',   'application/wasm')
                    self.send_header('Content-Length', len(server._fft_wasm))
                    self.send_header('Cache-Control',  'no-cache')
                    self.end_headers()
                    self.wfile.write(server._fft_wasm)

                elif parsed.path == '/events':
                    self._sse()

                else:
                    self.send_error(404)

            def do_POST(self):
                parsed = urlparse(self.path)

                if parsed.path == '/api/upload':
                    self._upload(parsed)
                    return

                length = int(self.headers.get('Content-Length', 0))
                try:
                    body = json.loads(self.rfile.read(length)) if length else {}
                except json.JSONDecodeError:
                    self.send_error(400)
                    return

                if parsed.path == '/api/randomize':
                    server._dispatch(server.playlist.randomize)
                    self._json({'ok': True})
                    return

                if parsed.path == '/api/clearqueue':
                    server._dispatch(server.playlist.clear_queue)
                    self._json({'ok': True})
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

            def _upload(self, parsed):
                if not server.uploads_enabled:
                    self.send_error(403, "Uploads are disabled")
                    return

                qs   = parse_qs(parsed.query)
                name = unquote(qs.get('filename', [''])[0]).strip()

                if not name or '/' in name or '\\' in name or name in ('.', '..'):
                    self.send_error(400, "Invalid filename")
                    return

                if os.path.splitext(name)[1].lower() not in AUDIO_EXTENSIONS:
                    self.send_error(400, "Unsupported file type")
                    return

                length = int(self.headers.get('Content-Length', 0))
                if length <= 0:
                    self.send_error(400, "Empty upload")
                    return

                data = self.rfile.read(length)

                os.makedirs(server.uploaddir, exist_ok=True)
                target = os.path.join(server.uploaddir, name)
                try:
                    with open(target, 'xb') as f:
                        f.write(data)
                except FileExistsError:
                    self.send_error(409, "A file with that name already exists")
                    return

                self._json({'ok': True, 'name': name, 'path': target})

            def _stream_file(self, fullpath):
                """Serve a library file's raw bytes so the mobile UI can
                decode + FFT it client-side. Whole-file only (no Range
                support) -- decodeAudioData wants the complete file anyway."""
                try:
                    size = os.path.getsize(fullpath)
                except OSError:
                    self.send_error(404)
                    return

                ctype = mimetypes.guess_type(fullpath)[0] or 'application/octet-stream'
                self.send_response(200)
                self.send_header('Content-Type',   ctype)
                self.send_header('Content-Length', size)
                self.send_header('Accept-Ranges',  'none')
                self.end_headers()
                try:
                    with open(fullpath, 'rb') as f:
                        while True:
                            chunk = f.read(65536)
                            if not chunk:
                                break
                            self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    pass

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
