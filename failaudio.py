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


class Player(QtCore.QObject, threading.Thread):
    sig_transition_start = QtCore.SIGNAL( 'transition_start(const QString, const QString)' )
    sig_transition_end   = QtCore.SIGNAL( 'transition_start(const QString, const QString)' )

    sig_position_normal  = QtCore.SIGNAL( 'position_normal(const QString, const float)' )
    sig_position_trans   = QtCore.SIGNAL( 'position_trans(const QString, const float, const QString, const float)' )

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
                self.emit(Player.sig_position_normal, self.source.path, self.source.pos)

                if self.next is not None and self.source.duration - self.source.pos <= transtime:
                    print "Entering transition!"
                    prev = self.source
                    self.source = self.next
                    self.next = None
                    self.source.start()
                    self.emit(Player.sig_transition_start, prev.path, self.source.path)

            else:
                try:
                    prevdata = prev.data.next()
                except StopIteration:
                    print "Old source done, leaving transition!"
                    self.emit(Player.sig_transition_end, prev.path, self.source.path)
                    prev = None
                    self.pcm.play( srcdata )
                    self.emit(Player.sig_position_normal, self.source.path, self.source.pos)
                else:
                    fac = max( (prev.duration - prev.pos), 0 ) / transtime
                    self.emit(Player.sig_position_trans, self.source.path, self.source.pos, prev.path, prev.pos)
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

