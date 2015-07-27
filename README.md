FailPlay
========

FailPlay is a media player with an extremely simplistic user interface combined with a set of unique features:

* Queue: Titles in the playlist can be enqueued to change the order in which tracks are played without changing the
  playlist.
* AutoStop: One track can be selected after which playing will stop. This can be any track you want, be it right in the
  middle of the playlist, after the last track of a queue, or in the middle of a queue. As soon as the selected title has
  been played, the player stops (read: exits).
* Repeat can be configured for one specific title, and will start as soon as that title is reached. When repeat is disabled
  for that title (or set for a different one), the playlist/queue will continue.
* If no track is configured to be the last one, playback will not end. Instead the whole playlist will repeat.
* The playlist and queue are saved between restarts, if you so choose. Format is a simple PLS file that should be compatible
  with other players (only tested with mplayer).
* Double-Clicking on a file adds it to the playlist, double-clicking in the playlist adds/removes the title from the queue.
* Crossfading between songs.
* Drag-and-Drop playlist reordering. (Yeah I know every player does this. FailPlay does too.)
* Aggressively simple user interface: One window, files on the left, playlist on the right, progress at the bottom, and
  a little playlist context menu to enable AutoStop/Repeat. That's it.

FailPlay doesn't (and probably never will) have:

* Play/Stop/Skip/Previous buttons. As long as it runs, it plays. Without interruption.
* Volume change thingy. Use your remote. Or `pavucontrol`.
* Support for streams, as you don't gain anything from the cool playlist features for streams.

Here's a ![Screenshot](https://bitbucket.org/Svedrin/failplay/downloads/failplay.png).

FailAudio
=========

FailPlay also comes with a command-line player named `failaudio`, which has the same features (crossfade, queue) but is intended
for more ad-hoc use.

Note that unlike FailPlay, `failaudio` does *not* infinitely repeat its playlist, but plays it only once.

Requirements
============

* python-pyao
* python-qt4
* libavcodec-dev, libavformat-dev, python-dev (for building myffmpeg)

Config
======

FailPlay doesn't really need much configuration, but setting a bit of stuff in //~~/.failplay/failplay.conf// does make life more convenient. Here's my config file:

    [options]
    musicdir = /media/daten/Musik
    playlist = /home/svedrin/.failplay/failplay.pls
    writepls = /home/svedrin/.failplay/failplay.pls
    enqueue  = True
    out = pulse

    [environment]
    PULSE_SERVER = tcp:gatekeeper

Variables in the `[environment]` section will be exported before initializing audio output, so it can be used e.g. to
connect to a remote PulseAudio server. The `options` section accepts the same variables that can also be given on the
command line as long options.

FailAudio supports a config file as well, and evaluates `~/.failplay/failaudio.conf` in the same manner.


Bugs
====

When loading the next song, the player might cause audible lag of about half a second, which kinda sucks hard. (I just
found out that it doesn't happen when you have an SSD, though - so chances are this might not get fixed (by me). :P )
