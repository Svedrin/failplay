#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import math
import numpy as np

from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtGui import QColor, QPainter, QPen, QBrush, QLinearGradient


class LedVizWidget(QtWidgets.QWidget):
    """
    LED matrix spectrum visualizer with crossfade support.

    Feed audio via update_normal() during single-track playback and
    update_crossfade() during transitions.  Both accept raw S16 stereo
    interleaved bytes at 48 kHz (the format produced by failaudio).
    """

    SAMPLE_RATE = 48000
    FFT_SIZE    = 2048
    NUM_COLS    = 52
    NUM_ROWS    = 26
    F_MIN       =   25.0
    F_MAX       = 17000.0
    DB_FLOOR    =  -60.0   # dB level that maps to row 0

    ATTACK      = 0.78     # fraction of gap closed per call on attack
    DECAY       = 0.018    # level drop per animation frame (~60 fps)
    PEAK_HOLD   = 55       # frames before peak dot starts falling
    PEAK_DROP   = 0.020    # peak drop per frame after hold expires

    # Color gradient keypoints (bottom=0 … top=1): (pos, r, g, b)
    _STOPS = [
        (0.00,   0, 215, 178),   # deep cyan-turquoise
        (0.30,   0, 155, 255),   # sky-blue
        (0.56, 115,   0, 255),   # blue-violet
        (0.76, 215,   0, 205),   # violet
        (0.88, 255,   0, 158),   # magenta
        (1.00, 255, 170, 215),   # warm white-pink
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        # Rolling audio buffers (mono float, FFT_SIZE samples)
        self._cur_buf  = np.zeros(self.FFT_SIZE, dtype=np.float32)
        self._prev_buf = np.zeros(self.FFT_SIZE, dtype=np.float32)

        # Smoothed levels and peak-hold state for current track
        self._levels = np.zeros(self.NUM_COLS)
        self._peaks  = np.zeros(self.NUM_COLS)
        self._phold  = np.zeros(self.NUM_COLS, dtype=int)

        # Same for the outgoing track during crossfade
        self._plev   = np.zeros(self.NUM_COLS)
        self._ppeak  = np.zeros(self.NUM_COLS)
        self._pphold = np.zeros(self.NUM_COLS, dtype=int)

        self._xfade    = 1.0    # 0 = prev dominant → 1 = current dominant
        self._in_xfade = False
        self._sweep_t  = -1.0   # -1 = no sweep in progress
        self._breathe  = 0.0
        self._frame    = 0

        self._bins       = self._compute_bins()
        self._row_colors = self._precompute_colors()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(33)   # ~30 fps

        self.setMinimumHeight(130)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding,
            QtWidgets.QSizePolicy.Preferred,
        )

    # ── Pre-computation ───────────────────────────────────────────────────────

    def _compute_bins(self):
        """Map each column to a (lo, hi) FFT bin range (logarithmic)."""
        freqs = np.fft.rfftfreq(self.FFT_SIZE, 1.0 / self.SAMPLE_RATE)
        bins = []
        for i in range(self.NUM_COLS):
            f0 = self.F_MIN * (self.F_MAX / self.F_MIN) ** (i / self.NUM_COLS)
            f1 = self.F_MIN * (self.F_MAX / self.F_MIN) ** ((i + 1) / self.NUM_COLS)
            lo = max(1, int(np.searchsorted(freqs, f0)))
            hi = max(lo + 1, int(np.searchsorted(freqs, f1)))
            hi = min(hi, len(freqs))
            bins.append((lo, hi))
        return bins

    def _precompute_colors(self):
        """One QColor per row, bottom=index 0, top=index NUM_ROWS-1."""
        stops = self._STOPS
        colors = []
        for row in range(self.NUM_ROWS):
            t = row / max(1, self.NUM_ROWS - 1)
            for i in range(len(stops) - 1):
                t0, r0, g0, b0 = stops[i]
                t1, r1, g1, b1 = stops[i + 1]
                if t <= t1:
                    f = (t - t0) / max(1e-9, t1 - t0)
                    r = int(r0 + f * (r1 - r0))
                    g = int(g0 + f * (g1 - g0))
                    b = int(b0 + f * (b1 - b0))
                    break
            else:
                _, r, g, b = stops[-1][0], stops[-1][1], stops[-1][2], stops[-1][3]
            colors.append(QColor(r, g, b))
        return colors

    # ── Audio ingestion ───────────────────────────────────────────────────────

    def _push(self, data_bytes, buf):
        """Shift new S16 stereo audio into the rolling buffer, return levels."""
        raw  = np.frombuffer(data_bytes, dtype=np.int16)
        mono = raw[::2].astype(np.float32) / 32768.0   # left channel, normalised
        n = len(mono)
        if n == 0:
            return self._fft(buf)
        if n >= len(buf):
            buf[:] = mono[-len(buf):]
        else:
            buf[:-n] = buf[n:]
            buf[-n:] = mono
        return self._fft(buf)

    def _fft(self, buf):
        """Hann-windowed FFT → per-column normalised levels [0, 1]."""
        win  = np.hanning(len(buf))
        mag  = np.abs(np.fft.rfft(buf * win)) * 2.0 / len(buf)
        db   = 20.0 * np.log10(np.maximum(mag, 1e-9))
        norm = np.clip((db - self.DB_FLOOR) / (-self.DB_FLOOR), 0.0, 1.0)
        out  = np.zeros(self.NUM_COLS)
        for i, (lo, hi) in enumerate(self._bins):
            out[i] = float(np.max(norm[lo:hi]))
        return out

    def _absorb(self, raw, levels, peaks, phold):
        """Apply attack smoothing and update peak hold arrays in-place."""
        up      = raw > levels
        levels[:] = np.where(up, levels + (raw - levels) * self.ATTACK, levels)
        new_pk  = raw > peaks
        peaks[:]  = np.where(new_pk, raw,          peaks)
        phold[:]  = np.where(new_pk, self.PEAK_HOLD, phold)

    # ── Public API ────────────────────────────────────────────────────────────

    def update_normal(self, data_bytes):
        """Feed audio for single-track playback."""
        raw = self._push(data_bytes, self._cur_buf)
        self._absorb(raw, self._levels, self._peaks, self._phold)
        if self._in_xfade:
            self._in_xfade  = False
            self._sweep_t   = -1.0
            self._plev[:]   = 0.0
            self._ppeak[:]  = 0.0

    def update_crossfade(self, src_bytes, prev_bytes, fac):
        """Feed audio for both tracks during crossfade.

        fac: 1.0 at transition start (prev dominant) → 0.0 at end (src dominant),
        matching the value emitted by Player.sig_position_trans.
        """
        raw_cur  = self._push(src_bytes,  self._cur_buf)
        raw_prev = self._push(prev_bytes, self._prev_buf)
        self._absorb(raw_cur,  self._levels, self._peaks,  self._phold)
        self._absorb(raw_prev, self._plev,   self._ppeak,  self._pphold)

        cur_prominence = 1.0 - fac   # 0 → 1 as crossfade progresses
        was = self._in_xfade
        self._in_xfade = True
        self._xfade    = cur_prominence
        if not was:
            self._sweep_t = 0.0
            self._breathe = 0.0

    # ── Animation tick ────────────────────────────────────────────────────────

    def _tick(self):
        self._frame += 1

        self._levels = np.maximum(0.0, self._levels - self.DECAY)
        self._plev   = np.maximum(0.0, self._plev   - self.DECAY)

        for peaks, phold in ((self._peaks, self._phold), (self._ppeak, self._pphold)):
            phold -= 1
            np.maximum(0, phold, out=phold)
            falling = phold == 0
            peaks[:] = np.where(falling, np.maximum(0.0, peaks - self.PEAK_DROP), peaks)

        if self._sweep_t >= 0.0:
            self._sweep_t += 0.025
            if self._sweep_t > 1.4:
                self._sweep_t = -1.0

        if self._in_xfade:
            self._breathe += 0.04

        self.update()

    # ── Painting ──────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)


        W = self.width()
        H = self.height()
        C = self.NUM_COLS
        R = self.NUM_ROWS

        # ── Background ────────────────────────────────────────────────────────
        if self._in_xfade:
            bv = int((0.5 + 0.5 * math.sin(self._breathe)) * 10)
            bg = QColor(10 + bv, 14 + bv, 22 + bv * 2)
        else:
            bg = QColor(10, 14, 22)
        p.fillRect(0, 0, W, H, bg)

        # Outer border (dark metal)
        p.setPen(QPen(QColor(28, 38, 54), 1))
        p.drawRect(0, 0, W - 1, H - 1)
        # Inner inset shadow
        p.setPen(QPen(QColor(5, 8, 13), 1))
        p.drawRect(2, 2, W - 5, H - 5)

        # ── LED matrix geometry ───────────────────────────────────────────────
        PAD = 5
        GAP = 2
        mx  = PAD;  my = PAD
        mw  = W - PAD * 2
        mh  = H - PAD * 2

        lw  = (mw - GAP * (C - 1)) / C
        lh  = (mh - GAP * (R - 1)) / R
        rad = min(lw, lh) * 0.22

        col_step = lw + GAP
        row_step = lh + GAP

        # ── Faint horizontal scanlines (grid feel) ────────────────────────────
        p.setPen(QPen(QColor(255, 255, 255, 5)))
        for r in range(R):
            sy = int(my + r * row_step)
            p.drawLine(mx, sy, mx + mw, sy)
        p.setPen(Qt.NoPen)

        # ── Cache frequently used brushes ─────────────────────────────────────
        inactive_brush = QBrush(QColor(16, 22, 32))

        # ── LED grid ──────────────────────────────────────────────────────────
        xf = self._xfade   # 0 = prev dominant, 1 = current dominant

        for col in range(C):
            cx   = mx + col * col_step
            lev  = self._levels[col]
            pk   = self._peaks[col]
            lit  = int(lev * R)
            # Peak dot: row index from top (0=top, R-1=bottom)
            pk_row = R - 1 - int(pk * (R - 1))

            if self._in_xfade:
                plev   = self._plev[col]
                ppk    = self._ppeak[col]
                plit   = int(plev * R)
                ppk_row = R - 1 - int(ppk * (R - 1))
                cur_a  = max(30, int(xf * 235))
                prv_a  = max(20, int((1.0 - xf) * 220))

            for row in range(R):
                # row 0 = top of widget, display_row 0 = bottom (lowest level)
                cy         = my + row * row_step
                drow       = R - 1 - row   # 0 = bottom, R-1 = top
                is_lit     = drow < lit

                rx = int(cx);  ry = int(cy)
                rw = max(1, int(lw));  rh = max(1, int(lh))

                if self._in_xfade:
                    is_plit = drow < plit

                    # Ghost layer (outgoing track) — violet-magenta tones
                    if is_plit:
                        t   = drow / max(1, R - 1)
                        r_c = int(75  + t * 155)
                        g_c = int(0   + t * 15)
                        b_c = int(195 - t * 35)
                        p.setBrush(QBrush(QColor(r_c, g_c, b_c, prv_a)))
                        p.drawRect(rx, ry, rw, rh)

                    # Current track layer
                    if is_lit:
                        if xf < 0.4:
                            # Early in fade: icy cyan-blue
                            t   = drow / max(1, R - 1)
                            r_c = int(t * 35)
                            g_c = int(175 + t * 30)
                            b_c = 255
                            clr = QColor(r_c, g_c, b_c, cur_a)
                        else:
                            c   = self._row_colors[drow]
                            clr = QColor(c.red(), c.green(), c.blue(), cur_a)
                        p.setBrush(QBrush(clr))
                        p.drawRect(rx, ry, rw, rh)

                    if not is_lit and not is_plit:
                        p.setBrush(inactive_brush)
                        p.drawRect(rx, ry, rw, rh)

                else:
                    if is_lit:
                        c  = self._row_colors[drow]
                        # Soft glow halo
                        ge = 2
                        p.setBrush(QBrush(QColor(c.red(), c.green(), c.blue(), 30)))
                        p.drawRect(rx - ge, ry - ge, rw + ge*2, rh + ge*2)
                        # LED itself
                        p.setBrush(QBrush(c))
                        p.drawRect(rx, ry, rw, rh)
                    else:
                        # Inactive LED — very dark, barely visible
                        # Occasional single-cell shimmer for idle life
                        a = 210
                        if (self._frame + col * 7 + row * 13) % 200 == 0:
                            a = 175
                        p.setBrush(QBrush(QColor(16, 22, 32, a)))
                        p.drawRect(rx, ry, rw, rh)

            # ── Peak dot ──────────────────────────────────────────────────────
            if not self._in_xfade:
                if pk > 0.01:
                    py  = my + pk_row * row_step
                    drow_pk = R - 1 - pk_row
                    bc  = self._row_colors[max(0, min(R - 1, drow_pk))]
                    pkc = QColor(min(255, bc.red() + 60),
                                 min(255, bc.green() + 60),
                                 min(255, bc.blue() + 60))
                    p.setBrush(QBrush(pkc))
                    p.drawRect(int(cx), int(py), max(1, int(lw)), max(1, int(lh)))
            else:
                # Ghost peak (outgoing track) — glimmering afterimage
                if ppk > 0.01:
                    py = my + ppk_row * row_step
                    pa = max(0, int((1.0 - xf) * 195))
                    p.setBrush(QBrush(QColor(210, 80, 255, pa)))
                    p.drawRect(int(cx), int(py), max(1, int(lw)), max(1, int(lh)))
                # Current peak
                if pk > 0.01:
                    py    = my + pk_row * row_step
                    drow_pk = R - 1 - pk_row
                    bc    = self._row_colors[max(0, min(R - 1, drow_pk))]
                    pka   = max(30, int(xf * 235))
                    pkc   = QColor(min(255, bc.red() + 60),
                                   min(255, bc.green() + 60),
                                   min(255, bc.blue() + 60), pka)
                    p.setBrush(QBrush(pkc))
                    p.drawRect(int(cx), int(py), max(1, int(lw)), max(1, int(lh)))

        # ── Crossfade sweep (soft horizontal pulse) ────────────────────────────
        if self._sweep_t >= 0.0:
            sw_x = mx + self._sweep_t * mw
            sw_w = mw * 0.11
            grad = QLinearGradient(sw_x - sw_w, 0, sw_x + sw_w, 0)
            grad.setColorAt(0.0, QColor(120, 215, 255,  0))
            grad.setColorAt(0.5, QColor(160, 230, 255, 38))
            grad.setColorAt(1.0, QColor(120, 215, 255,  0))
            p.fillRect(int(sw_x - sw_w), my, int(sw_w * 2), mh, grad)

        # ── Glass reflection (top strip) ──────────────────────────────────────
        gl = QLinearGradient(0, my, 0, my + mh * 0.22)
        gl.setColorAt(0, QColor(255, 255, 255, 16))
        gl.setColorAt(1, QColor(255, 255, 255,  0))
        p.fillRect(mx + 3, my + 3, mw - 6, int(mh * 0.22), gl)

        p.end()
