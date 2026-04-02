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

import sys

from os.path import exists
from shutil import copyfile

from PyQt5 import Qt, QtCore
from PyQt5.QtCore import pyqtSignal

import audioop
import ao
from myffmpeg.ffmpeg import Decoder
import threading

from configparser import ConfigParser
from queue import Queue


class Source(QtCore.QObject):
    sig_start = pyqtSignal(str)

    def __init__(self, path):
        QtCore.QObject.__init__(self)
        self.path  = path
        self.fd    = Decoder(path)
        self.title = (path.rsplit('/', 1)[1] if "/" in path else path).rsplit('.', 1)[0]
        self.fd.dump_format()

        if "replaygain_track_gain" in self.fd.metadata:
            self.gain_db  = float(self.fd.metadata["replaygain_track_gain"].split()[0])
            self.gain_fac = 10 ** (self.gain_db / 10.)
            print("ReplayGain: %fdB = %f Gain" % (self.gain_db, self.gain_fac))
        else:
            self.gain_fac = 1

        self.in_gen   = self.fd.read()
        self.out_gen  = self.data()

    def start(self):
        self.sig_start.emit(self.path)

    def stop(self):
        pass

    @property
    def duration(self):
        return self.fd.duration

    @property
    def pos(self):
        return self.fd.position

    def data(self):
        for chunk in self.in_gen:
            if self.gain_fac == 1:
                yield chunk[0]
            else:
                yield audioop.mul(chunk[0], 2, self.gain_fac)

    def next(self):
        return next(self.out_gen)

class Playlist(QtCore.QAbstractTableModel):
    """ Playlist management object. """

    sig_append  = pyqtSignal(str)
    sig_insert  = pyqtSignal(int, str)
    sig_remove  = pyqtSignal(str)
    sig_enqueue = pyqtSignal(str)
    sig_dequeue = pyqtSignal(str)
    sig_datachg = pyqtSignal(QtCore.QModelIndex, QtCore.QModelIndex)

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.playlist  = []
        self.jmpqueue  = []
        self.current   = None
        self.stopafter = None
        self.repeat    = None

        self.currentBg = None

        self.playlist_dirty = False
        self.jmpqueue_dirty = False

    def loadpls(self, fpath):
        """ Load the playlist from a .pls file. Silently clears the current playlist. """
        pls = ConfigParser()
        if not pls.read(fpath):
            raise ValueError("Could not read file")

        self.playlist  = []
        self.jmpqueue  = []
        self.current   = None
        self.stopafter = None
        self.repeat    = None

        files = [opt for opt in pls.options("playlist") if opt.startswith("file")]
        files.sort(key=lambda x: int(x[4:]))  # sort numerically by FileXY
        self.beginInsertRows(QtCore.QModelIndex(), 0, len(files) - 1)
        for fileopt in files:
            path = pls.get("playlist", fileopt)
            if not exists(path):
                print("Input file '%s' does not exist! Adding it anyway though." % path)
            self.playlist.append(path)
            self.sig_append.emit(path)
        self.endInsertRows()

        if pls.has_section("failplay"):
            def intOrNone(name):
                if pls.has_option("failplay", name):
                    value = pls.get("failplay", name)
                else:
                    value = "None"
                if value == "None":
                    value = None
                else:
                    value = int(value) - 1
                return value

            self.stopafter = intOrNone("stopafter")
            self.current   = intOrNone("current")
            self.repeat    = intOrNone("repeat")

            if pls.has_option("failplay", "queue"):
                queuestr = pls.get("failplay", "queue").strip()
                if queuestr:
                    self.jmpqueue = [self.playlist[int(idx) - 1] for idx in queuestr.split(' ')]

        self.playlist_dirty = False
        self.jmpqueue_dirty = False
        return self

    def writepls(self, fpath):
        """ Write the current playlist to a file in .pls format. """
        if exists(fpath):
            copyfile(fpath, fpath + '~')
        with open(fpath, "w", encoding="utf-8") as fd:
            fd.write("[playlist]\n")
            for i, path in enumerate(self.playlist):
                i += 1
                fd.write("File%d=%s\n" % (i, path))
                fd.write("Title%d=%s\n" % (i, self._parse_title(path)))
                fd.write("\n")

            fd.write("NumberOfEntries=%d\n" % len(self.playlist))
            fd.write("Version=2\n")
            fd.write("\n")

            def intOrNone(something):
                if something is None:
                    return None
                return something + 1

            fd.write("[failplay]\n")
            fd.write("StopAfter=%s\n" % intOrNone(self.stopafter))
            fd.write("Repeat=%s\n"    % intOrNone(self.repeat))
            fd.write("Current=%s\n"   % intOrNone(self.current))
            fd.write("Queue=%s\n"     % ' '.join([str(self.playlist.index(path) + 1) for path in self.jmpqueue]))

            self.playlist_dirty = False
            self.jmpqueue_dirty = False

        return self

    def next(self):
        """ Move to the next song. """
        if self.current is not None:
            prevpath = self.playlist[self.current]
        else:
            prevpath = None

        if not self.playlist:
            raise StopIteration("No songs in playlist")
        if self.stopafter is not None and self.current == self.stopafter:
            self.stopafter = None
            raise StopIteration("Set to stop after this track")
        if self.repeat is not None and self.current == self.repeat:
            pass
        elif self.jmpqueue:
            self.jmpqueue_dirty = True
            path = self.jmpqueue.pop(0)
            self.sig_dequeue.emit(path)
            self.current = self.playlist.index(path)
        elif self.current is None or self.current == len(self.playlist) - 1:
            # Not yet started or at end of list
            self.current = 0
        else:
            self.current += 1

        nextpath = self.playlist[self.current]

        if not exists(nextpath):
            # skip
            return self.next()

        if prevpath is not None and prevpath != nextpath:  # don't emit twice on repeat
            self._emit_changed(prevpath)
        self._emit_changed(nextpath)
        return nextpath

    def peek_next(self):
        """ Get the song that is going to be played next. """
        if not self.playlist:
            return None
        if self.stopafter is not None and self.current == self.stopafter:
            return None
        if self.repeat is not None and self.current == self.repeat:
            return self.playlist[self.current]
        elif self.jmpqueue:
            return self.jmpqueue[0]
        elif self.current is None or self.current == len(self.playlist) - 1:
            # Not yet started or at end of list
            return self.playlist[0]
        else:
            return self.playlist[self.current + 1]

    @property
    def current_index(self):
        return self.index(self.current, 0)

    @property
    def dirty(self):
        """ True if there are unsaved changes. """
        return self.playlist_dirty or self.jmpqueue_dirty

    @property
    def path(self):
        """ The path of the current file. """
        return self.playlist[self.current]

    def _parse_title(self, path):
        return path.rsplit('/', 1)[1].rsplit('.', 1)[0]

    @property
    def title(self):
        return self._parse_title(self.path)

    def indexOf(self, path):
        return self.playlist.index(path)

    def __contains__(self, path):
        return path in self.playlist

    def append(self, path):
        """ Append a new file to the playlist. """
        if path not in self.playlist:
            self.beginInsertRows(QtCore.QModelIndex(), len(self), len(self))
            self.playlist_dirty = True
            self.playlist.append(path)
            self.endInsertRows()
            self.sig_append.emit(path)
        return self

    def _remove(self, path):
        idx = self.playlist.index(path)
        if self.current is not None and idx <= self.current:
            if self.current > 0:
                self.current -= 1
            else:
                self.current = None
        if self.repeat is not None:
            if idx == self.repeat:
                self.repeat = None
            elif idx < self.repeat:
                self.repeat -= 1
        if self.stopafter is not None:
            if idx == self.stopafter:
                self.stopafter = None
            elif idx < self.stopafter:
                self.stopafter -= 1

        self.playlist_dirty = True
        self.playlist.remove(path)
        self.sig_remove.emit(path)

    def remove(self, path):
        """ Remove a file from the playlist.

            If it is also in the queue, it will be dequeued first.
        """
        self.dequeue(path)
        if path in self.playlist:
            idx = self.playlist.index(path)
            self.beginRemoveRows(QtCore.QModelIndex(), idx, idx)
            self._remove(path)
            self.endRemoveRows()
        return self

    def _insert(self, index, path):
        self.playlist_dirty = True
        self.playlist.insert(index, path)
        self.sig_insert.emit(index, path)
        if self.current is not None and index <= self.current:
            self.current += 1
        if self.repeat is not None and index <= self.repeat:
            self.repeat += 1
        if self.stopafter is not None and index <= self.stopafter:
            self.stopafter += 1

    def insert(self, index, path):
        """ Insert a new file before the given index. """
        if path not in self.playlist:
            self.beginInsertRows(QtCore.QModelIndex(), index, index)
            self._insert(index, path)
            self.endInsertRows()
        return self

    def move(self, index, path):
        """ Move a file to the given index without changing its status in the queue. """
        oldidx = self.playlist.index(path)
        if oldidx == index:
            return self
        self.beginMoveRows(QtCore.QModelIndex(), oldidx, oldidx, QtCore.QModelIndex(), index)
        repeat    = (oldidx == self.repeat)
        stopafter = (oldidx == self.stopafter)
        self._remove(path)
        self._insert(index, path)
        if stopafter:
            self.stopafter = index
        if repeat:
            self.repeat = index
        self.endMoveRows()
        return self

    def enqueue(self, path):
        """ Enqueue a file, automatically adding it to the playlist if necessary. """
        if path not in self.playlist:
            self.playlist.append(path)
        if path not in self.jmpqueue:
            self.jmpqueue_dirty = True
            self.jmpqueue.append(path)
            self.sig_enqueue.emit(path)
            self._emit_changed(path)
        return self

    def dequeue(self, path):
        """ Remove a file from the queue without changing its status in the playlist. """
        if path in self.jmpqueue:
            self.jmpqueue_dirty = True
            self.jmpqueue.remove(path)
            self.sig_dequeue.emit(path)
            self._emit_changed(path)
        return self

    def toggleQueue(self, path):
        if path in self.jmpqueue:
            self.dequeue(path)
        else:
            self.enqueue(path)

    def toggleRepeat(self, path):
        idx = self.playlist.index(path)
        if self.repeat == idx:
            self.repeat = None
        else:
            oldidx = self.repeat
            self.repeat = idx
            if oldidx is not None:
                self._emit_changed(self.playlist[oldidx])
        self._emit_changed(path)

    def toggleStopAfter(self, path):
        idx = self.playlist.index(path)
        if self.stopafter == idx:
            self.stopafter = None
        else:
            oldidx = self.stopafter
            self.stopafter = idx
            if oldidx is not None:
                self._emit_changed(self.playlist[oldidx])
        self._emit_changed(path)

    def headerData(self, section, orientation, role=Qt.Qt.DisplayRole):
        if role != Qt.Qt.DisplayRole:
            return None

        if orientation == Qt.Qt.Horizontal:
            if section == 0:
                return "Track"
            elif section == 1:
                return "Flags"
        else:
            return str(section + 1)

    @property
    def qlen(self):
        """ Return the length of the queue. """
        return len(self.jmpqueue)

    def __len__(self):
        """ Return the length of the playlist. """
        return len(self.playlist)

    len = property(__len__)

    def __iter__(self):
        """ Iterate over the playlist. """
        while True:
            try:
                yield self.next()
            except StopIteration:
                return


    # QAbstractTableModel methods
    def _emit_changed(self, path):
        idx = self.index(path, 1)
        self.sig_datachg.emit(idx, idx)

    def __getitem__(self, index):
        """ Return the path of the title at <index>. Index may be an int or a QModelIndex. """
        if isinstance(index, QtCore.QModelIndex):
            return self.playlist[index.row()]
        return self.playlist[index]

    def index(self, path_or_index, column=0, parent=QtCore.QModelIndex()):
        if isinstance(path_or_index, int):
            return QtCore.QAbstractTableModel.index(self, path_or_index, column, parent)

        idx = self.playlist.index(path_or_index)
        return QtCore.QAbstractTableModel.index(self, idx, 0, QtCore.QModelIndex())

    def data(self, index, role=Qt.Qt.DisplayRole):
        if not index.isValid():
            return None
        path = self.playlist[index.row()]

        if role == Qt.Qt.BackgroundRole:
            if index.row() == self.current and self.currentBg is not None:
                return self.currentBg

        elif index.column() == 0:
            if role == Qt.Qt.DisplayRole:
                return self._parse_title(path)
            elif role == Qt.Qt.UserRole:
                return path

        elif index.column() == 1:
            if role == Qt.Qt.DisplayRole:
                modifiers = []
                if path in self.jmpqueue:
                    modifiers.append(str(self.jmpqueue.index(path) + 1))
                if index.row() == self.repeat:
                    modifiers.append('\u267b')  # ♻
                if index.row() == self.stopafter:
                    modifiers.append('\u25fe')  # ◾
                return ''.join(modifiers)

        return None

    def columnCount(self, parent=QtCore.QModelIndex()):
        return 2

    def rowCount(self, parent=QtCore.QModelIndex()):
        if parent.isValid():
            return 0
        return len(self)

    def supportedDragActions(self):
        return Qt.Qt.MoveAction

    def supportedDropActions(self):
        return Qt.Qt.CopyAction | Qt.Qt.MoveAction

    def mimeTypes(self):
        return ["text/uri-list"]

    def dropMimeData(self, data, action, row, column, parent):
        if action == Qt.Qt.IgnoreAction:
            return True
        if row == -1 and parent.isValid():
            row = parent.row()
        if data.hasUrls() and row != -1:
            for url in data.urls():
                url = url.path()
                if url in self:
                    self.move(row, url)
                elif row < len(self):
                    self.insert(row, url)
                else:
                    self.append(url)
                row += 1
            return True
        return False

    def mimeData(self, index):
        data = QtCore.QMimeData()
        data.setUrls([QtCore.QUrl(self[index[0]])])
        return data

    def flags(self, index):
        defaultFlags = QtCore.QAbstractTableModel.flags(self, index)
        if index.isValid():
            return Qt.Qt.ItemIsDragEnabled | Qt.Qt.ItemIsDropEnabled | defaultFlags
        else:
            return Qt.Qt.ItemIsDropEnabled | defaultFlags



class Player(QtCore.QThread):
    sig_transition_start = pyqtSignal(object, object)
    sig_transition_end   = pyqtSignal(object, object)

    sig_position_normal  = pyqtSignal(object, object)
    sig_position_trans   = pyqtSignal(object, object, float, object, object)

    sig_started          = pyqtSignal(object)
    sig_stopped          = pyqtSignal(str)

    def __init__(self, pcm, playlist):
        QtCore.QThread.__init__(self)
        self.pcm      = ao.AudioDevice(pcm)
        self.source   = None
        self.playlist = playlist
        self.shutdown = False

        self.preloaded = False
        self.preloader_queue = Queue()

        self.preloader_thread = threading.Thread(target=self.preloader)
        self.preloader_thread.daemon = True
        self.preloader_thread.start()

    def preloader(self):
        while True:
            path = self.preloader_queue.get()
            if not exists(path):
                continue
            # This is fucking brutal but it works
            with open(path, "rb") as fd:
                fd.read(1024**2)

    def preload(self):
        if not self.preloaded:
            self.preloaded = True
            nextpath = self.playlist.peek_next()
            if nextpath is not None:
                self.preloader_queue.put(nextpath)

    def next(self):
        """ Create a source for the next item in the playlist. """
        self.preloaded = False
        return Source(self.playlist.next())

    def stop(self):
        self.shutdown = True

    def run(self):
        transtime  = 6.0  # crossfade of 6 seconds...
        transearly = 1.4  # that starts a bit early because many tracks have tons of silence at the end
        prev = None
        end_of_playlist = False

        if self.source is None:
            try:
                self.source = self.next()
            except StopIteration as e:
                self.sig_stopped.emit(str(e))
                return

        self.source.start()
        self.sig_started.emit(self.source)

        while not self.shutdown:
            try:
                srcdata = self.source.next()
            except StopIteration:
                if not end_of_playlist:
                    self.source.stop()
                    print("Huh. Looks like the source file ended prematurely. No transition then.")
                    try:
                        self.source = self.next()
                    except StopIteration:
                        print("Also, there's no more items in the playlist, exiting.")
                    else:
                        print("Phew, got the next source. Go on people, nothing to see here.")
                        self.source.start()
                        self.sig_started.emit(self.source)
                        continue
                break
            except Exception as err:
                self.sig_stopped.emit("Error: " + str(err))
                self.source.stop()
                break

            if prev is None:
                self.pcm.play(srcdata)
                self.sig_position_normal.emit(self.source, srcdata)

                if self.source.duration - self.source.pos - transearly <= transtime + 1 and not end_of_playlist:
                    # We'll enter transition in a second, preload the next file.
                    self.preload()

                if self.source.duration - self.source.pos - transearly <= transtime and not end_of_playlist:
                    prev = self.source
                    try:
                        self.source = self.next()
                    except StopIteration:
                        end_of_playlist = True
                        self.source = prev
                        prev = None
                    else:
                        self.source.start()
                        self.sig_started.emit(self.source)
                        self.sig_transition_start.emit(prev, self.source)

            else:
                try:
                    prevdata = prev.next()
                except StopIteration:
                    self.sig_transition_end.emit(prev, self.source)
                    prev.stop()
                    prev = None
                    self.pcm.play(srcdata)
                    self.sig_position_normal.emit(self.source, srcdata)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    # some other error happened, just play the other stream in its correct volume
                    fac = max((prev.duration - prev.pos - transearly), 0) / transtime
                    self.sig_position_trans.emit(prev, self.source, fac, b"", srcdata)
                    self.pcm.play(audioop.mul(srcdata, 2, 1 - fac))
                else:
                    fac = max((prev.duration - prev.pos - transearly), 0) / transtime
                    self.sig_position_trans.emit(prev, self.source, fac, prevdata, srcdata)
                    if len(prevdata) != len(srcdata):
                        # The last chunk may be too short, causing audioop some pain.
                        print("Chunk size mismatch (prev=%d, src=%d)" % (len(prevdata), len(srcdata)))
                        if len(prevdata) < len(srcdata):
                            # looks like this is the case, work around it.
                            rest = srcdata[len(prevdata):]
                            srcdata = srcdata[:len(prevdata)]
                        else:
                            # doesn't look that way. screw it, then.
                            self.pcm.play(audioop.mul(srcdata, 2, 1 - fac))
                    else:
                        rest = None
                    sample = audioop.add(audioop.mul(prevdata, 2, fac), audioop.mul(srcdata, 2, 1 - fac), 2)
                    self.pcm.play(sample)
                    if rest is not None:
                        self.pcm.play(audioop.mul(rest, 2, 1 - fac))

        self.source.stop()
        self.sig_stopped.emit("end of playlist")


if __name__ == '__main__':
    import os
    import signal
    from optparse import OptionParser
    from datetime import timedelta

    parser = OptionParser(usage="%prog [options] [<file> ...]\n")
    parser.add_option("-o", "--out",
        help="Audio output device. See http://xiph.org/ao/doc/ for supported drivers. Defaults to pulse.",
        default="pulse"
        )
    parser.add_option("-p", "--playlist", help="A file to initialize the playlist from.")
    parser.add_option("-w", "--writepls", help="A file to write the playlist into. Can be the same as -p.")
    parser.add_option("-q", "--enqueue",  help="Enqueue the tracks named on the command line.", action="store_true", default=False)
    options, posargs = parser.parse_args()

    conf = ConfigParser()
    conf.read(os.path.join(os.environ["HOME"], ".failplay", "failaudio.conf"))

    if conf.has_section("environment"):
        for key in conf.options("environment"):
            os.environ[key.upper()] = conf.get("environment", key)

    def getconf(value, default=None):
        if getattr(options, value) is not None:
            return getattr(options, value)
        if conf.has_option("options", value):
            return conf.get("options", value)
        return default


    p = Playlist()

    playlistfile = getconf("playlist")
    if playlistfile:
        print("Loading playlist from", playlistfile)
        p.loadpls(playlistfile)

    enqueue = getconf("enqueue") in (True, "True")
    for filename in posargs:
        if enqueue:
            p.enqueue(filename)
        else:
            p.append(filename)

    if not playlistfile and posargs:
        p.toggleStopAfter(posargs[-1])

    app = QtCore.QCoreApplication([])

    player = Player(getconf("out", "pulse"), p)

    class ConPrinter(QtCore.QObject):
        class Colors:
            gray    = 30
            red     = 31
            green   = 32
            yellow  = 33
            blue    = 34
            magenta = 35
            cyan    = 36
            white   = 37
            crimson = 38

            class Highlighted:
                red     = 41
                green   = 42
                brown   = 43
                blue    = 44
                magenta = 45
                cyan    = 46
                gray    = 47
                crimson = 48

        def colorprint(self, color, text):
            sys.stdout.write("\033[1;%dm%s\033[1;m" % (color, text))

        def termclear(self):
            # \x1b[K = VT100 delete everything right of the cursor
            sys.stdout.write("\r\x1b[K")

        def sourcetext(self, source):
            return "%s \u2014 %s (%s)" % (source.title, timedelta(seconds=int(source.pos)), timedelta(seconds=int(source.duration)))

        def showstatus_normal(self, src, data):
            self.termclear()
            self.colorprint(ConPrinter.Colors.blue, self.sourcetext(src))
            sys.stdout.flush()

        def showstatus_transition(self, prev, src, fac, prevdata, srcdata):
            self.termclear()
            self.colorprint(ConPrinter.Colors.red,   self.sourcetext(prev))
            sys.stdout.write(" \u2192 ")
            self.colorprint(ConPrinter.Colors.green, self.sourcetext(src))
            sys.stdout.flush()

        def showstatus_started(self, src):
            self.termclear()
            print("Now playing:", src.title)
            sys.stdout.flush()

        def showstatus_stop(self, msg):
            self.termclear()
            print("Exit:", msg)
            sys.stdout.flush()

    printer = ConPrinter()

    player.sig_position_normal.connect(printer.showstatus_normal)
    player.sig_position_trans.connect(printer.showstatus_transition)
    player.sig_started.connect(printer.showstatus_started)
    player.sig_stopped.connect(printer.showstatus_stop)
    player.sig_stopped.connect(lambda msg: app.quit())

    print("OK, here we go - hit ^C to exit.")

    player.start()

    def sigint_handler(sig, frame):
        player.stop()
    signal.signal(signal.SIGINT, sigint_handler)

    app.exec_()

    playlistfile = getconf("writepls")
    if playlistfile:
        print("Saving playlist to", playlistfile)
        p.writepls(playlistfile)
