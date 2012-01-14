# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os, sys

from optparse import OptionParser

from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui

from failaudio import Source, Player
from ui_failplay import Ui_MainWindow

class FailPlay(Ui_MainWindow, QtGui.QMainWindow ):
    def __init__(self, outdev):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        self.player = Player(outdev)

        self.setupUi(self)

        self.connect( self.btnPlayPause,     QtCore.SIGNAL("clicked(bool)"), self.playPause            )
        self.connect( self.player,           Player.sig_position_normal,     self.status_update_normal )
        self.connect( self.player,           Player.sig_position_trans,      self.status_update_trans  )

        self.show()

    def playPause(self, checked):
        pass

    def skip(self, checked):
        pass

    def previous(self, checked):
        pass

    def stop(self, checked):
        pass

    def status_update_normal(self, source):
        self.lblTime.setText("%.3f" % source.pos)

    def status_update_trans(self, prev, source):
        self.lblTime.setText("%.3f\n%.3f" % (prev.pos, source.pos))


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option( "-o", "--out",
        help="Audio output device. See http://xiph.org/ao/doc/ for supported drivers. Defaults to pulse.",
        default="pulse"
        )
    options, posargs = parser.parse_args()

    app = QtGui.QApplication( sys.argv )
    ply = FailPlay(options.out)

    last  = Source("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 10 - Stardust.flac")
    later = Source("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 06 - Fantasia.flac")
    ply.player.enqueue(last)
    ply.player.enqueue(later)
    ply.player.start()


    app.exec_()
