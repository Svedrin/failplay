/**
 *  Python Module to run Fuzzy Calculations using fis.c from MATLAB.
 *
 *  Copyright © 2009/10, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 *
 *  To compile this file into a Python module, run `python setup.py build`.
 *  The compiled binary will be put into build/lib.<platform>/fis.so.
 *
 *  This requires the fis.c file which is distributed in MATLAB. Since
 *  fis.c does not state copyright regulations, I don't distribute it with
 *  this file.
 *
 *  The FIS module is free software; you can redistribute it and/or modify
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

#define INBUF_SIZE 4096
#define AUDIO_INBUF_SIZE 20480
#define AUDIO_REFILL_THRESH 4096


typedef struct {
	PyObject_HEAD
	const char *infile;
	AVFormatContext *pFormatCtx;
	AVCodecContext *pCodecCtx;
} ffmpegObject;



static PyObject* ffmpeg_new( PyTypeObject* type, PyObject* args ){
	printf( "C!!!...\n");
	ffmpegObject* self;
	
	self = (ffmpegObject *) type->tp_alloc( type, 0 );
	
	if( self == NULL )
		return NULL;
	
	if( !PyArg_ParseTuple( args, "s", &self->infile ) )
		return NULL;
	
	printf( "Opening...\n");
	if(avformat_open_input(&self->pFormatCtx, self->infile, NULL, NULL) < 0){
		PyErr_SetString(PyExc_IndexError, "could not open infile");
		return NULL;
	}
	
	if (av_find_stream_info(self->pFormatCtx) < 0) {
		PyErr_SetString(PyExc_IndexError, "could not find stream information");
		return NULL;
	}
	
	av_dump_format(self->pFormatCtx, 0, self->infile, 0);
	
	AVCodec *codec;
	
	int streamIdx = av_find_best_stream(self->pFormatCtx, AVMEDIA_TYPE_AUDIO, -1, -1, &codec, 0);
	self->pCodecCtx = self->pFormatCtx->streams[streamIdx]->codec;
	
	printf( "bitrate: %d\n", self->pCodecCtx->bit_rate );
	printf( "smprate: %d\n", self->pCodecCtx->sample_rate );
	printf( "channels: %d\n", self->pCodecCtx->channels );
	
	if( avcodec_open(self->pCodecCtx, codec) < 0 ){
		PyErr_SetString(PyExc_IndexError, "could not open infile");
		return NULL;
	}
	
	return (PyObject *)self;
}

static void ffmpeg_dealloc( ffmpegObject* self ){
	avcodec_close(self->pCodecCtx);
	av_free(self->pCodecCtx);
// 	av_close_input_file(self->pFormatCtx);
}

static PyObject* ffmpeg_read( ffmpegObject* self, PyObject* args ){
	int len;
	AVPacket avpkt;
	AVFrame avfrm;
	int got_frame;
	
	if( av_read_frame(self->pFormatCtx, &avpkt) != 0 ){
		PyErr_SetString(PyExc_IndexError, "read failed");
		return NULL;
	}
		
	avcodec_get_frame_defaults(&avfrm);
	
	got_frame = 0;
	len = avcodec_decode_audio4(self->pCodecCtx, &avfrm, &got_frame, &avpkt);
	av_free_packet(&avpkt);
	
	if (got_frame == 0) {
		PyErr_SetString(PyExc_IndexError, "no frame today, the music's gone away, my packet stands forlorn, a symbol of the dawn");
		return NULL;
	}
	
	char* resultbuf = malloc(avfrm.linesize[0] + 1);
	memcpy(resultbuf, avfrm.data, avfrm.linesize[0]);
	resultbuf[avfrm.linesize[0]] = 0;
	
	return Py_BuildValue( "s#", resultbuf, avfrm.linesize[0] );
}


static PyObject* ffmpeg_hallo( ffmpegObject* self, PyObject* args ){
	char* infile;
	
	if( !PyArg_ParseTuple( args, "s", &infile ) )
		return NULL;
	
	if(avformat_open_input(&self->pFormatCtx, infile, NULL, NULL) < 0){
		PyErr_SetString(PyExc_IndexError, "could not open infile");
		return NULL;
	}
	
	if (av_find_stream_info(self->pFormatCtx) < 0) {
		PyErr_SetString(PyExc_IndexError, "could not find stream information");
		return NULL;
	}
	
	av_dump_format(self->pFormatCtx, 0, infile, 0);
	
	AVCodec *codec;
	
	int streamIdx = av_find_best_stream(self->pFormatCtx, AVMEDIA_TYPE_AUDIO, -1, -1, &codec, 0);
	self->pCodecCtx = self->pFormatCtx->streams[streamIdx]->codec;
	
	printf( "bitrate: %d\n", self->pCodecCtx->bit_rate );
	printf( "smprate: %d\n", self->pCodecCtx->sample_rate );
	printf( "channels: %d\n", self->pCodecCtx->channels );
	
	if( avcodec_open(self->pCodecCtx, codec) < 0 ){
		PyErr_SetString(PyExc_IndexError, "could not open infile");
		return NULL;
	}
	
	int len;
	AVPacket avpkt;
	AVFrame avfrm;
	int got_frame;
	
	
	char* resultbuf = malloc(40960000);
	int resultpos = 0;
	
	while( av_read_frame(self->pFormatCtx, &avpkt) == 0 && resultpos < 40960000 - AVCODEC_MAX_AUDIO_FRAME_SIZE ){
// 		printf("Readn... \n" );
		
		avcodec_get_frame_defaults(&avfrm);
		
		got_frame = 0;
		len = avcodec_decode_audio4(self->pCodecCtx, &avfrm, &got_frame, &avpkt);
		av_free_packet(&avpkt);
		
// 		if (len < 0) {
// 			printf( "Looks failish: %d %d\n", len, got_frame );
// 			break;
// 		}
// 		else{
// 			printf( "Looks good: %d %d %d %d\n", len, got_frame, avfrm.linesize[0], avfrm.nb_samples );
// 		}
		
		if (got_frame > 0) {
// 			printf( "save dat stuff: %d\n", resultpos);
			memcpy(resultbuf + resultpos, avfrm.data, avfrm.linesize[0]);
			resultpos += avfrm.linesize[0];
		}
	}
	
	
	avcodec_close(self->pCodecCtx);
	av_free(self->pCodecCtx);
// 	av_close_input_file(self->pFormatCtx);
	
	return Py_BuildValue( "(si)",
		resultbuf, resultpos
		);
}



static PyMethodDef ffmpegObject_Methods[] = {
	{"read",  ffmpeg_read, METH_NOARGS, "read some stuff."},
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
	"derpyherp",               /* tp_doc */
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
	{"hallo",  ffmpeg_hallo, METH_VARARGS, "herpyderp."},
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
	
	module = Py_InitModule3( "ffmpeg", ffmpegmodule_Methods, "voll der docstring" );
	
	Py_INCREF( &ffmpegType );
	PyModule_AddObject( module, "Decoder", (PyObject *)&ffmpegType );
	
	avcodec_register_all();
	av_register_all();
	avformat_network_init();
}


