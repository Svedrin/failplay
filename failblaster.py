#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

"""
 *  Copyright (C) 2013, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 *
 *  This code is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This package is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
"""

import sys
import os
import curses

from time import time, sleep
from configparser import ConfigParser
from PyQt5 import Qt, QtCore

from failaudio import Playlist, Player
from failweb import WebServer
from initwizard import AUDIO_EXTENSIONS, run_init_wizard


def get_lib_entries(path, name_filter=""):
    try:
        names = os.listdir(path)
    except (PermissionError, OSError):
        return []
    entries = []
    for name in sorted(names, key=str.lower):
        if name.startswith('.'):
            continue
        fullpath = os.path.join(path, name)
        is_dir = os.path.isdir(fullpath)
        if not is_dir and os.path.splitext(name)[1].lower() not in AUDIO_EXTENSIONS:
            continue
        if name_filter and name_filter.lower() not in name.lower():
            continue
        entries.append((name, is_dir))
    entries.sort(key=lambda e: (not e[1], e[0].lower()))
    return entries


if __name__ == '__main__':
    import signal
    from optparse import OptionParser
    from datetime import timedelta

    parser = OptionParser(usage="%prog [options] [<file> ...]\n")
    parser.add_option( "-o", "--out",
        help="Audio output device. See http://xiph.org/ao/doc/ for supported drivers. Defaults to pulse.",
        default="pulse"
        )
    parser.add_option( "-d", "--musicdir", help="Library directory", default=None)
    parser.add_option( "-p", "--playlist", help="A file to initialize the playlist from.")
    parser.add_option( "-w", "--writepls", help="A file to write the playlist into. Can be the same as -p.")
    parser.add_option( "-q", "--enqueue",  help="Enqueue the tracks named on the command line.", action="store_true", default=False)
    parser.add_option("--web", dest="web", metavar="PORT",
        help="Enable the web interface on the given port (e.g. --web 8080).", default=None)
    parser.add_option("--uploaddir", dest="uploaddir", metavar="DIR",
        help="Enable file uploads in the web interface. Must be <musicdir> itself or a directory within it.", default=None)
    options, posargs = parser.parse_args()

    conf_path = os.path.join(os.environ["HOME"], ".failplay", "failplay.conf")
    blaster_conf_path = os.path.join(os.environ["HOME"], ".failplay", "failblaster.conf")

    conf = ConfigParser()
    conf.read([conf_path, blaster_conf_path])

    if conf.has_section("environment"):
        for key in conf.options("environment"):
            os.environ[key.upper()] = conf.get("environment", key)

    def getconf(value, default=None):
        if getattr(options, value) is not None:
            return getattr(options, value)
        if conf.has_option("options", value):
            return conf.get("options", value)
        return default


    p = Playlist()

    playlistfile = getconf("playlist")
    if playlistfile:
        print("Loading playlist from", playlistfile)
        p.loadpls(playlistfile)

    enqueue = getconf("enqueue") in (True, "True")
    for filename in posargs:
        if enqueue:
            p.enqueue(filename)
        else:
            p.append(filename)

    if len(p) == 0:
        run_init_wizard(conf_path)
        conf.read([conf_path, blaster_conf_path])

        playlistfile = getconf("playlist")
        if playlistfile:
            print("Loading playlist from", playlistfile)
            p.loadpls(playlistfile)

    app = QtCore.QCoreApplication([])
    player = Player(getconf("out", "pulse"), p)

    web_port = getconf("web")
    if web_port is not None:
        WebServer(
            p, player, getconf("musicdir") or os.environ["HOME"], int(web_port),
            uploaddir=getconf("uploaddir"),
        ).start()

    def main(stdscr):
        stdscr.nodelay(1)
        player.start()

        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_CYAN)

        # Playlist state
        pl_cursor = 0

        # Library state
        lib_path = getconf("musicdir") or os.environ["HOME"]
        lib_filter = ""
        lib_filter_mode = False
        lib_entries = get_lib_entries(lib_path, lib_filter)
        lib_cursor = 0
        lib_scroll = 0
        lib_focus = True

        while True:
            app.processEvents()
            stdscr.clear()

            maxy, maxx = stdscr.getmaxyx()
            # Reserve 2 rows at bottom: hints + status
            content_rows = maxy - 2
            lib_w = maxx // 2
            sep_col = lib_w
            pl_x = lib_w + 1
            pl_w = maxx - pl_x

            # --- Library header ---
            if lib_filter_mode:
                lib_header = " Filter: " + lib_filter + "_"
            elif lib_filter:
                lib_header = " Library [" + lib_filter + "] "
            else:
                lib_header = " Library "
            lib_hattr = curses.A_REVERSE if lib_focus else curses.A_BOLD
            stdscr.addstr(0, 0, lib_header[:lib_w].ljust(lib_w), lib_hattr)

            # Current path (truncated from left)
            path_disp = lib_path
            if len(path_disp) > lib_w - 1:
                path_disp = "\u2026" + path_disp[-(lib_w - 2):]
            try:
                stdscr.addstr(1, 0, path_disp[:lib_w].ljust(lib_w))
            except curses.error:
                pass

            # Library entries (rows 2 .. content_rows-1)
            lib_visible = content_rows - 2
            if lib_entries:
                lib_scroll = max(0, min(lib_scroll, len(lib_entries) - 1))
                if lib_cursor >= lib_scroll + lib_visible:
                    lib_scroll = lib_cursor - lib_visible + 1
                if lib_cursor < lib_scroll:
                    lib_scroll = lib_cursor

            for i in range(lib_visible):
                idx = lib_scroll + i
                row = i + 2
                if row >= content_rows or idx >= len(lib_entries):
                    break
                name, is_dir = lib_entries[idx]
                display = ("/" if is_dir else " ") + name
                clr = 0
                if idx == lib_cursor:
                    clr = curses.color_pair(2) if lib_focus else curses.A_REVERSE
                try:
                    stdscr.addstr(row, 0, display[:lib_w].ljust(lib_w), clr)
                except curses.error:
                    pass

            if not lib_entries:
                try:
                    stdscr.addstr(2, 0, " (empty)", curses.A_DIM)
                except curses.error:
                    pass

            # --- Separator ---
            for row in range(content_rows):
                try:
                    stdscr.addch(row, sep_col, curses.ACS_VLINE)
                except curses.error:
                    pass

            # --- Playlist header ---
            pl_header = " Playlist "
            pl_hattr = curses.A_REVERSE if not lib_focus else curses.A_BOLD
            try:
                stdscr.addstr(0, pl_x, pl_header[:pl_w].ljust(pl_w), pl_hattr)
            except curses.error:
                pass

            # Playlist entries (rows 1 .. content_rows-1)
            pl_visible = content_rows - 1
            pl_dur_w = 6
            pl_title_w = pl_w - pl_dur_w - 1
            pl_start_idx = max(0, min(pl_cursor - 5, len(p) - pl_visible))
            pl_end_idx   = min(pl_start_idx + pl_visible, len(p))

            for itemIdx in range(pl_start_idx, pl_end_idx):
                row = itemIdx - pl_start_idx + 1
                if row >= content_rows:
                    break
                clr = 0
                if itemIdx == p.current:
                    clr += 1
                if itemIdx == pl_cursor and not lib_focus:
                    clr += 2
                if clr:
                    clr = curses.color_pair(clr)

                title = p.data(p.index(itemIdx, 0), Qt.Qt.DisplayRole)
                dur   = p.data(p.index(itemIdx, 1), Qt.Qt.DisplayRole)
                if len(title) > pl_title_w:
                    title = title[:pl_title_w - 1] + "\u2026"
                try:
                    stdscr.addstr(row, pl_x, title.ljust(pl_title_w), clr)
                    stdscr.addstr(row, pl_x + pl_title_w + 1, dur[:pl_dur_w].rjust(pl_dur_w), clr)
                except curses.error:
                    pass

            # --- Key hints ---
            if lib_focus and not lib_filter_mode:
                hints = "Tab:playlist  Enter/\u2192:open  \u2190/Bsp:up  /:filter  q:quit"
            elif lib_filter_mode:
                hints = "Type to filter  Enter/Esc:done"
            else:
                hints = "Tab:library  Space:queue  r:repeat  s:stop-after  z:randomize  x:clear-queue  Del:remove  q:quit"
            try:
                stdscr.addstr(maxy - 2, 0, hints[:maxx - 1], curses.A_DIM)
            except curses.error:
                pass

            # --- Status bar ---
            if player.source is not None:
                status = "%s \u2014 %s (%s)" % (
                    player.source.title,
                    timedelta(seconds=int(player.source.pos)),
                    timedelta(seconds=int(player.source.duration)))
            else:
                status = "Loading..."
            try:
                stdscr.addstr(maxy - 1, 0, status[:maxx - 1])
            except curses.error:
                pass

            stdscr.refresh()

            c = stdscr.getch()

            if lib_filter_mode:
                if c in (curses.KEY_ENTER, ord("\n"), ord("\r"), 27):  # Enter or Escape
                    lib_filter_mode = False
                elif c in (curses.KEY_BACKSPACE, 127, 8):
                    lib_filter = lib_filter[:-1]
                    lib_entries = get_lib_entries(lib_path, lib_filter)
                    lib_cursor = 0
                    lib_scroll = 0
                elif 32 <= c < 127:
                    lib_filter += chr(c)
                    lib_entries = get_lib_entries(lib_path, lib_filter)
                    lib_cursor = 0
                    lib_scroll = 0
            elif c == ord("q"):
                break
            elif c == ord("\t"):
                lib_focus = not lib_focus
            elif c == -1:
                sleep(.05)
            elif lib_focus:
                if c == curses.KEY_DOWN:
                    if lib_cursor < len(lib_entries) - 1:
                        lib_cursor += 1
                elif c == curses.KEY_UP:
                    if lib_cursor > 0:
                        lib_cursor -= 1
                elif c in (curses.KEY_RIGHT, curses.KEY_ENTER, ord("\n"), ord("\r")):
                    if lib_entries:
                        name, is_dir = lib_entries[lib_cursor]
                        fullpath = os.path.join(lib_path, name)
                        if is_dir:
                            lib_path = fullpath
                            lib_entries = get_lib_entries(lib_path, lib_filter)
                            lib_cursor = 0
                            lib_scroll = 0
                        else:
                            p.append(fullpath)
                elif c in (curses.KEY_LEFT, curses.KEY_BACKSPACE, 127, 8):
                    parent = os.path.dirname(lib_path)
                    if parent != lib_path:
                        old_name = os.path.basename(lib_path)
                        lib_path = parent
                        lib_entries = get_lib_entries(lib_path, lib_filter)
                        lib_scroll = 0
                        lib_cursor = next(
                            (i for i, (n, _) in enumerate(lib_entries) if n == old_name), 0)
                elif c == ord("/"):
                    lib_filter_mode = True
            else:  # playlist focus
                if c == curses.KEY_DOWN:
                    if pl_cursor < len(p) - 1:
                        pl_cursor += 1
                elif c == curses.KEY_UP:
                    if pl_cursor > 0:
                        pl_cursor -= 1
                elif c == ord(" "):
                    if pl_cursor == p.current:
                        p.toggleRepeat( p[ p.current ] )
                    else:
                        p.toggleQueue( p[pl_cursor] )
                elif c == ord("s"):
                    p.toggleStopAfter( p[pl_cursor] )
                elif c == ord("r"):
                    p.toggleRepeat( p[pl_cursor] )
                elif c == ord("z"):
                    p.randomize()
                elif c == ord("x"):
                    p.clear_queue()
                elif c == curses.KEY_DC:
                    if len(p) > 0:
                        p.remove(p[pl_cursor])
                        pl_cursor = min(pl_cursor, len(p) - 1)


    try:
        curses.wrapper(main)
    finally:
        player.stop()

        playlistfile = getconf("writepls")
        if playlistfile:
            print("Saving playlist to", playlistfile)
            p.writepls(playlistfile)
