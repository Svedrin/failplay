# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

import os, sys

from PyQt4 import Qt
from PyQt4 import QtCore
from PyQt4 import QtGui

from failaudio import Source, Player
from ui_failplay import Ui_MainWindow

class FailPlay(Ui_MainWindow, QtGui.QMainWindow ):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)

        self.setupUi(self)
        self.show()
    


if __name__ == '__main__':
    app = QtGui.QApplication( sys.argv )
    ply = FailPlay()

    app.exec_()
