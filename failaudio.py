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
        self.playlist = []
        self.jmpqueue = []
        self.current  = None

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
            raise ValueError("No songs in playlist")
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
        return len(self.playlist)

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
        return len(self.playlist)

    def insert(self, index, path):
        """ Insert a new file before the given index. """
        if path not in self.playlist:
            self.playlist.insert(index, path)
            if index <= self.current:
                self.current += 1
        return len(self.playlist)

    def move(self, index, path):
        """ Move a file to the given index without changing its status in the queue. """
        self._remove(path)
        self.insert(path, index)

    def __len__(self):
        return len(self.playlist)

    def enqueue(self, path):
        """ Enqueue a file, automatically adding it to the playlist if necessary. """
        if path not in self.playlist:
            self.playlist.append(path)
        if path not in self.jmpqueue:
            self.jmpqueue.append(path)
        return len(self.jmpqueue)

    def dequeue(self, path):
        """ Remove a file from the queue without changing its status in the playlist. """
        if path in self.jmpqueue:
            self.jmpqueue.remove(path)
        return len(self.jmpqueue)



class Player(QtCore.QObject, threading.Thread):
    sig_transition_start = QtCore.SIGNAL( 'transition_start(const QObject, const QOBject)' )
    sig_transition_end   = QtCore.SIGNAL( 'transition_start(const QObject, const QOBject)' )

    sig_position_normal  = QtCore.SIGNAL( 'position_normal(const Object)' )
    sig_position_trans   = QtCore.SIGNAL( 'position_trans(const QObject, const QObject)' )

    def __init__(self, pcm):
        threading.Thread.__init__(self)
        QtCore.QObject.__init__(self)
        self.pcm    = ao.AudioDevice(pcm)
        self.next   = None
        self.source = None

    def enqueue(self, next):
        if self.source is None:
            self.source = next
        else:
            self.next = next

    def run(self):
        transtime = 6.0
        prev = None

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
                    self.source = self.next
                    self.next = None
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
    #first = Source("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 02 - Dreamscape.flac")
    #last  = Source("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 10 - Stardust.flac")

    #first = Source("/tmp/eins.mp3")
    #last  = Source("/tmp/zwei.mp3")

    eternity = Player("pulse")
    #eternity.enqueue(first)
    #eternity.enqueue(last)
    #eternity.start()

    later = Source("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 06 - Fantasia.flac")
    eternity.enqueue(later)
    eternity.start()
    print "Playing!"
    eternity.join()

