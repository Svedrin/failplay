#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os, sys

from datetime     import timedelta
from optparse     import OptionParser
from ConfigParser import ConfigParser

from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui

from failaudio   import Playlist, Player
from ui_failplay import Ui_MainWindow


class FailPlay(Ui_MainWindow, QtGui.QMainWindow ):
    def __init__(self, outdev, librarydir=os.environ["HOME"]):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        self.playlist = Playlist()
        self.player   = Player(outdev, self.playlist)

        self.setupUi(self)

        self.connect( self.player,           Player.sig_stopped,             self.close                )

        self.connect( self.player,           Player.sig_position_normal,     self.status_update_normal )
        self.connect( self.player,           Player.sig_position_trans,      self.status_update_trans  )

        self.connect( self.lstLibrary,  QtCore.SIGNAL("itemDoubleClicked(QListWidgetItem *)"), self.append )

        self.connect( self.lstPlaylist, QtCore.SIGNAL("doubleClicked(QModelIndex)"), self.toggleQueue )

        self.playlist.currentBg = QtGui.QBrush(Qt.Qt.cyan, Qt.Qt.SolidPattern)
        self.lstPlaylist.setModel(self.playlist)

        # build playlist context menu
        self.actRemove = QtGui.QAction("Remove", self.lstPlaylist)
        self.connect( self.actRemove, QtCore.SIGNAL("triggered(bool)"), self.remove)
        self.lstPlaylist.insertAction(None, self.actRemove)

        self.actEnqueue = QtGui.QAction("Enqueue", self.lstPlaylist)
        self.connect( self.actEnqueue, QtCore.SIGNAL("triggered(bool)"), self.enqueue)
        self.lstPlaylist.insertAction(None, self.actEnqueue)

        self.actDequeue = QtGui.QAction("Dequeue", self.lstPlaylist)
        self.connect( self.actDequeue, QtCore.SIGNAL("triggered(bool)"), self.dequeue)
        self.lstPlaylist.insertAction(None, self.actDequeue)

        self.actRepeat = QtGui.QAction("Repeat", self.lstPlaylist)
        self.connect( self.actRepeat, QtCore.SIGNAL("triggered(bool)"), self.repeat)
        self.lstPlaylist.insertAction(None, self.actRepeat)

        self.actStopAfter = QtGui.QAction("Stop after this track", self.lstPlaylist)
        self.connect( self.actStopAfter, QtCore.SIGNAL("triggered(bool)"), self.stopafter)
        self.lstPlaylist.insertAction(None, self.actStopAfter)

        # populate library list
        musicfiles = os.listdir(librarydir)
        musicfiles.sort()
        for fname in musicfiles:
            path = os.path.join(librarydir, fname)
            if os.path.isfile(path):
                item = QtGui.QListWidgetItem()
                item.setData(Qt.Qt.DisplayRole, fname)
                item.setData(Qt.Qt.UserRole, path)
                self.lstLibrary.addItem(item)

        self.show()

    def start(self):
        self.player.start()

    def append(self, item):
        path = item.data(Qt.Qt.UserRole).toString().toLocal8Bit().data()
        self.playlist.append( path )

    def toggleQueue(self, index):
        self.playlist.toggleQueue( self.playlist[index] )

    def remove(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.remove( self.playlist[index] )

    def enqueue(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.enqueue( self.playlist[index] )

    def dequeue(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.dequeue( self.playlist[index] )

    def repeat(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.toggleRepeat( self.playlist[index] )

    def stopafter(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.toggleStopAfter( self.playlist[index] )

    def closeEvent(self, ev):
        self.player.stop()
        QtGui.QMainWindow.closeEvent(self, ev)

    def _status_update(self, progressbar, source):
        progressbar.setMaximum(source.duration)
        progressbar.setValue(source.pos)
        # Let's abuse setFormat() a little, shall we?
        progressbar.setFormat(
            u"%s — %s (%s)" % (source.title, timedelta(seconds=int(source.pos)), timedelta(seconds=int(source.duration)))
            )

    def status_update_normal(self, source):
        self._status_update(self.pgbSongProgress, source)
        self.pgbSongProgressPrev.setFormat("Idle")
        self.pgbSongProgressPrev.setMaximum(100)
        self.pgbSongProgressPrev.setValue(0)
        self.sldCrossfade.setValue(100)

    def status_update_trans(self, prev, source, fac):
        self._status_update(self.pgbSongProgress, source)
        self._status_update(self.pgbSongProgressPrev, prev)
        self.sldCrossfade.setValue((1 - fac) * 100)



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
        if enqueue:
            ply.playlist.enqueue(filename)
        else:
            ply.playlist.append(filename)

    ply.start()

    app.exec_()

    playlistfile = getconf("writepls")
    if playlistfile:
        print "Saving playlist to", playlistfile
        ply.playlist.writepls(playlistfile)
