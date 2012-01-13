# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from time import time

import audioop
import ao
import audioread


class Source(object):
    def __init__(self, path):
        self.starttime = None
        self.path  = path
        self.fd    = audioread.audio_open(path)
        self.gen   = None

    def start(self):
        self.starttime = time()

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



class Player(object):
    def __init__(self, pcm, source):
        self.pcm = pcm
        self.next   = None
        self.source = source

    def enqueue(self, next):
        self.next = next

    def play(self):
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

                if self.next is not None and self.source.duration - self.source.pos <= transtime:
                    print "Entering transition!"
                    prev = self.source
                    self.source = self.next
                    self.next = None
                    self.source.start()

            else:
                try:
                    prevdata = prev.data.next()
                except StopIteration:
                    print "Old source done, leaving transition!"
                    prev = None
                    self.pcm.play( srcdata )
                else:
                    fac = max( (prev.duration - prev.pos), 0 ) / transtime
                    if len(prevdata) < len(srcdata):
                        # The last sample may be too short, causing audioop some pain. Screw it, then.
                        self.pcm.play( audioop.mul( srcdata, 2, 1 - fac ) )
                    else:
                        sample = audioop.add( audioop.mul( prevdata, 2, fac ), audioop.mul( srcdata, 2, 1 - fac ), 2 )
                        self.pcm.play( sample )

pcm = ao.AudioDevice("pulse")

first = Source("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 02 - Dreamscape.flac")
last  = Source("/media/daten/Musik/Brian El - Spiritual Evolution/Bryan El - Spiritual Evolution - 10 - Stardust.flac")

#first = Source("/tmp/eins.mp3")
#last  = Source("/tmp/zwei.mp3")

eternity = Player(pcm, first)
eternity.enqueue(last)
eternity.play()

