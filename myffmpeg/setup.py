# -*- coding: utf-8 -*-

"""
 *  This script uses distutils to build and install the ffmpeg
 *  Python module.
 *
 *  Usage:
 *    python setup.py build
 *      Compile the modules.
 *
 *    python setup.py install
 *      Install the modules into the Python module directory, usually
 *        /usr/lib/python<version>/site-packages.
 *      Note that this step is not necessary if you only want to use
 *      the modules temporarily for testing, as modules can also be
 *      loaded from the current working directory.
 *
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

from distutils.core import setup, Extension

ffmpegmodule = Extension(
	'_ffmpeg',
	sources   = ['ffmpegmodule.c'],
	libraries = ["avcodec", "avformat", "avutil", "avresample"]
	)

setup(
	name = 'myffmpeg',
	version = '1.0',
	description = "Python module that allows decoding and resampling of audio files using the ffmpeg libraries",
	keywords    = ["ffmpeg", "lavc", "libavcodec", "libavformat", "decoding", "decoder", "resampling", "resampler", "audio"],
	ext_modules = [ffmpegmodule],
	py_modules  = ["ffmpeg"],
	author="Michael Ziegler",
	author_email='diese-addy@funzt-halt.net',
	url='http://bitbucket.org/Svedrin/failplay/src/tip/myffmpeg',
	download_url='https://bitbucket.org/Svedrin/failplay/downloads/myffmpeg-1.0.tar.gz',
	classifiers=[
		'Development Status :: 5 - Production/Stable',
		'Intended Audience :: Developers',
		'License :: OSI Approved :: GNU General Public License (GPL)',
		'Operating System :: OS Independent',
		'Programming Language :: Python :: Implementation :: CPython',
		'Topic :: Software Development :: Libraries :: Python Modules',
		'Topic :: Multimedia :: Sound/Audio'],
	)

