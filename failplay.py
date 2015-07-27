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
from ConfigParser import ConfigParser

from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui

from failaudio   import Playlist, Player
from ui_failplay import Ui_MainWindow


def mkIcon():
    data = ""
    for y in range(16):
        for x in range(16):
            v = (abs((8-y)/8.) <= abs(-(1/3.) * (x-8)/8. + (1/3.))) * 0xFF
            data += struct.pack( "BBB", v, v, v )
    img = QtGui.QImage(data, 16, 16, QtGui.QImage.Format_RGB888)
    pm = QtGui.QPixmap()
    pm.convertFromImage(img)
    return QtGui.QIcon(pm)



class FailPlay(Ui_MainWindow, QtGui.QMainWindow ):
    def __init__(self, outdev, librarydir=os.environ["HOME"]):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        self.playlist = Playlist()
        self.player   = Player(outdev, self.playlist)

        self.setupUi(self)

        self.connect( self.player, Player.sig_started, self.onPlayerStarted )
        self.connect( self.player, Player.sig_stopped, self.close )

        self.connect( self.player, Player.sig_position_normal, self.onPlayerPositionNormal )
        self.connect( self.player, Player.sig_position_trans,  self.onPlayerPositionTrans  )

        self.library = QtGui.QFileSystemModel()
        self.library.setRootPath(librarydir)
        self.lstLibrary.setModel(self.library)
        self.lstLibrary.setRootIndex(self.library.index(librarydir))
        self.library.setNameFilterDisables(False)
        self.lstLibrary.hideColumn(2)
        self.lstLibrary.hideColumn(3)

        self.connect( self.playlist,        Playlist.sig_datachg,                        self.onPlaylistChanged       )
        self.connect( self.leLibraryFilter, QtCore.SIGNAL("textEdited(QString)"),        self.onFilterEdited          )
        self.connect( self.lstLibrary,      QtCore.SIGNAL("doubleClicked(QModelIndex)"), self.onLibraryDoubleClicked  )
        self.connect( self.lstPlaylist,     QtCore.SIGNAL("doubleClicked(QModelIndex)"), self.onPlaylistDoubleClicked )

        self.playlist.currentBg = QtGui.QBrush(Qt.Qt.cyan, Qt.Qt.SolidPattern)
        self.lstPlaylist.setModel(self.playlist)

        hderp = self.lstPlaylist.horizontalHeader()
        hderp.setResizeMode(0, QtGui.QHeaderView.Stretch)
        hderp.resizeSection(1, 50)
        hderp.setResizeMode(1, QtGui.QHeaderView.Fixed)
        self.lstPlaylist.setHorizontalHeader(hderp)

        # build playlist context menu
        self.actRemove = QtGui.QAction("Remove", self.lstPlaylist)
        self.connect( self.actRemove, QtCore.SIGNAL("triggered(bool)"), self.onRemoveTriggered)
        self.actRemove.setShortcut(Qt.Qt.Key_Delete)
        self.lstPlaylist.insertAction(None, self.actRemove)

        self.actEnqueue = QtGui.QAction("Enqueue", self.lstPlaylist)
        self.connect( self.actEnqueue, QtCore.SIGNAL("triggered(bool)"), self.onEnqueueTriggered)
        self.actEnqueue.setShortcut(Qt.Qt.Key_Plus)
        self.lstPlaylist.insertAction(None, self.actEnqueue)

        self.actDequeue = QtGui.QAction("Dequeue", self.lstPlaylist)
        self.connect( self.actDequeue, QtCore.SIGNAL("triggered(bool)"), self.onDequeueTriggered)
        self.actDequeue.setShortcut(Qt.Qt.Key_Minus)
        self.lstPlaylist.insertAction(None, self.actDequeue)

        self.actRepeat = QtGui.QAction("Repeat", self.lstPlaylist)
        self.connect( self.actRepeat, QtCore.SIGNAL("triggered(bool)"), self.onRepeatTriggered)
        self.actRepeat.setShortcut(Qt.Qt.Key_R)
        self.lstPlaylist.insertAction(None, self.actRepeat)

        self.actStopAfter = QtGui.QAction("Stop after this track", self.lstPlaylist)
        self.connect( self.actStopAfter, QtCore.SIGNAL("triggered(bool)"), self.onStopAfterTriggered)
        self.actStopAfter.setShortcut(Qt.Qt.Key_S)
        self.lstPlaylist.insertAction(None, self.actStopAfter)

        def mkShortcut(key, callback):
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key), self)
            shortcut.setContext(Qt.Qt.ApplicationShortcut)
            self.connect( shortcut, QtCore.SIGNAL("activated()"), callback )
            return shortcut

        self.shortcutSpace   = mkShortcut(Qt.Qt.Key_Space,  self.onSpacePressed)
        self.shortcutEnd     = mkShortcut(Qt.Qt.Key_End,    self.onEndPressed)
        self.shortcutEsc     = mkShortcut(Qt.Qt.Key_Escape, self.onEscPressed)
        self.shortcutQuit    = mkShortcut(Qt.Qt.Key_Q,      self.close)

        self.setWindowIcon(mkIcon())

        self.invstatusbars = False
        self.intransition  = False
        self.selection     = None

        self.titleregex = re.compile(r"(?P<title>[^(]+)\([^)]+\)?$")

    def start(self):
        self.player.start()

    @property
    def selected_or_current_index(self):
        if self.lstPlaylist.selectedIndexes():
            return self.lstPlaylist.selectedIndexes()[0]
        return self.playlist.current_index

    def save_selection(self):
        if self.lstPlaylist.selectedIndexes():
            self.selection = self.lstPlaylist.selectedIndexes()[0]
        else:
            self.selection = None

    def restore_selection(self):
        if self.selection is not None:
            self.lstPlaylist.selectRow(self.selection.row())
        else:
            self.lstPlaylist.clearSelection()

    def onPlaylistDoubleClicked(self, index):
        """ Toggle repeat if currently playing track is doubleclicked, en/dequeue otherwise. """
        if index.row() == self.playlist.current:
            return self.playlist.toggleRepeat( self.playlist[ self.playlist.current ] )
        self.playlist.toggleQueue( self.playlist[index] )

    def onSpacePressed(self):
        """ Toggle repeat if currently playing track or none is selected, en/dequeue otherwise. """
        self.save_selection()
        self.onPlaylistDoubleClicked(self.selected_or_current_index)
        self.restore_selection()

    def onEndPressed(self):
        """ Toggle stopAfter on the selected track or the current one if none is selected. """
        self.save_selection()
        self.playlist.toggleStopAfter( self.playlist[self.selected_or_current_index] )
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
        self.lstPlaylist.scrollTo( self.playlist.index( self.playlist.current ), QtGui.QAbstractItemView.PositionAtCenter )

    def onLibraryDoubleClicked(self, index):
        self.playlist.append( unicode(self.library.filePath(index)) )

    def onRemoveTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.remove( self.playlist[index] )

    def onEnqueueTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.enqueue( self.playlist[index] )

    def onDequeueTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.dequeue( self.playlist[index] )

    def onRepeatTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.toggleRepeat( self.playlist[index] )

    def onStopAfterTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.toggleStopAfter( self.playlist[index] )

    def closeEvent(self, ev):
        self.player.stop()
        QtGui.QMainWindow.closeEvent(self, ev)

    def _status_update(self, progressbar, source):
        progressbar.setMaximum(source.duration)
        progressbar.setValue(source.pos)
        # see if the title is "asd - sdf (some stuff)", and if so, strip the parens
        match = self.titleregex.match(source.title)
        if match is None:
            title = source.title
        else:
            title = match.group("title")
        # Let's abuse setFormat() a little, shall we?
        progressbar.setFormat(
            u"%s — %s (%s)" % (title, timedelta(seconds=int(source.pos)), timedelta(seconds=int(source.duration)))
            )

    def onPlayerPositionNormal(self, source, srcdata):
        self.intransition  = False
        if not self.invstatusbars:
            self._status_update(self.pgbSongProgress, source)
            self.pgbSongProgressPrev.setFormat("Idle")
            self.pgbSongProgressPrev.setMaximum(100)
            self.pgbSongProgressPrev.setValue(0)
            self.sldCrossfade.setValue(0)
            self.anzSong(srcdata)
        else:
            self._status_update(self.pgbSongProgressPrev, source)
            self.pgbSongProgress.setFormat("Idle")
            self.pgbSongProgress.setMaximum(100)
            self.pgbSongProgress.setValue(0)
            self.sldCrossfade.setValue(100)
            self.anzPrev(srcdata)

    def onPlayerPositionTrans(self, prev, source, fac, prevdata, srcdata):
        if not self.intransition:
            self.intransition  = True
            self.invstatusbars = not self.invstatusbars
        if not self.invstatusbars:
            self._status_update(self.pgbSongProgress, source)
            self._status_update(self.pgbSongProgressPrev, prev)
            self.sldCrossfade.setValue(fac * 100)
            self.anzSong(srcdata)
            self.anzPrev(prevdata)
        else:
            self._status_update(self.pgbSongProgressPrev, source)
            self._status_update(self.pgbSongProgress, prev)
            self.sldCrossfade.setValue((1 - fac) * 100)
            self.anzPrev(srcdata)
            self.anzSong(prevdata)



if __name__ == '__main__':
    parser = OptionParser(usage="%prog [options] [<file> ...]\n")
    parser.add_option( "-o", "--out", default=None,
        help="Audio output device. See http://xiph.org/ao/doc/ for supported drivers. Defaults to pulse."
        )
    parser.add_option( "-d", "--musicdir", help="Library directory", default=None)
    parser.add_option( "-q", "--enqueue",  help="Enqueue the tracks named on the command line.", action="store_true", default=None)
    parser.add_option( "-p", "--playlist", help="A file to initialize the playlist from.", default=None)
    parser.add_option( "-w", "--writepls", help="A file to write the playlist into. Can be the same as -p.", default=None)
    options, posargs = parser.parse_args()

    conf = ConfigParser()
    conf.read(os.path.join(os.environ["HOME"], ".failplay", "failplay.conf"))

    if conf.has_section("environment"):
        for key in conf.options("environment"):
            os.environ[key.upper()] = conf.get("environment", key)

    def getconf(value, default=None):
        if getattr(options, value) is not None:
            return getattr(options, value)
        if conf.has_option("options", value):
            return conf.get("options", value)
        return default

    app = QtGui.QApplication( sys.argv )
    ply = FailPlay(getconf("out", "pulse"), getconf("musicdir", os.environ["HOME"]))

    playlistfile = getconf("playlist")
    if playlistfile:
        print "Loading playlist from", playlistfile
        ply.playlist.loadpls(playlistfile)

    enqueue = getconf("enqueue") in (True, "True")
    for filename in posargs:
        filename = filename.decode("utf-8")
        if enqueue:
            ply.playlist.enqueue(filename)
        else:
            ply.playlist.append(filename)

    ply.show()
    ply.start()

    app.exec_()

    playlistfile = getconf("writepls")
    if playlistfile:
        print "Saving playlist to", playlistfile
        ply.playlist.writepls(playlistfile)
