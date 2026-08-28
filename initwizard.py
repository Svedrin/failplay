#!/usr/bin/python
# -*- coding: utf-8 -*-
# kate: space-indent on; indent-width 4; replace-tabs on;

"""
 *  Copyright (C) 2026, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
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

import os
import random

from configparser import ConfigParser


AUDIO_EXTENSIONS = {'.mp3', '.flac', '.ogg', '.opus', '.m4a', '.wav', '.aac', '.wma', '.ape', '.mpc'}


def find_audio_files(musicdir):
    """ Recursively collect all audio files below musicdir. """
    audio_files = []
    if os.path.isdir(musicdir):
        for dirpath, _, filenames in os.walk(musicdir):
            for fname in filenames:
                if os.path.splitext(fname)[1].lower() in AUDIO_EXTENSIONS:
                    audio_files.append(os.path.join(dirpath, fname))
    return audio_files


def run_init_wizard(conf_path):
    """
    Ask a few questions on the console to get a sensible config to start from,
    then write it to conf_path (creating/updating its [options] section) and
    seed a playlist file with a single track so the player has something to
    work with right away.
    """
    print("Your playlist is empty. Let's set up a config to start from.")
    print()

    default_musicdir = os.path.join(os.environ["HOME"], "Music")
    musicdir = input("Music directory [%s]: " % default_musicdir).strip()
    if not musicdir:
        musicdir = default_musicdir
    musicdir = os.path.expanduser(musicdir)

    if not os.path.isdir(musicdir):
        print("Warning: '%s' does not exist or is not a directory." % musicdir)

    audio_files = find_audio_files(musicdir)
    default_track = random.choice(audio_files) if audio_files else ""

    if default_track:
        track = input("Track to add to the playlist [%s]: " % default_track).strip()
        if not track:
            track = default_track
    else:
        print("No audio files found in '%s'." % musicdir)
        track = input("Track to add to the playlist []: ").strip()
    track = os.path.expanduser(track) if track else ""

    default_pls = os.path.join(os.environ["HOME"], ".failplay", "playlist.pls")
    plsfile = input("Playlist file [%s]: " % default_pls).strip()
    if not plsfile:
        plsfile = default_pls
    plsfile = os.path.expanduser(plsfile)

    # Write config
    os.makedirs(os.path.dirname(conf_path), exist_ok=True)
    conf = ConfigParser()
    conf.read(conf_path)
    if not conf.has_section("options"):
        conf.add_section("options")
    conf.set("options", "musicdir", musicdir)
    conf.set("options", "playlist", plsfile)
    conf.set("options", "writepls", plsfile)
    with open(conf_path, "w") as f:
        conf.write(f)
    print("Config written to %s" % conf_path)

    # Write seed playlist
    os.makedirs(os.path.dirname(plsfile), exist_ok=True)
    with open(plsfile, "w", encoding="utf-8") as f:
        if track:
            title = os.path.splitext(os.path.basename(track))[0]
            f.write("[playlist]\nFile1=%s\nTitle1=%s\n\nNumberOfEntries=1\nVersion=2\n" % (track, title))
        else:
            f.write("[playlist]\n\nNumberOfEntries=0\nVersion=2\n")
    print("Playlist written to %s" % plsfile)
    print()
