# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'failplay.ui'
#
# Created: Fri Oct 18 22:11:29 2013
#      by: PyQt4 UI code generator 4.10.3
#
# WARNING! All changes made in this file will be lost!

from PyQt4 import QtCore, QtGui

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    def _fromUtf8(s):
        return s

try:
    _encoding = QtGui.QApplication.UnicodeUTF8
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig, _encoding)
except AttributeError:
    def _translate(context, text, disambig):
        return QtGui.QApplication.translate(context, text, disambig)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName(_fromUtf8("MainWindow"))
        MainWindow.resize(632, 662)
        self.centralwidget = QtGui.QWidget(MainWindow)
        self.centralwidget.setObjectName(_fromUtf8("centralwidget"))
        self.verticalLayout_4 = QtGui.QVBoxLayout(self.centralwidget)
        self.verticalLayout_4.setObjectName(_fromUtf8("verticalLayout_4"))
        self.splitter = QtGui.QSplitter(self.centralwidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.splitter.sizePolicy().hasHeightForWidth())
        self.splitter.setSizePolicy(sizePolicy)
        self.splitter.setOrientation(QtCore.Qt.Horizontal)
        self.splitter.setObjectName(_fromUtf8("splitter"))
        self.layoutWidget = QtGui.QWidget(self.splitter)
        self.layoutWidget.setObjectName(_fromUtf8("layoutWidget"))
        self.verticalLayout_2 = QtGui.QVBoxLayout(self.layoutWidget)
        self.verticalLayout_2.setMargin(0)
        self.verticalLayout_2.setObjectName(_fromUtf8("verticalLayout_2"))
        self.lstLibrary = LibraryView(self.layoutWidget)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(5)
        sizePolicy.setHeightForWidth(self.lstLibrary.sizePolicy().hasHeightForWidth())
        self.lstLibrary.setSizePolicy(sizePolicy)
        self.lstLibrary.setDragEnabled(True)
        self.lstLibrary.setDragDropMode(QtGui.QAbstractItemView.DragOnly)
        self.lstLibrary.setObjectName(_fromUtf8("lstLibrary"))
        self.verticalLayout_2.addWidget(self.lstLibrary)
        self.leLibraryFilter = QtGui.QLineEdit(self.layoutWidget)
        self.leLibraryFilter.setObjectName(_fromUtf8("leLibraryFilter"))
        self.verticalLayout_2.addWidget(self.leLibraryFilter)
        self.lstPlaylist = QtGui.QTableView(self.splitter)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.lstPlaylist.sizePolicy().hasHeightForWidth())
        self.lstPlaylist.setSizePolicy(sizePolicy)
        self.lstPlaylist.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.lstPlaylist.setAcceptDrops(True)
        self.lstPlaylist.setDragEnabled(True)
        self.lstPlaylist.setDragDropMode(QtGui.QAbstractItemView.DragDrop)
        self.lstPlaylist.setDefaultDropAction(QtCore.Qt.MoveAction)
        self.lstPlaylist.setSelectionMode(QtGui.QAbstractItemView.SingleSelection)
        self.lstPlaylist.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.lstPlaylist.setObjectName(_fromUtf8("lstPlaylist"))
        self.verticalLayout_4.addWidget(self.splitter)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName(_fromUtf8("horizontalLayout"))
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setSizeConstraint(QtGui.QLayout.SetMinimumSize)
        self.verticalLayout.setObjectName(_fromUtf8("verticalLayout"))
        self.anzSong = QFftAnalyzer(self.centralwidget)
        self.anzSong.setMinimumSize(QtCore.QSize(0, 100))
        self.anzSong.setObjectName(_fromUtf8("anzSong"))
        self.verticalLayout.addWidget(self.anzSong)
        self.pgbSongProgress = QtGui.QProgressBar(self.centralwidget)
        self.pgbSongProgress.setProperty("value", 0)
        self.pgbSongProgress.setTextVisible(True)
        self.pgbSongProgress.setInvertedAppearance(False)
        self.pgbSongProgress.setObjectName(_fromUtf8("pgbSongProgress"))
        self.verticalLayout.addWidget(self.pgbSongProgress)
        self.horizontalLayout.addLayout(self.verticalLayout)
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
        self.sldCrossfade.setOrientation(QtCore.Qt.Horizontal)
        self.sldCrossfade.setObjectName(_fromUtf8("sldCrossfade"))
        self.horizontalLayout.addWidget(self.sldCrossfade)
        self.verticalLayout_3 = QtGui.QVBoxLayout()
        self.verticalLayout_3.setObjectName(_fromUtf8("verticalLayout_3"))
        self.anzPrev = QFftAnalyzer(self.centralwidget)
        self.anzPrev.setMinimumSize(QtCore.QSize(0, 100))
        self.anzPrev.setObjectName(_fromUtf8("anzPrev"))
        self.verticalLayout_3.addWidget(self.anzPrev)
        self.pgbSongProgressPrev = QtGui.QProgressBar(self.centralwidget)
        self.pgbSongProgressPrev.setProperty("value", 0)
        self.pgbSongProgressPrev.setTextVisible(True)
        self.pgbSongProgressPrev.setInvertedAppearance(False)
        self.pgbSongProgressPrev.setObjectName(_fromUtf8("pgbSongProgressPrev"))
        self.verticalLayout_3.addWidget(self.pgbSongProgressPrev)
        self.horizontalLayout.addLayout(self.verticalLayout_3)
        self.verticalLayout_4.addLayout(self.horizontalLayout)
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtGui.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 632, 20))
        self.menubar.setObjectName(_fromUtf8("menubar"))
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtGui.QStatusBar(MainWindow)
        self.statusbar.setObjectName(_fromUtf8("statusbar"))
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(_translate("MainWindow", "FailPlay", None))
        self.leLibraryFilter.setPlaceholderText(_translate("MainWindow", "Search...", None))
        self.pgbSongProgress.setFormat(_translate("MainWindow", "Idle", None))
        self.pgbSongProgressPrev.setFormat(_translate("MainWindow", "Idle", None))

from libraryview import LibraryView
from analyzer import QFftAnalyzer
