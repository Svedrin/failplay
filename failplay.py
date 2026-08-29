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
 *
 *  This package is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
"""

import os, sys
import struct
import re

from datetime import timedelta
from optparse import OptionParser
from configparser import ConfigParser

from PyQt5 import Qt, QtCore, QtGui, QtWidgets

from failaudio   import Playlist, Player
from ui_failplay import Ui_MainWindow
from failweb     import WebServer
from initwizard  import run_init_wizard
from mpris       import MPRISInterface
from sinkwatch   import SinkWatchdog, EX_UNAVAILABLE


def mkIcon():
    data = b""
    for y in range(16):
        for x in range(16):
            v = int((abs((8-y)/8.) <= abs(-(1/3.) * (x-8)/8. + (1/3.))) * 0xFF)
            data += struct.pack("BBB", v, v, v)
    img = QtGui.QImage(data, 16, 16, QtGui.QImage.Format_RGB888)
    pm = QtGui.QPixmap()
    pm.convertFromImage(img)
    return QtGui.QIcon(pm)



class FailPlay(Ui_MainWindow, QtWidgets.QMainWindow):
    def __init__(self, outdev, librarydir=os.environ["HOME"]):
        QtWidgets.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        self.playlist = Playlist()
        self.player   = Player(outdev, self.playlist)

        # Optional: expose an MPRIS2 interface over DBus so desktops (KDE's lock
        # screen media widget etc.) can show what's playing. Stop is the only control
        # that actually does anything - it closes the window, same as pressing Q.
        # If DBus isn't reachable this quietly does nothing.
        self.mpris = MPRISInterface("FailPlay", self.player, self.close, librarydir=librarydir)

        self.setupUi(self)

        self.player.sig_started.connect(lambda src: self.onPlayerStarted())
        self.player.sig_stopped.connect(lambda msg: self.close())

        self.player.sig_position_normal.connect(self.onPlayerPositionNormal)
        self.player.sig_position_trans.connect(self.onPlayerPositionTrans)

        self.library = QtWidgets.QFileSystemModel()
        self.library.setRootPath(librarydir)
        self.lstLibrary.setModel(self.library)
        self.lstLibrary.setRootIndex(self.library.index(librarydir))
        self.library.setNameFilterDisables(False)
        self.lstLibrary.hideColumn(2)
        self.lstLibrary.hideColumn(3)

        self.playlist.sig_datachg.connect(self.onPlaylistChanged)
        self.leLibraryFilter.textEdited.connect(self.onFilterEdited)
        self.lstLibrary.doubleClicked.connect(self.onLibraryDoubleClicked)
        self.lstPlaylist.doubleClicked.connect(self.onPlaylistDoubleClicked)

        self.playlist.currentBg = QtGui.QBrush(Qt.Qt.cyan, Qt.Qt.SolidPattern)
        self.lstPlaylist.setModel(self.playlist)

        hderp = self.lstPlaylist.horizontalHeader()
        hderp.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        hderp.resizeSection(1, 50)
        hderp.setSectionResizeMode(1, QtWidgets.QHeaderView.Fixed)
        self.lstPlaylist.setHorizontalHeader(hderp)

        # build playlist context menu
        self.actRemove = QtWidgets.QAction("Remove", self.lstPlaylist)
        self.actRemove.triggered.connect(lambda checked: self.onRemoveTriggered())
        self.actRemove.setShortcut(Qt.Qt.Key_Delete)
        self.lstPlaylist.insertAction(None, self.actRemove)

        self.actEnqueue = QtWidgets.QAction("Enqueue", self.lstPlaylist)
        self.actEnqueue.triggered.connect(lambda checked: self.onEnqueueTriggered())
        self.actEnqueue.setShortcut(Qt.Qt.Key_Plus)
        self.lstPlaylist.insertAction(None, self.actEnqueue)

        self.actDequeue = QtWidgets.QAction("Dequeue", self.lstPlaylist)
        self.actDequeue.triggered.connect(lambda checked: self.onDequeueTriggered())
        self.actDequeue.setShortcut(Qt.Qt.Key_Minus)
        self.lstPlaylist.insertAction(None, self.actDequeue)

        self.actRepeat = QtWidgets.QAction("Repeat", self.lstPlaylist)
        self.actRepeat.triggered.connect(lambda checked: self.onRepeatTriggered())
        self.actRepeat.setShortcut(Qt.Qt.Key_R)
        self.lstPlaylist.insertAction(None, self.actRepeat)

        self.actStopAfter = QtWidgets.QAction("Stop after this track", self.lstPlaylist)
        self.actStopAfter.triggered.connect(lambda checked: self.onStopAfterTriggered())
        self.actStopAfter.setShortcut(Qt.Qt.Key_S)
        self.lstPlaylist.insertAction(None, self.actStopAfter)

        self.actRandomize = QtWidgets.QAction("Randomize", self.lstPlaylist)
        self.actRandomize.triggered.connect(lambda checked: self.playlist.randomize())
        self.actRandomize.setShortcut(Qt.Qt.Key_Z)
        self.lstPlaylist.insertAction(None, self.actRandomize)

        self.actClearQueue = QtWidgets.QAction("Clear queue", self.lstPlaylist)
        self.actClearQueue.triggered.connect(lambda checked: self.playlist.clear_queue())
        self.actClearQueue.setShortcut(Qt.Qt.Key_X)
        self.lstPlaylist.insertAction(None, self.actClearQueue)

        def mkShortcut(key, callback):
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.setContext(Qt.Qt.ApplicationShortcut)
            shortcut.activated.connect(callback)
            return shortcut

        self.shortcutSpace = mkShortcut(Qt.Qt.Key_Space,  self.onSpacePressed)
        self.shortcutEnd   = mkShortcut(Qt.Qt.Key_End,    self.onEndPressed)
        self.shortcutEsc   = mkShortcut(Qt.Qt.Key_Escape, self.onEscPressed)
        self.shortcutQuit  = mkShortcut(Qt.Qt.Key_Q,      self.close)

        self.setWindowIcon(mkIcon())

        self.invstatusbars = False
        self.intransition  = False
        self.selection     = None

        self.titleregex = re.compile(r"(?P<title>[^(]+)\([^)]+\)?$")

    def start(self):
        self.player.start()

    @property
    def selected_or_current_index(self):
        if (index := next(iter(self.lstPlaylist.selectedIndexes()), None)) is not None:
            return index
        return self.playlist.current_index

    def save_selection(self):
        self.selection = next(iter(self.lstPlaylist.selectedIndexes()), None)

    def restore_selection(self):
        if self.selection is not None:
            self.lstPlaylist.selectRow(self.selection.row())
        else:
            self.lstPlaylist.clearSelection()

    def onPlaylistDoubleClicked(self, index):
        """ Toggle repeat if currently playing track is doubleclicked, en/dequeue otherwise. """
        if index.row() == self.playlist.current:
            return self.playlist.toggleRepeat(self.playlist[self.playlist.current])
        self.playlist.toggleQueue(self.playlist[index])

    def onSpacePressed(self):
        """ Toggle repeat if currently playing track or none is selected, en/dequeue otherwise. """
        self.save_selection()
        self.onPlaylistDoubleClicked(self.selected_or_current_index)
        self.restore_selection()

    def onEndPressed(self):
        """ Toggle stopAfter on the selected track or the current one if none is selected. """
        self.save_selection()
        self.playlist.toggleStopAfter(self.playlist[self.selected_or_current_index])
        self.restore_selection()

    def onEscPressed(self):
        self.lstPlaylist.clearSelection()

    def onPlaylistChanged(self, topleft, btright):
        self.lstPlaylist.reset()

    def onFilterEdited(self, text):
        if text:
            self.library.setNameFilters(["*" + text + "*"])
            self.lstLibrary.expandAll()
        else:
            self.library.setNameFilters([])
            self.lstLibrary.collapseAll()

    def onPlayerStarted(self):
        self.lstPlaylist.scrollTo(self.playlist.index(self.playlist.current), QtWidgets.QAbstractItemView.PositionAtCenter)

    def onLibraryDoubleClicked(self, index):
        self.playlist.append(self.library.filePath(index))

    def onRemoveTriggered(self):
        if (index := next(iter(self.lstPlaylist.selectedIndexes()), None)) is not None:
            self.playlist.remove(self.playlist[index])

    def onEnqueueTriggered(self):
        if (index := next(iter(self.lstPlaylist.selectedIndexes()), None)) is not None:
            self.playlist.enqueue(self.playlist[index])

    def onDequeueTriggered(self):
        if (index := next(iter(self.lstPlaylist.selectedIndexes()), None)) is not None:
            self.playlist.dequeue(self.playlist[index])

    def onRepeatTriggered(self):
        self.playlist.toggleRepeat(self.playlist[self.selected_or_current_index])

    def onStopAfterTriggered(self):
        self.playlist.toggleStopAfter(self.playlist[self.selected_or_current_index])

    def closeEvent(self, ev):
        self.player.stop()
        QtWidgets.QMainWindow.closeEvent(self, ev)

    def _status_update(self, progressbar, source):
        progressbar.setMaximum(int(source.duration))
        progressbar.setValue(int(source.pos))
        # see if the title is "asd - sdf (some stuff)", and if so, strip the parens
        match = self.titleregex.match(source.title)
        if match is None:
            title = source.title
        else:
            title = match.group("title")
        # Let's abuse setFormat() a little, shall we?
        progressbar.setFormat(
            "%s \u2014 %s (%s)" % (title, timedelta(seconds=int(source.pos)), timedelta(seconds=int(source.duration)))
            )

    def onPlayerPositionNormal(self, source, srcdata):
        self.intransition  = False
        if not self.invstatusbars:
            self._status_update(self.pgbSongProgress, source)
            self.pgbSongProgressPrev.setFormat("Idle")
            self.pgbSongProgressPrev.setMaximum(100)
            self.pgbSongProgressPrev.setValue(0)
        else:
            self._status_update(self.pgbSongProgressPrev, source)
            self.pgbSongProgress.setFormat("Idle")
            self.pgbSongProgress.setMaximum(100)
            self.pgbSongProgress.setValue(0)
        self.ledViz.update_normal(srcdata)

    def onPlayerPositionTrans(self, prev, source, fac, prevdata, srcdata):
        if not self.intransition:
            self.intransition  = True
            self.invstatusbars = not self.invstatusbars
        if not self.invstatusbars:
            self._status_update(self.pgbSongProgress, source)
            self._status_update(self.pgbSongProgressPrev, prev)
        else:
            self._status_update(self.pgbSongProgressPrev, source)
            self._status_update(self.pgbSongProgress, prev)
        self.ledViz.update_crossfade(srcdata, prevdata, fac)



if __name__ == '__main__':
    parser = OptionParser(usage="%prog [options] [<file> ...]\n")
    parser.add_option("-o", "--out", default=None,
        help="Audio output device. See http://xiph.org/ao/doc/ for supported drivers. Defaults to pulse."
        )
    parser.add_option("-d", "--musicdir", help="Library directory", default=None)
    parser.add_option("-q", "--enqueue",  help="Enqueue the tracks named on the command line.", action="store_true", default=None)
    parser.add_option("-p", "--playlist", help="A file to initialize the playlist from.", default=None)
    parser.add_option("-w", "--writepls", help="A file to write the playlist into. Can be the same as -p.", default=None)
    parser.add_option("--web", dest="web", metavar="PORT",
        help="Enable the web interface on the given port (e.g. --web 8080).", default=None)
    parser.add_option("--uploaddir", dest="uploaddir", metavar="DIR",
        help="Enable file uploads in the web interface. Must be <musicdir> itself or a directory within it.", default=None)
    parser.add_option("--stop-on-sink-disconnect", dest="stop_on_sink_disconnect", action="store_true", default=None,
        help="Exit automatically if the PulseAudio sink currently in use (PULSE_SINK, "
             "or else PulseAudio's default) disappears, instead of continuing on "
             "whatever sink PulseAudio falls back to. Requires DBus.")
    options, posargs = parser.parse_args()

    conf_path = os.path.join(os.environ["HOME"], ".failplay", "failplay.conf")

    conf = ConfigParser()
    conf.read(conf_path)

    if conf.has_section("environment"):
        for key in conf.options("environment"):
            os.environ[key.upper()] = conf.get("environment", key)

    def getconf(value, default=None):
        if getattr(options, value) is not None:
            return getattr(options, value)
        if conf.has_option("options", value):
            return conf.get("options", value)
        return default

    app = QtWidgets.QApplication(sys.argv)
    ply = FailPlay(getconf("out", "pulse"), getconf("musicdir", os.environ["HOME"]))

    playlistfile = getconf("playlist")
    if playlistfile:
        print("Loading playlist from", playlistfile)
        ply.playlist.loadpls(playlistfile)

    enqueue = getconf("enqueue") in (True, "True")
    for filename in posargs:
        if enqueue:
            ply.playlist.enqueue(filename)
        else:
            ply.playlist.append(filename)

    if len(ply.playlist) == 0:
        run_init_wizard(conf_path)
        conf.read(conf_path)

        musicdir = getconf("musicdir", os.environ["HOME"])
        ply.library.setRootPath(musicdir)
        ply.lstLibrary.setRootIndex(ply.library.index(musicdir))

        playlistfile = getconf("playlist")
        if playlistfile:
            print("Loading playlist from", playlistfile)
            ply.playlist.loadpls(playlistfile)

    web_port = getconf("web")
    if web_port is not None:
        WebServer(
            ply.playlist, ply.player, getconf("musicdir", os.environ["HOME"]), int(web_port),
            uploaddir=getconf("uploaddir"),
        ).start()

    exit_code = 0
    if getconf("stop_on_sink_disconnect") in (True, "True"):
        sink_watchdog = SinkWatchdog(sink_name=os.environ.get("PULSE_SINK"))
        if sink_watchdog.active:
            def _on_sink_gone():
                global exit_code
                exit_code = EX_UNAVAILABLE
                print("Sink disconnected, exiting.")
                ply.close()
            sink_watchdog.sig_sink_gone.connect(_on_sink_gone)

    ply.show()
    ply.start()

    app.exec_()

    playlistfile = getconf("writepls")
    if playlistfile:
        print("Saving playlist to", playlistfile)
        ply.playlist.writepls(playlistfile)

    sys.exit(exit_code)
