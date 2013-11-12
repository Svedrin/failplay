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
import curses

from time import time, sleep
from ConfigParser import ConfigParser
from PyQt4 import Qt, QtCore

from failaudio import Playlist, Player



if __name__ == '__main__':
    import os
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
    options, posargs = parser.parse_args()

    conf = ConfigParser()
    conf.read(os.path.join(os.environ["HOME"], ".failplay", "failblaster.conf"))

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
        print "Loading playlist from", playlistfile
        p.loadpls(playlistfile)

    enqueue = getconf("enqueue") in (True, "True")
    for filename in posargs:
        if enqueue:
            p.enqueue(filename)
        else:
            p.append(filename)

    app = QtCore.QCoreApplication([])
    player = Player(getconf("out", "pulse"), p)

    def main(stdscr):
        stdscr.nodelay(1)
        player.start()

        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_CYAN)
        curses.init_pair(3, curses.COLOR_GREEN, curses.COLOR_CYAN)
        cursor = 0
        while True:
            app.processEvents()
            stdscr.clear()
            stdscr.move(0, 0)

            maxy = stdscr.getmaxyx()[0] - 2
            startIdx = max(0, min(cursor - 5, len(p) - maxy))
            endIdx   = min(startIdx + maxy, len(p))

            for itemIdx in range(startIdx, endIdx):
                # Color flag.
                # bg: black = standard, cyan  = cursored
                # fg: white = standard, green = playing
                clr = 0
                if itemIdx == p.current:
                    clr += 1
                if itemIdx == cursor:
                    clr += 2
                if clr:
                    clr = curses.color_pair(clr)

                #stdscr.addstr(itemIdx - startIdx,  0, "%d / %d" % (itemIdx, len(p)), clr)
                stdscr.addstr(itemIdx - startIdx,  0,
                    p.data(p.index(itemIdx, 0), Qt.Qt.DisplayRole).encode("UTF-8"), clr)
                stdscr.addstr(itemIdx - startIdx, 70,
                    p.data(p.index(itemIdx, 1), Qt.Qt.DisplayRole).encode("UTF-8"), clr)

            stdscr.addstr(maxy + 1, 0,
                (u"%s — %s (%s)" % (player.source.title,
                    timedelta(seconds=int(player.source.pos)),
                    timedelta(seconds=int(player.source.duration)))).encode("utf-8"))

            stdscr.refresh()

            c = stdscr.getch()
            if   c == curses.KEY_DOWN:
                if cursor < len(p) - 1:
                    cursor += 1
            elif c == curses.KEY_UP:
                if cursor > 0:
                    cursor -= 1
            elif c == ord("q"):
                break
            elif c == ord(" "):
                if cursor == p.current:
                    p.toggleRepeat( p[ p.current ] )
                else:
                    p.toggleQueue( p[cursor] )
            elif c == ord("s"):
                p.toggleStopAfter( p[cursor] )
            elif c == ord("r"):
                p.toggleRepeat( p[cursor] )
            elif c == -1:
                sleep(.05)
            else:
                print "wat", c


    try:
        curses.wrapper(main)
    finally:
        player.stop()

        playlistfile = getconf("writepls")
        if playlistfile:
            print "Saving playlist to", playlistfile
            p.writepls(playlistfile)
