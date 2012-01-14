# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from time import time

from PyQt4 import QtCore

import audioop
import ao
import audioread
import threading


class Source(QtCore.QObject):
    sig_start  = QtCore.SIGNAL( 'start(const QString)' )

    def __init__(self, path):
        QtCore.QObject.__init__(self)
        self.starttime = None
        self.path  = path
        self.fd    = audioread.audio_open(path)
        self.gen   = None

    def start(self):
        self.starttime = time()
        self.emit( Source.sig_start, self.path )

    @property
    def duration(self):
        return self.fd.duration

    @property
    def pos(self):
        return time() - self.starttime

    @property
    def data(self):
        if self.gen is None:
            self.gen = self.fd.read_data()
        return self.gen


class Playlist(QtCore.QObject):
    """ Playlist management object. """

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.playlist  = []
        self.jmpqueue  = []
        self.current   = None
        self.stopafter = None

    def prev(self):
        """ Move to the previous song. """
        if self.current == 0:
            self.current = len(self.playlist) - 1
        else:
            self.current -= 1
        return self.playlist[self.current]

    def next(self):
        """ Move to the next song. """
        if not self.playlist:
            raise StopIteration("No songs in playlist")
        if self.stopafter is not None and self.current == self.stopafter:
            self.stopafter = None
            raise StopIteration("Set to stop after this track")
        if self.jmpqueue:
            path = self.jmpqueue.pop(0)
            self.current = self.playlist.index(path)
        elif self.current is None or self.current == len(self.playlist) - 1:
            # Not yet started or at end of list
            self.current = 0
        else:
            self.current += 1
        return self.playlist[self.current]

    @property
    def path(self):
        """ The path of the current file. """
        return self.playlist[self.current]

    def append(self, path):
        """ Append a new file to the playlist. """
        if path not in self.playlist:
            self.playlist.append(path)
        return self

    def _remove(self, path):
        if path in self.playlist:
            if self.playlist.index(path) == self.current:
                if self.current > 0:
                    self.current -= 1
                else:
                    self.current = None

            self.playlist.remove(path)

    def remove(self, path):
        """ Remove a file from the playlist.

            If it is also in the queue, it will be dequeued first.
        """
        self.dequeue(path)
        self._remove(path)
        return self

    def insert(self, index, path):
        """ Insert a new file before the given index. """
        if path not in self.playlist:
            self.playlist.insert(index, path)
            if index <= self.current:
                self.current += 1
        return self

    def move(self, index, path):
        """ Move a file to the given index without changing its status in the queue. """
        self._remove(path)
        self.insert(path, index)
        return self

    def enqueue(self, path):
        """ Enqueue a file, automatically adding it to the playlist if necessary. """
        if path not in self.playlist:
            self.playlist.append(path)
        if path not in self.jmpqueue:
            self.jmpqueue.append(path)
        return self

    def dequeue(self, path):
        """ Remove a file from the queue without changing its status in the playlist. """
        if path in self.jmpqueue:
            self.jmpqueue.remove(path)
        return self

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


class Player(QtCore.QObject, threading.Thread):
    sig_transition_start = QtCore.SIGNAL( 'transition_start(const QObject, const QOBject)' )
    sig_transition_end   = QtCore.SIGNAL( 'transition_start(const QObject, const QOBject)' )

    sig_position_normal  = QtCore.SIGNAL( 'position_normal(const Object)' )
    sig_position_trans   = QtCore.SIGNAL( 'position_trans(const QObject, const QObject)' )

    def __init__(self, pcm, playlist):
        threading.Thread.__init__(self)
        QtCore.QObject.__init__(self)
        self.pcm      = ao.AudioDevice(pcm)
        self.source   = None
        self.playlist = playlist

    def next(self):
        """ Create a source for the next item in the playlist. """
        return Source( self.playlist.next() )

    def run(self):
        transtime = 6.0
        prev = None

        if self.source is None:
            self.source = self.next()
        self.source.start()

        while True:
            try:
                srcdata = self.source.data.next()
            except StopIteration:
                print "source ran out of data."
                break

            if prev is None:
                self.pcm.play( srcdata )
                self.emit(Player.sig_position_normal, self.source)

                if self.next is not None and self.source.duration - self.source.pos <= transtime:
                    print "Entering transition!"
                    prev = self.source
                    self.source = self.next()
                    self.source.start()
                    self.emit(Player.sig_transition_start, prev, self.source)

            else:
                try:
                    prevdata = prev.data.next()
                except StopIteration:
                    print "Old source done, leaving transition!"
                    self.emit(Player.sig_transition_end, prev, self.source)
                    prev = None
                    self.pcm.play( srcdata )
                    self.emit(Player.sig_position_normal, self.source)
                else:
                    fac = max( (prev.duration - prev.pos), 0 ) / transtime
                    self.emit(Player.sig_position_trans, self.source, prev)
                    if len(prevdata) < len(srcdata):
                        # The last chunk may be too short, causing audioop some pain. Screw it, then.
                        self.pcm.play( audioop.mul( srcdata, 2, 1 - fac ) )
                    else:
                        sample = audioop.add( audioop.mul( prevdata, 2, fac ), audioop.mul( srcdata, 2, 1 - fac ), 2 )
                        self.pcm.play( sample )

if __name__ == '__main__':
    p = Playlist()
    p.append("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 02 - Dreamscape.flac")
    p.append("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 10 - Stardust.flac")
    p.enqueue("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 06 - Fantasia.flac")

    eternity = Player("pulse", p)

    eternity.start()
    print "Playing!"
    eternity.join()

