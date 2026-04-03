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
import random

from datetime import timedelta
from optparse import OptionParser
from configparser import ConfigParser

from PyQt5 import Qt, QtCore, QtGui, QtWidgets

from failaudio   import Playlist, Player
from ui_failplay import Ui_MainWindow


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
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.remove(self.playlist[index])

    def onEnqueueTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.enqueue(self.playlist[index])

    def onDequeueTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.dequeue(self.playlist[index])

    def onRepeatTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.toggleRepeat(self.playlist[index])

    def onStopAfterTriggered(self):
        index = self.lstPlaylist.selectedIndexes()[0]
        self.playlist.toggleStopAfter(self.playlist[index])

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
            self.sldCrossfade.setValue(int(fac * 100))
            self.anzSong(srcdata)
            self.anzPrev(prevdata)
        else:
            self._status_update(self.pgbSongProgressPrev, source)
            self._status_update(self.pgbSongProgress, prev)
            self.sldCrossfade.setValue(int((1 - fac) * 100))
            self.anzPrev(srcdata)
            self.anzSong(prevdata)



AUDIO_EXTENSIONS = {'.mp3', '.flac', '.ogg', '.opus', '.m4a', '.wav', '.aac', '.wma', '.ape', '.mpc'}


def run_init_wizard(conf_path):
    print("Welcome to failplay! No config file found. Let's set things up.")
    print()

    default_musicdir = os.path.join(os.environ["HOME"], "Music")
    musicdir = input("Music directory [%s]: " % default_musicdir).strip()
    if not musicdir:
        musicdir = default_musicdir
    musicdir = os.path.expanduser(musicdir)

    if not os.path.isdir(musicdir):
        print("Warning: '%s' does not exist or is not a directory." % musicdir)

    default_pls = os.path.join(os.environ["HOME"], ".failplay", "playlist.pls")
    plsfile = input("Playlist file [%s]: " % default_pls).strip()
    if not plsfile:
        plsfile = default_pls
    plsfile = os.path.expanduser(plsfile)

    # Find a random audio file to seed the playlist
    seed_file = None
    audio_files = []
    if os.path.isdir(musicdir):
        for dirpath, _, filenames in os.walk(musicdir):
            for fname in filenames:
                if os.path.splitext(fname)[1].lower() in AUDIO_EXTENSIONS:
                    audio_files.append(os.path.join(dirpath, fname))
    if audio_files:
        seed_file = random.choice(audio_files)
        print("Seeding playlist with: %s" % seed_file)
    else:
        print("No audio files found in '%s'; playlist will be empty." % musicdir)

    # Write config
    os.makedirs(os.path.dirname(conf_path), exist_ok=True)
    conf = ConfigParser()
    conf["options"] = {
        "musicdir": musicdir,
        "playlist": plsfile,
        "writepls": plsfile,
    }
    with open(conf_path, "w") as f:
        conf.write(f)
    print("Config written to %s" % conf_path)

    # Write seed playlist
    os.makedirs(os.path.dirname(plsfile), exist_ok=True)
    with open(plsfile, "w", encoding="utf-8") as f:
        if seed_file:
            title = os.path.splitext(os.path.basename(seed_file))[0]
            f.write("[playlist]\nFile1=%s\nTitle1=%s\n\nNumberOfEntries=1\nVersion=2\n" % (seed_file, title))
        else:
            f.write("[playlist]\n\nNumberOfEntries=0\nVersion=2\n")
    print("Playlist written to %s" % plsfile)
    print()


if __name__ == '__main__':
    parser = OptionParser(usage="%prog [options] [<file> ...]\n")
    parser.add_option("-o", "--out", default=None,
        help="Audio output device. See http://xiph.org/ao/doc/ for supported drivers. Defaults to pulse."
        )
    parser.add_option("-d", "--musicdir", help="Library directory", default=None)
    parser.add_option("-q", "--enqueue",  help="Enqueue the tracks named on the command line.", action="store_true", default=None)
    parser.add_option("-p", "--playlist", help="A file to initialize the playlist from.", default=None)
    parser.add_option("-w", "--writepls", help="A file to write the playlist into. Can be the same as -p.", default=None)
    options, posargs = parser.parse_args()

    conf_path = os.path.join(os.environ["HOME"], ".failplay", "failplay.conf")

    if not os.path.exists(conf_path) and not posargs and options.playlist is None:
        run_init_wizard(conf_path)

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

    ply.show()
    ply.start()

    app.exec_()

    playlistfile = getconf("writepls")
    if playlistfile:
        print("Saving playlist to", playlistfile)
        ply.playlist.writepls(playlistfile)
