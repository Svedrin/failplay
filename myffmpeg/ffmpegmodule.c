/**
 *  Python Module to decode audio files using FFmpeg's lavc.
 *
 *  Copyright © 2009/10, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 *
 *  To compile this file into a Python module, run `python setup.py build`.
 *  The compiled binary will be put into build/lib.<platform>/fis.so.
 *
 *  The FFMPEG module is free software; you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation; either version 2 of the License, or
 *  (at your option) any later version.
 *
 *  This package is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 */

#include <Python.h>
#include "structmember.h"

#include <libavcodec/avcodec.h>
#include <libavformat/avformat.h>
#include <libavutil/mathematics.h>

#define MODULE_DOCSTRING "Python Module that decodes audio using FFmpeg's lavc."
#define DECODER_DOCSTRING ""\
	"This class handles decoding audio frames.\n"\
	"\n"\
	"Usage:\n"\
	">>> decoder = ffmpeg.Decoder('/path/to/some/file.ogg')\n"\
	">>> while True:\n"\
	"...     pcm.play( decoder.read() )\n"\
	""


static PyObject *FfmpegDecodeError;
static PyObject *FfmpegFileError;


typedef struct {
	PyObject_HEAD
	const char *infile;
	AVFormatContext *pFormatCtx;
	AVCodecContext *pCodecCtx;
} ffmpegObject;



static PyObject* ffmpeg_new( PyTypeObject* type, PyObject* args ){
	ffmpegObject* self;
	
	self = (ffmpegObject *) type->tp_alloc( type, 0 );
	
	if( self == NULL )
		return NULL;
	
	if( !PyArg_ParseTuple( args, "s", &self->infile ) )
		return NULL;
	
	if(avformat_open_input(&self->pFormatCtx, self->infile, NULL, NULL) < 0){
		PyErr_SetString(FfmpegFileError, "could not open infile");
		return NULL;
	}
	
	if (avformat_find_stream_info(self->pFormatCtx, NULL) < 0) {
		PyErr_SetString(FfmpegDecodeError, "could not find stream information");
		return NULL;
	}
	
	AVCodec *codec;
	
	int streamIdx = av_find_best_stream(self->pFormatCtx, AVMEDIA_TYPE_AUDIO, -1, -1, &codec, 0);
	if( streamIdx < 0 ){
		PyErr_SetString(FfmpegDecodeError, "could not find an audio stream");
		return NULL;
	}
	self->pCodecCtx = self->pFormatCtx->streams[streamIdx]->codec;
	
	if( avcodec_open2(self->pCodecCtx, codec, NULL) < 0 ){
		PyErr_SetString(FfmpegDecodeError, "could not open codec");
		return NULL;
	}
	
	return (PyObject *)self;
}

static void ffmpeg_dealloc( ffmpegObject* self ){
	avcodec_close(self->pCodecCtx);
	av_free(self->pCodecCtx);
// 	av_close_input_file(self->pFormatCtx);
}

static PyObject* ffmpeg_dump_format( ffmpegObject* self ){
	av_dump_format(self->pFormatCtx, 0, self->infile, 0);
	Py_RETURN_NONE;
}

static PyObject* ffmpeg_get_bitrate( ffmpegObject* self ){
	return Py_BuildValue( "i", self->pCodecCtx->bit_rate );
}

static PyObject* ffmpeg_get_samplerate( ffmpegObject* self ){
	return Py_BuildValue( "i", self->pCodecCtx->sample_rate );
}

static PyObject* ffmpeg_get_channels( ffmpegObject* self ){
	return Py_BuildValue( "i", self->pCodecCtx->channels );
}

static PyObject* ffmpeg_get_path( ffmpegObject* self ){
	return Py_BuildValue( "s", self->infile );
}



static PyObject* ffmpeg_read( ffmpegObject* self, PyObject* args ){
	AVPacket avpkt;
	AVFrame avfrm;
	int got_frame;
	
	if( av_read_frame(self->pFormatCtx, &avpkt) != 0 ){
		PyErr_SetString(FfmpegFileError, "read failed");
		return NULL;
	}
	
	avcodec_get_frame_defaults(&avfrm);
	
	got_frame = 0;
	if( avcodec_decode_audio4(self->pCodecCtx, &avfrm, &got_frame, &avpkt) < 0 ){
		PyErr_SetString(FfmpegDecodeError, "decoding failed");
		return NULL;
	}
	av_free_packet(&avpkt);
	
	if (got_frame == 0) {
		PyErr_SetString(PyExc_StopIteration, "no frame today, the music's gone away, my packet stands forlorn, a symbol of the dawn");
		return NULL;
	}
	
	char* resultbuf = malloc(avfrm.linesize[0] + 1);
	memcpy(resultbuf, avfrm.extended_data[0], avfrm.linesize[0]);
	resultbuf[avfrm.linesize[0]] = 0;
	
	return Py_BuildValue( "s#", resultbuf, avfrm.linesize[0] );
}


static PyMethodDef ffmpegObject_Methods[] = {
	{ "read",           (PyCFunction)ffmpeg_read,           METH_NOARGS, "read()\nRead the next frame and return its data." },
	{ "dump_format",    (PyCFunction)ffmpeg_dump_format,    METH_NOARGS, "dump_format()\nDump a bit of info about the file to stdout." },
	{ "get_path",       (PyCFunction)ffmpeg_get_path,       METH_NOARGS, "get_path()\nReturn the path to the input file." },
	{ "get_bitrate",    (PyCFunction)ffmpeg_get_bitrate,    METH_NOARGS, "get_bitrate()\nReturn the bit rate of the decoded file." },
	{ "get_samplerate", (PyCFunction)ffmpeg_get_samplerate, METH_NOARGS, "get_samplerate()\nReturn the sample rate of the decoded file." },
	{ "get_channels",   (PyCFunction)ffmpeg_get_channels,   METH_NOARGS, "get_channels()\nReturn the number of channels in the decoded file." },
	{ NULL, NULL, 0, NULL }
};

static PyMemberDef ffmpegObject_Members[] = {
	{ NULL }
};

static PyTypeObject ffmpegType = {
	PyObject_HEAD_INIT(NULL)
	0,                         /*ob_size*/
	"ffmpeg.Decoder",          /*tp_name*/
	sizeof( ffmpegObject ),    /*tp_basicsize*/
	0,                         /*tp_itemsize*/
	(destructor)ffmpeg_dealloc,/*tp_dealloc*/
	0,                         /*tp_print*/
	0,                         /*tp_getattr*/
	0,                         /*tp_setattr*/
	0,                         /*tp_compare*/
	0,                         /*tp_repr*/
	0,                         /*tp_as_number*/
	0,                         /*tp_as_sequence*/
	0,                         /*tp_as_mapping*/
	0,                         /*tp_hash */
	0,                         /*tp_call*/
	0,                         /*tp_str*/
	0,                         /*tp_getattro*/
	0,                         /*tp_setattro*/
	0,                         /*tp_as_buffer*/
	Py_TPFLAGS_DEFAULT,        /*tp_flags*/
	DECODER_DOCSTRING,         /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	ffmpegObject_Methods,      /* tp_methods */
	ffmpegObject_Members,      /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	0,                         /* tp_init */
	0,                         /* tp_alloc */
	(newfunc)ffmpeg_new,       /* tp_new */
};




static PyMethodDef ffmpegmodule_Methods[] = {
	{ NULL, NULL, 0, NULL }
};


/**
 *  Module initialization.
 */
#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC initffmpeg(void){
	PyObject* module;
	
	if( PyType_Ready( &ffmpegType ) < 0 ){
		return;
	}
	
	module = Py_InitModule3( "ffmpeg", ffmpegmodule_Methods, MODULE_DOCSTRING );
	
	Py_INCREF( &ffmpegType );
	PyModule_AddObject( module, "Decoder", (PyObject *)&ffmpegType );
	
	FfmpegDecodeError = PyErr_NewException("ffmpeg.DecodeError", NULL, NULL);
	Py_INCREF(FfmpegDecodeError);
	PyModule_AddObject( module, "DecodeError", FfmpegDecodeError );
	
	FfmpegFileError = PyErr_NewException("ffmpeg.FileError", NULL, NULL);
	Py_INCREF(FfmpegFileError);
	PyModule_AddObject( module, "FileError", FfmpegFileError );
	
	avcodec_register_all();
	av_register_all();
	avformat_network_init();
}


