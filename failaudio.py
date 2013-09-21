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

from os.path import exists
from shutil import copyfile

from PyQt4 import Qt
from PyQt4 import QtCore

import audioop
import ao
from myffmpeg.ffmpeg import Decoder
import threading

from ConfigParser import ConfigParser


class Source(QtCore.QObject):
    sig_start  = QtCore.SIGNAL( 'start(const QString)' )

    def __init__(self, path):
        QtCore.QObject.__init__(self)
        self.path  = path
        self.fd    = Decoder(path)
        self.gen   = None
        self.title = path.rsplit( '/', 1 )[1].rsplit('.', 1)[0]
        self.fd.dump_format()

    def start(self):
        self.emit( Source.sig_start, self.path )

    def stop(self):
        pass

    @property
    def duration(self):
        return self.fd.duration

    @property
    def pos(self):
        return self.fd.position

    @property
    def _data(self):
        for chunk in self.fd.read():
            yield chunk[0]
        raise StopIteration

    @property
    def data(self):
        if self.gen is None:
            self.gen = self._data
        return self.gen


class Playlist(QtCore.QAbstractTableModel):
    """ Playlist management object. """

    sig_append  = QtCore.SIGNAL( 'append(const QString)' )
    sig_insert  = QtCore.SIGNAL( 'insert(const int, const QString)' )
    sig_remove  = QtCore.SIGNAL( 'remove(const QString)' )
    sig_enqueue = QtCore.SIGNAL( 'enqueue(const QString)' )
    sig_dequeue = QtCore.SIGNAL( 'dequeue(const QString)' )
    sig_datachg = QtCore.SIGNAL( 'dataChanged (const QModelIndex, const QModelIndex)' )

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
        files.sort( cmp=lambda a, b: cmp(int(a[4:]), int(b[4:])) ) # sort numerically by FileXY
        self.beginInsertRows(QtCore.QModelIndex(), 0, len(files) - 1)
        for fileopt in files:
            path = pls.get("playlist", fileopt)
            self.playlist.append(path)
            self.emit(Playlist.sig_append, path)
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
                    self.jmpqueue  = [ self.playlist[int(idx) - 1] for idx in queuestr.split(' ') ]

        self.playlist_dirty = False
        self.jmpqueue_dirty = False
        return self

    def writepls(self, fpath):
        """ Write the current playlist to a file in .pls format. """
        if exists( fpath ):
            copyfile( fpath, fpath+'~' )
        fd = open(fpath, "wb")
        try:
            fd.write("[playlist]\n")
            for i, path in enumerate(self.playlist):
                i += 1
                fd.write( "File%d=%s\n" % (i, path) )
                fd.write( "Title%d=%s\n" % (i, self._parse_title(path)) )
                fd.write( "\n" )

            fd.write("NumberOfEntries=%d\n" % len(self.playlist))
            fd.write("Version=2\n")
            fd.write( "\n" )

            def intOrNone(something):
                if something is None:
                    return None
                return something + 1

            fd.write("[failplay]\n")
            fd.write("StopAfter=%s\n" % intOrNone(self.stopafter))
            fd.write("Repeat=%s\n"    % intOrNone(self.repeat))
            fd.write("Current=%s\n"   % intOrNone(self.current))
            fd.write("Queue=%s\n"     % ' '.join([ str(self.playlist.index(path) + 1) for path in self.jmpqueue ]))

            self.playlist_dirty = False
            self.jmpqueue_dirty = False
        finally:
            fd.close()

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
            self.emit(Playlist.sig_dequeue, path)
            self.current = self.playlist.index(path)
        elif self.current is None or self.current == len(self.playlist) - 1:
            # Not yet started or at end of list
            self.current = 0
        else:
            self.current += 1

        nextpath = self.playlist[self.current]
        if prevpath is not None and prevpath != nextpath: # don't emit twice on repeat
            self._emit_changed(prevpath)
        self._emit_changed(nextpath)
        return nextpath

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
        return path.rsplit( '/', 1 )[1].rsplit('.', 1)[0]

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
            self.emit(Playlist.sig_append, path)
        return self

    def _remove(self, path):
        idx = self.playlist.index(path)
        if idx <= self.current:
            if self.current > 0:
                self.current -= 1
            else:
                self.current = None
        if idx == self.repeat:
            self.repeat = None
        elif idx < self.repeat:
            self.repeat -= 1
        if idx == self.stopafter:
            self.stopafter = None
        elif idx < self.stopafter:
            self.stopafter -= 1

        self.playlist_dirty = True
        self.playlist.remove(path)
        self.emit(Playlist.sig_remove, path)

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
        self.emit(Playlist.sig_insert, index, path)
        if index <= self.current:
            self.current += 1
        if index <= self.repeat:
            self.repeat += 1
        if index <= self.stopafter:
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
            self.emit(Playlist.sig_enqueue, path)
            self._emit_changed(path)
        return self

    def dequeue(self, path):
        """ Remove a file from the queue without changing its status in the playlist. """
        if path in self.jmpqueue:
            self.jmpqueue_dirty = True
            self.jmpqueue.remove(path)
            self.emit(Playlist.sig_dequeue, path)
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
                self._emit_changed( self.playlist[oldidx] )
        self._emit_changed(path)

    def toggleStopAfter(self, path):
        idx = self.playlist.index(path)
        if self.stopafter == idx:
            self.stopafter = None
        else:
            oldidx = self.stopafter
            self.stopafter = idx
            if oldidx is not None:
                self._emit_changed( self.playlist[oldidx] )
        self._emit_changed(path)

    def headerData(self, section, orientation, role):
        if role != Qt.Qt.DisplayRole:
            return None

        if orientation == Qt.Qt.Horizontal:
            if section == 0:
                return "Track"
            elif section == 1:
                return "Flags"

        else:
            return unicode(section + 1)

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
            yield self.next()


    # QAbstractTableModel methods
    def _emit_changed(self, path):
        idx = self.index(path, 1)
        self.emit( self.sig_datachg, idx, idx )

    def __getitem__(self, index):
        """ Return the path of the title at <index>. Index may be an int or a QModelIndex. """
        if isinstance(index, QtCore.QModelIndex):
            return self.playlist[index.row()]
        return self.playlist[index]

    def index(self, path_or_index, column=0, parent=QtCore.QModelIndex()):
        if isinstance( path_or_index, int ):
            return QtCore.QAbstractTableModel.index(self, path_or_index, column, parent)

        idx = self.playlist.index(path_or_index)
        return QtCore.QAbstractTableModel.index(self, idx, 0, QtCore.QModelIndex())


    def data(self, index, role):
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
                    modifiers.append( unicode(self.jmpqueue.index(path) + 1) )
                if index.row() == self.repeat:
                    modifiers.append( u'♻' )
                if index.row() == self.stopafter:
                    # http://www.decodeunicode.org/de/geometric_shapes
                    modifiers.append( u'◾' ) #■◾◼
                return ''.join(modifiers)

    def columnCount(self, parent):
        return 2

    def rowCount(self, parent):
        if parent != QtCore.QModelIndex():
            return 0
        return len(self)

    def supportedDragActions(self):
        return Qt.Qt.MoveAction

    def supportedDropActions(self):
        return Qt.Qt.CopyAction|Qt.Qt.MoveAction

    def mimeTypes(self):
        return ["text/uri-list"]

    def dropMimeData(self, data, action, row, column, parent):
        if action == Qt.Qt.IgnoreAction:
            return True
        if row == -1 and parent.isValid():
            row = parent.row()
        if data.hasUrls() and row != -1:
            for url in data.urls():
                url = url.path().toLocal8Bit().data()
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
        data.setUrls([ QtCore.QUrl(self[ index[0] ]) ])
        return data

    def flags(self, index):
        defaultFlags = QtCore.QAbstractTableModel.flags(self, index)
        if index.isValid():
            return Qt.Qt.ItemIsDragEnabled | Qt.Qt.ItemIsDropEnabled | defaultFlags
        else:
            return Qt.Qt.ItemIsDropEnabled | defaultFlags



class Player(QtCore.QObject, threading.Thread):
    sig_transition_start = QtCore.SIGNAL( 'transition_start(const PyQt_PyObject, const PyQt_PyObject)' )
    sig_transition_end   = QtCore.SIGNAL( 'transition_start(const PyQt_PyObject, const PyQt_PyObject)' )

    sig_position_normal  = QtCore.SIGNAL( 'position_normal(const PyQt_PyObject)' )
    sig_position_trans   = QtCore.SIGNAL( 'position_trans(const PyQt_PyObject, const PyQt_PyObject, const float)' )

    sig_started          = QtCore.SIGNAL( 'started(const PyQt_PyObject)' )
    sig_stopped          = QtCore.SIGNAL( 'stopped(const QString)' )

    def __init__(self, pcm, playlist):
        threading.Thread.__init__(self)
        QtCore.QObject.__init__(self)
        self.pcm      = ao.AudioDevice(pcm)
        self.source   = None
        self.playlist = playlist
        self.shutdown = False

    def next(self):
        """ Create a source for the next item in the playlist. """
        return Source( self.playlist.next() )

    def stop(self):
        self.shutdown = True

    def run(self):
        transtime  = 6.0 # crossfade of 6 seconds...
        transearly = 1.4 # that starts a bit early because many tracks have tons of silence at the end
        prev = None
        end_of_playlist = False

        if self.source is None:
            try:
                self.source = self.next()
            except StopIteration, e:
                self.emit(Player.sig_stopped, e.message)
                return

        self.source.start()
        self.emit(Player.sig_started, self.source)

        while not self.shutdown:
            try:
                srcdata = self.source.data.next()
            except StopIteration:
                if not end_of_playlist:
                    self.source.stop()
                    print "Huh. Looks like the source file ended prematurely. No transition then."
                    try:
                        self.source = self.next()
                    except StopIteration:
                        print "Also, there's no more items in the playlist, exiting."
                    else:
                        print "Phew, got the next source. Go on people, nothing to see here."
                        self.source.start()
                        self.emit(Player.sig_started, self.source)
                        continue
                break
            except Exception, err:
                self.emit(Player.sig_stopped, "Error: " + err.message)
                self.source.stop()
                break

            if prev is None:
                self.pcm.play( srcdata )
                self.emit(Player.sig_position_normal, self.source)

                if self.source.duration - self.source.pos - transearly <= transtime and not end_of_playlist:
                    #print "Entering transition!"
                    prev = self.source
                    try:
                        self.source = self.next()
                    except StopIteration:
                        end_of_playlist = True
                        self.source = prev
                        prev = None
                    else:
                        self.source.start()
                        self.emit(Player.sig_started, self.source)
                        self.emit(Player.sig_transition_start, prev, self.source)

            else:
                try:
                    prevdata = prev.data.next()
                except StopIteration:
                    #print "Old source done, leaving transition!"
                    self.emit(Player.sig_transition_end, prev, self.source)
                    prev.stop()
                    prev = None
                    self.pcm.play( srcdata )
                    self.emit(Player.sig_position_normal, self.source)
                except Exception:
                    import traceback
                    traceback.print_exc()
                    # some other error happened, just play the other stream in its correct volume
                    fac = max( (prev.duration - prev.pos - transearly), 0 ) / transtime
                    self.emit(Player.sig_position_trans, prev, self.source, fac)
                    self.pcm.play( audioop.mul( srcdata, 2, 1 - fac ) )
                else:
                    fac = max( (prev.duration - prev.pos - transearly), 0 ) / transtime
                    self.emit(Player.sig_position_trans, prev, self.source, fac)
                    if len(prevdata) != len(srcdata):
                        # The last chunk may be too short, causing audioop some pain. Screw it, then.
                        print "Chunk size mismatch (prev=%d, src=%d)" % (len(prevdata), len(srcdata))
                        self.pcm.play( audioop.mul( srcdata, 2, 1 - fac ) )
                    else:
                        sample = audioop.add( audioop.mul( prevdata, 2, fac ), audioop.mul( srcdata, 2, 1 - fac ), 2 )
                        self.pcm.play( sample )

        self.source.stop()
        self.emit(Player.sig_stopped, "end of playlist")


if __name__ == '__main__':
    import os
    from optparse import OptionParser

    parser = OptionParser(usage="%prog [options] [<file> ...]\n")
    parser.add_option( "-o", "--out",
        help="Audio output device. See http://xiph.org/ao/doc/ for supported drivers. Defaults to pulse.",
        default="pulse"
        )
    parser.add_option( "-p", "--playlist", help="A file to initialize the playlist from.")
    parser.add_option( "-w", "--writepls", help="A file to write the playlist into. Can be the same as -p.")
    parser.add_option( "-q", "--enqueue",  help="Enqueue the tracks named on the command line.", action="store_true", default=False)
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
        print "Loading playlist from", playlistfile
        p.loadpls(playlistfile)

    enqueue = getconf("enqueue") in (True, "True")
    for filename in posargs:
        if enqueue:
            p.enqueue(filename)
        else:
            p.append(filename)


    app = QtCore.QCoreApplication([])

    player = Player("pulse", p)

    class ConPrinter(QtCore.QObject):
        def showstatus_normal(self, src):
            # \x1b[K = VT100 delete everything right of the cursor
            print "\r\x1b[K", src.title, src.pos,

        def showstatus_transition(self, prev, src):
            # \x1b[K = VT100 delete everything right of the cursor
            print "\r\x1b[K", prev.title, prev.pos, u'→', src.title + src.pos,

        def showstatus_started(self, src):
            print "Now playing:", src.title

        def showstatus_stop(self, msg):
            print "Exit:", msg

    printer = ConPrinter()

    #player.connect( player, Player.sig_position_normal, printer.showstatus_normal     )
    #player.connect( player, Player.sig_position_trans,  printer.showstatus_transition )
    player.connect( player, Player.sig_started, printer.showstatus_started )
    player.connect( player, Player.sig_stopped, printer.showstatus_stop    )
    player.connect( player, Player.sig_stopped, app.quit )

    print "OK, here we go - hit q to exit."

    player.start()

    app.exec_()

    playlistfile = getconf("writepls")
    if playlistfile:
        print "Saving playlist to", playlistfile
        p.writepls(playlistfile)
