# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'failplay.ui'
#
# Created: Sun Jan 15 15:41:20 2012
#      by: PyQt4 UI code generator 4.9
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(667, 514)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.lstLibrary = QtGui.QListWidget(self.centralwidget)
        self.lstLibrary.setObjectName(_fromUtf8("lstLibrary"))
        self.horizontalLayout.addWidget(self.lstLibrary)
        self.lstPlaylist = PlaylistWidget(self.centralwidget)
        self.lstPlaylist.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.lstPlaylist.setDragEnabled(True)
        self.lstPlaylist.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.lstPlaylist.setObjectName(_fromUtf8("lstPlaylist"))
        self.horizontalLayout.addWidget(self.lstPlaylist)
        self.verticalLayout_2.addLayout(self.horizontalLayout)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.pgbSongProgress = QtGui.QProgressBar(self.centralwidget)
        self.pgbSongProgress.setProperty("value", 0)
        self.pgbSongProgress.setTextVisible(True)
        self.pgbSongProgress.setInvertedAppearance(False)
        self.pgbSongProgress.setObjectName(_fromUtf8("pgbSongProgress"))
        self.verticalLayout.addWidget(self.pgbSongProgress)
        self.pgbSongProgressPrev = QtGui.QProgressBar(self.centralwidget)
        self.pgbSongProgressPrev.setProperty("value", 0)
        self.pgbSongProgressPrev.setTextVisible(True)
        self.pgbSongProgressPrev.setInvertedAppearance(False)
        self.pgbSongProgressPrev.setObjectName(_fromUtf8("pgbSongProgressPrev"))
        self.verticalLayout.addWidget(self.pgbSongProgressPrev)
        self.horizontalLayout_2.addLayout(self.verticalLayout)
        self.sldCrossfade = QtGui.QSlider(self.centralwidget)
        self.sldCrossfade.setEnabled(False)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.sldCrossfade.sizePolicy().hasHeightForWidth())
        self.sldCrossfade.setSizePolicy(sizePolicy)
        self.sldCrossfade.setMaximum(100)
        self.sldCrossfade.setProperty("value", 100)
        self.sldCrossfade.setSliderPosition(100)
        self.sldCrossfade.setOrientation(QtCore.Qt.Vertical)
        self.sldCrossfade.setObjectName(_fromUtf8("sldCrossfade"))
        self.horizontalLayout_2.addWidget(self.sldCrossfade)
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 667, 22))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QtGui.QApplication.translate("MainWindow", "FailPlay", None, QtGui.QApplication.UnicodeUTF8))
        self.pgbSongProgress.setFormat(QtGui.QApplication.translate("MainWindow", "Idle", None, QtGui.QApplication.UnicodeUTF8))
        self.pgbSongProgressPrev.setFormat(QtGui.QApplication.translate("MainWindow", "Idle", None, QtGui.QApplication.UnicodeUTF8))

from playlistwidget import PlaylistWidget
