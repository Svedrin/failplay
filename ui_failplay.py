# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'failplay.ui'
#
# Created: Thu Jan 19 20:00:11 2012
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
        MainWindow.resize(632, 469)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.splitter = QtGui.QSplitter(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.lstLibrary = QtGui.QListWidget(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(5)
        sizePolicy.setHeightForWidth(self.lstLibrary.sizePolicy().hasHeightForWidth())
        self.lstLibrary.setSizePolicy(sizePolicy)
        self.lstLibrary.setObjectName(_fromUtf8("lstLibrary"))
        self.lstPlaylist = QtGui.QTableView(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(5)
        sizePolicy.setHeightForWidth(self.lstPlaylist.sizePolicy().hasHeightForWidth())
        self.lstPlaylist.setSizePolicy(sizePolicy)
        self.lstPlaylist.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.lstPlaylist.setDragDropMode(QtGui.QAbstractItemView.InternalMove)
        self.lstPlaylist.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.lstPlaylist.setObjectName(_fromUtf8("lstPlaylist"))
        self.verticalLayout_2.addWidget(self.splitter)
        self.horizontalLayout_2 = QtGui.QHBoxLayout()
        self.horizontalLayout_2.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self.horizontalLayout_2.setObjectName(_fromUtf8("horizontalLayout_2"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
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
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
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
        self.menubar.setGeometry(QtCore.QRect(0, 0, 632, 22))
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

