# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

from time import time

from PyQt4 import QtCore

import audioop
import ao
import audioread
import threading

from ConfigParser import ConfigParser


class Source(QtCore.QObject):
    sig_start  = QtCore.SIGNAL( 'start(const QString)' )

    def __init__(self, path):
        QtCore.QObject.__init__(self)
        self.starttime = None
        self.path  = path
        self.fd    = audioread.audio_open(path)
        self.gen   = None
        self.title = path.rsplit( '/', 1 )[1].rsplit('.', 1)[0]


    def start(self):
        self.starttime = time()
        self.emit( Source.sig_start, self.path )

    def stop(self):
        self.fd.close()

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

    sig_append  = QtCore.SIGNAL( 'append(const QString)' )
    sig_insert  = QtCore.SIGNAL( 'insert(const int, const QString)' )
    sig_remove  = QtCore.SIGNAL( 'remove(const QString)' )
    sig_enqueue = QtCore.SIGNAL( 'enqueue(const QString)' )
    sig_dequeue = QtCore.SIGNAL( 'dequeue(const QString)' )

    def __init__(self):
        QtCore.QObject.__init__(self)
        self.playlist  = []
        self.jmpqueue  = []
        self.current   = None
        self.stopafter = None
        self.repeat    = None

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
        files.sort()
        for fileopt in files:
            self.append( pls.get("playlist", fileopt) )

        if pls.has_section("failplay"):
            def intOrNone(name):
                if pls.has_option("failplay", name):
                    value = pls.get("failplay", name)
                else:
                    value = "None"
                if value == "None":
                    value = None
                else:
                    value = int(value)
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

            fd.write("[failplay]\n")
            fd.write("StopAfter=%s\n" % self.stopafter)
            fd.write("Repeat=%s\n"    % self.repeat)
            fd.write("Current=%s\n"   % self.current)
            fd.write("Queue=%s\n"     % ' '.join([ str(self.playlist.index(path) + 1) for path in self.jmpqueue ]))

            self.playlist_dirty = False
            self.jmpqueue_dirty = False
        finally:
            fd.close()

        return self

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
        return self.playlist[self.current]

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

    def append(self, path):
        """ Append a new file to the playlist. """
        if path not in self.playlist:
            self.playlist_dirty = True
            self.playlist.append(path)
            self.emit(Playlist.sig_append, path)
        return self

    def _remove(self, path):
        if path in self.playlist:
            if self.playlist.index(path) == self.current:
                if self.current > 0:
                    self.current -= 1
                else:
                    self.current = None

            self.playlist_dirty = True
            self.playlist.remove(path)
            self.emit(Playlist.sig_remove, path)

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
            self.playlist_dirty = True
            self.playlist.insert(index, path)
            self.emit(Playlist.sig_insert, index, path)
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
            self.jmpqueue_dirty = True
            self.jmpqueue.append(path)
            self.emit(Playlist.sig_enqueue, path)
        return self

    def dequeue(self, path):
        """ Remove a file from the queue without changing its status in the playlist. """
        if path in self.jmpqueue:
            self.jmpqueue_dirty = True
            self.jmpqueue.remove(path)
            self.emit(Playlist.sig_dequeue, path)
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
        transtime = 6.0
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
                self.emit(Player.sig_stopped, "source ran out of data.")
                self.source.stop()
                break

            if prev is None:
                self.pcm.play( srcdata )
                self.emit(Player.sig_position_normal, self.source)

                if self.source.duration - self.source.pos <= transtime and not end_of_playlist:
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
                else:
                    fac = max( (prev.duration - prev.pos), 0 ) / transtime
                    self.emit(Player.sig_position_trans, prev, self.source, fac)
                    if len(prevdata) < len(srcdata):
                        # The last chunk may be too short, causing audioop some pain. Screw it, then.
                        self.pcm.play( audioop.mul( srcdata, 2, 1 - fac ) )
                    else:
                        sample = audioop.add( audioop.mul( prevdata, 2, fac ), audioop.mul( srcdata, 2, 1 - fac ), 2 )
                        self.pcm.play( sample )

        self.source.stop()
        self.emit(Player.sig_stopped, "end of playlist")


if __name__ == '__main__':
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


    p = Playlist()

    if options.playlist:
        print "Loading playlist from", options.playlist
        p.loadpls(options.playlist)

    for filename in posargs:
        if options.enqueue:
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
    player.connect( player, Player.sig_started,         printer.showstatus_started    )
    player.connect( player, Player.sig_stopped,         printer.showstatus_stop       )
    player.connect( player, Player.sig_stopped,         app.quit                      )

    print "OK, here we go - hit q to exit."

    player.start()

    app.exec_()

    if options.writepls:
        print "Saving playlist to", options.writepls
        p.writepls(options.writepls)
