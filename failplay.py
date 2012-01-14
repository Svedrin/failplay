# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os, sys

from optparse import OptionParser

from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui

from failaudio   import Playlist, Player
from ui_failplay import Ui_MainWindow

class FailPlay(Ui_MainWindow, QtGui.QMainWindow ):
    def __init__(self, outdev):
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

    def closeEvent(self, ev):
        self.player.stop()
        QtGui.QMainWindow.closeEvent(self, ev)

    def status_update_normal(self, source):
        self.pgbSongProgress.setMaximum(source.duration)
        self.pgbSongProgress.setValue(source.pos)
        self.lblTime.setText("%.3f" % source.pos)

    def status_update_trans(self, prev, source):
        self.pgbSongProgress.setMaximum(prev.duration)
        self.pgbSongProgress.setValue(prev.pos)
        self.lblTime.setText("%.3f\n%.3f" % (prev.pos, source.pos))

    def update_playlist(self):
        self.lstPlaylist.clear()
        print "Redraw.", self.playlist.current
        for idx, path in enumerate(self.playlist.playlist):
            item = QtGui.QListWidgetItem()
            item.setData(Qt.Qt.DisplayRole, path.rsplit( '/', 1 )[1].rsplit('.', 1)[0])
            item.setData(Qt.Qt.UserRole, path)
            if idx == self.playlist.current:
                print "selected", path
                item.setBackground( QtGui.QBrush(Qt.Qt.cyan, Qt.Qt.SolidPattern) )
            self.lstPlaylist.addItem(item)


if __name__ == '__main__':
    parser = OptionParser(usage="%prog [options] [<file> ...]\n")
    parser.add_option( "-o", "--out",
        help="Audio output device. See http://xiph.org/ao/doc/ for supported drivers. Defaults to pulse.",
        default="pulse"
        )
    parser.add_option( "-p", "--playlist", help="A file to initialize the playlist from.")
    parser.add_option( "-w", "--writepls", help="A file to write the playlist into. Can be the same as -p.")
    options, posargs = parser.parse_args()


    app = QtGui.QApplication( sys.argv )
    ply = FailPlay(options.out)

    if options.playlist:
        ply.playlist.loadpls(options.playlist)

    for filename in posargs:
        ply.playlist.append(filename)

    if options.writepls:
        ply.playlist.writepls(options.writepls)

    ply.start()

    app.exec_()
