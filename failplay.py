# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os, sys

from optparse import OptionParser
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

        self.connect( self.btnPlayPause,     QtCore.SIGNAL("clicked(bool)"), self.play_pause           )

        self.connect( self.player,           Player.sig_started,             self.update_playlist      )
        self.connect( self.playlist,         Playlist.sig_append,            self.update_playlist      )
        self.connect( self.playlist,         Playlist.sig_insert,            self.update_playlist      )
        self.connect( self.playlist,         Playlist.sig_remove,            self.update_playlist      )
        self.connect( self.playlist,         Playlist.sig_enqueue,           self.update_playlist      )
        self.connect( self.playlist,         Playlist.sig_dequeue,           self.update_playlist      )

        self.connect( self.player,           Player.sig_position_normal,     self.status_update_normal )
        self.connect( self.player,           Player.sig_position_trans,      self.status_update_trans  )

        self.connect( self.lstLibrary, QtCore.SIGNAL("itemDoubleClicked(QListWidgetItem *)"), self.append )

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

    def play_pause(self, checked):
        pass

    def skip(self, checked):
        pass

    def previous(self, checked):
        pass

    def stop(self, checked):
        pass

    def start(self):
        self.player.start()

    def append(self, item):
        path = item.data(Qt.Qt.UserRole).toString().toLocal8Bit().data()
        self.playlist.append( path )

    def remove(self):
        path = self.lstPlaylist.currentItem().data(Qt.Qt.UserRole).toString().toLocal8Bit().data()
        self.playlist.remove(path)

    def enqueue(self):
        path = self.lstPlaylist.currentItem().data(Qt.Qt.UserRole).toString().toLocal8Bit().data()
        self.playlist.enqueue(path)

    def dequeue(self):
        path = self.lstPlaylist.currentItem().data(Qt.Qt.UserRole).toString().toLocal8Bit().data()
        self.playlist.dequeue(path)

    def repeat(self):
        path = self.lstPlaylist.currentItem().data(Qt.Qt.UserRole).toString().toLocal8Bit().data()
        idx = self.playlist.playlist.index(path)
        if self.playlist.repeat == idx:
            self.playlist.repeat = None
        else:
            self.playlist.repeat = idx
        self.update_playlist()

    def stopafter(self):
        path = self.lstPlaylist.currentItem().data(Qt.Qt.UserRole).toString().toLocal8Bit().data()
        idx = self.playlist.playlist.index(path)
        if self.playlist.stopafter == idx:
            self.playlist.stopafter = None
        else:
            self.playlist.stopafter = idx
        self.update_playlist()

    def closeEvent(self, ev):
        self.player.stop()
        QtGui.QMainWindow.closeEvent(self, ev)

    def status_update_normal(self, source):
        self.pgbSongProgress.setMaximum(source.duration)
        self.pgbSongProgress.setValue(source.pos)
        self.lblTime.setText("%.3f" % source.pos)

    def status_update_trans(self, prev, source):
        self.pgbSongProgress.setMaximum(source.duration)
        self.pgbSongProgress.setValue(source.pos)
        self.lblTime.setText("%.3f\n%.3f" % (prev.pos, source.pos))

    def update_playlist(self):
        self.lstPlaylist.clear()
        print "Redraw.", self.playlist.current
        for idx, path in enumerate(self.playlist.playlist):
            item = QtGui.QListWidgetItem()

            display = path.rsplit( '/', 1 )[1].rsplit('.', 1)[0]
            modifiers = []
            if path in self.playlist.jmpqueue:
                modifiers.append( unicode(self.playlist.jmpqueue.index(path) + 1) )
            if idx == self.playlist.repeat:
                modifiers.append( u'♻' )
            if idx == self.playlist.stopafter:
                # http://www.decodeunicode.org/de/geometric_shapes
                modifiers.append( u'◾' ) #■◾◼
            if modifiers:
                display += " [%s]" % ''.join(modifiers)
            item.setData(Qt.Qt.DisplayRole, display)

            item.setData(Qt.Qt.UserRole, path)

            if idx == self.playlist.current:
                item.setBackground( QtGui.QBrush(Qt.Qt.cyan, Qt.Qt.SolidPattern) )

            self.lstPlaylist.addItem(item)


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
