# -*- coding: utf-8 -*-

"""
 *  This script uses distutils to build and install the FIS and Marvin
 *  Python modules.
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
 *  Copyright (C) 2009, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
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

fismodule = Extension(
	'_ffmpeg',
	sources   = ['ffmpegmodule.c'],
	libraries = ["avcodec", "avformat"]
	)

setup(
	name = 'PyFfmpeg',
	version = '1.0',
	description = 'Python module that allows decoding and resampling of audio files',
	ext_modules = [fismodule]
	)
