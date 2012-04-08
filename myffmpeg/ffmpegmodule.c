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

#define MODULE_DOCSTRING "Python Module that decodes audio using FFmpeg's lavc."
#define DECODER_DOCSTRING ""\
	"This class handles decoding audio frames.\n"\
	"\n"\
	"Usage:\n"\
	">>> import ao\n" \
	">>> pcm = ao.AudioDevice()\n" \
	">>> decoder = ffmpeg.Decoder('/path/to/some/file.ogg')\n"\
	">>> for chunk in decoder.read():\n"\
	"...     pcm.play( chunk )\n"\
	""
#define RESAMPLER_DOCSTRING ""\
	"This class handles resampling audio frames.\n"\
	"\n"\
	"Usage:\n"\
	"wermer sehn"


static PyObject *FfmpegDecodeError;
static PyObject *FfmpegResampleError;
static PyObject *FfmpegFileError;


/**
 * DECODER
 */

typedef struct {
	PyObject_HEAD
	const char *infile;
	AVFormatContext *pFormatCtx;
	AVCodecContext *pCodecCtx;
	AVStream *pStream;
} ffmpegDecoderObject;

static PyObject* ffmpeg_decoder_new( PyTypeObject* type, PyObject* args ){
	ffmpegDecoderObject* self;
	AVCodec *codec;
	int streamIdx;
	
	self = (ffmpegDecoderObject *) type->tp_alloc( type, 0 );
	
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
	
	streamIdx = av_find_best_stream(self->pFormatCtx, AVMEDIA_TYPE_AUDIO, -1, -1, &codec, 0);
	if( streamIdx < 0 ){
		PyErr_SetString(FfmpegDecodeError, "could not find an audio stream");
		return NULL;
	}
	self->pStream = self->pFormatCtx->streams[streamIdx];
	self->pCodecCtx = self->pFormatCtx->streams[streamIdx]->codec;
	
	if( avcodec_open2(self->pCodecCtx, codec, NULL) < 0 ){
		PyErr_SetString(FfmpegDecodeError, "could not open codec");
		return NULL;
	}
	
	return (PyObject *)self;
}

static void ffmpeg_decoder_dealloc( ffmpegDecoderObject* self ){
	avcodec_close(self->pCodecCtx);
	avformat_close_input(&self->pFormatCtx);
}

static PyObject* ffmpeg_decoder_dump_format( ffmpegDecoderObject* self ){
	av_dump_format(self->pFormatCtx, 0, self->infile, 0);
	Py_RETURN_NONE;
}

static PyObject* ffmpeg_decoder_get_bitrate( ffmpegDecoderObject* self ){
	return Py_BuildValue( "i", self->pCodecCtx->bit_rate );
}

static PyObject* ffmpeg_decoder_get_samplerate( ffmpegDecoderObject* self ){
	return Py_BuildValue( "i", self->pCodecCtx->sample_rate );
}

static PyObject* ffmpeg_decoder_get_channels( ffmpegDecoderObject* self ){
	return Py_BuildValue( "i", self->pCodecCtx->channels );
}

static PyObject* ffmpeg_decoder_get_codec( ffmpegDecoderObject* self ){
	return Py_BuildValue( "s", self->pCodecCtx->codec->name );
}

static PyObject* ffmpeg_decoder_get_duration( ffmpegDecoderObject* self ){
	return Py_BuildValue( "d", self->pFormatCtx->duration / (double)AV_TIME_BASE );
}

static PyObject* ffmpeg_decoder_get_path( ffmpegDecoderObject* self ){
	return Py_BuildValue( "s", self->infile );
}

static PyObject* ffmpeg_decoder_get_metadata( ffmpegDecoderObject* self ){
	PyObject* metadict = PyDict_New();
	AVDictionaryEntry *metaent = NULL;
	while( (metaent = av_dict_get(self->pFormatCtx->metadata, "", metaent, AV_DICT_IGNORE_SUFFIX)) != NULL ){
		PyObject* str = PyString_FromString(metaent->value);
		PyDict_SetItemString(metadict, metaent->key, str);
		Py_DECREF(str);
	}
	metaent = NULL;
	while( (metaent = av_dict_get(self->pStream->metadata, "", metaent, AV_DICT_IGNORE_SUFFIX)) != NULL ){
		PyObject* str = PyString_FromString(metaent->value);
		PyDict_SetItemString(metadict, metaent->key, str);
		Py_DECREF(str);
	}
	return metadict;
}


static PyObject* ffmpeg_decoder_read( ffmpegDecoderObject* self, PyObject* args ){
	AVPacket avpkt;
	AVFrame *avfrm;
	int got_frame;
	int data_size;
	PyObject* ret;
	
	if( av_read_frame(self->pFormatCtx, &avpkt) < 0 ){
		PyErr_SetString(PyExc_StopIteration, "no more frames to read");
		return NULL;
	}
	
	
	got_frame = 0;
	avfrm = avcodec_alloc_frame();
	avcodec_get_frame_defaults(avfrm);
	if( avcodec_decode_audio4(self->pCodecCtx, avfrm, &got_frame, &avpkt) < 0 ){
		PyErr_SetString(FfmpegDecodeError, "decoding failed");
		av_free_packet(&avpkt);
		av_free(avfrm);
		return NULL;
	}
	av_free_packet(&avpkt);
	
	if (got_frame == 0) {
		av_free(avfrm);
		return Py_BuildValue( "s", "" );
	}
	
	data_size = av_samples_get_buffer_size(
		NULL, self->pCodecCtx->channels, avfrm->nb_samples, self->pCodecCtx->sample_fmt, 1
	);
	
	ret = Py_BuildValue( "s#", avfrm->data[0], data_size );
	av_free(avfrm);
	return ret;
}


static PyMethodDef ffmpegDecoderObject_Methods[] = {
	{ "read",           (PyCFunction)ffmpeg_decoder_read,           METH_NOARGS, "read()\nRead the next frame and return its data." },
	{ "dump_format",    (PyCFunction)ffmpeg_decoder_dump_format,    METH_NOARGS, "dump_format()\nDump a bit of info about the file to stdout." },
	{ "get_path",       (PyCFunction)ffmpeg_decoder_get_path,       METH_NOARGS, "get_path()\nReturn the path to the input file." },
	{ "get_bitrate",    (PyCFunction)ffmpeg_decoder_get_bitrate,    METH_NOARGS, "get_bitrate()\nReturn the bit rate of the decoded file." },
	{ "get_samplerate", (PyCFunction)ffmpeg_decoder_get_samplerate, METH_NOARGS, "get_samplerate()\nReturn the sample rate of the decoded file." },
	{ "get_channels",   (PyCFunction)ffmpeg_decoder_get_channels,   METH_NOARGS, "get_channels()\nReturn the number of channels in the decoded file." },
	{ "get_duration",   (PyCFunction)ffmpeg_decoder_get_duration,   METH_NOARGS, "get_duration()\nReturn the duration of the decoded file in seconds." },
	{ "get_metadata",   (PyCFunction)ffmpeg_decoder_get_metadata,   METH_NOARGS, "get_metadata()\nReturn a dict containing the file's meta data." },
	{ "get_codec",      (PyCFunction)ffmpeg_decoder_get_codec,      METH_NOARGS, "get_codec()\nReturn the name of the codec being used." },
	{ NULL, NULL, 0, NULL }
};

static PyMemberDef ffmpegDecoderObject_Members[] = {
	{ NULL }
};

static PyTypeObject ffmpegDecoder = {
	PyObject_HEAD_INIT(NULL)
	0,                         /*ob_size*/
	"ffmpeg.Decoder",          /*tp_name*/
	sizeof( ffmpegDecoderObject ),    /*tp_basicsize*/
	0,                         /*tp_itemsize*/
	(destructor)ffmpeg_decoder_dealloc,/*tp_dealloc*/
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
	ffmpegDecoderObject_Methods,      /* tp_methods */
	ffmpegDecoderObject_Members,      /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	0,                         /* tp_init */
	0,                         /* tp_alloc */
	(newfunc)ffmpeg_decoder_new,       /* tp_new */
};


/**
 * RESAMPLER
 */

typedef struct {
	PyObject_HEAD
	ReSampleContext *pResampleCtx;
} ffmpegResamplerObject;

static PyObject* ffmpeg_resampler_new( PyTypeObject* type, PyObject* args, PyObject* kw ){
	ffmpegResamplerObject* self;
	
	int output_rate = 0;
	int input_rate  = 0;
	int output_channels = 2;
	int input_channels  = 2;
	enum AVSampleFormat output_sample_format = AV_SAMPLE_FMT_S16;
	enum AVSampleFormat input_sample_format  = AV_SAMPLE_FMT_S16;
	/* The following defaults are blindly copied from
	 * http://stackoverflow.com/questions/5501357/the-problem-with-ffmpeg-on-android
	 */
	int filter_length = 16;
	int log2_phase_count = 10;
	int linear = 0;
	double cutoff = 1;
	
	static char *kwlist[] = {
		"output_rate", "input_rate", "output_channels", "input_channels",
		"output_sample_format", "input_sample_format",
		"filter_length", "log2_phase_count", "linear", "cutoff",
		NULL};
	
	self = (ffmpegResamplerObject *) type->tp_alloc( type, 0 );
	
	if( self == NULL )
		return NULL;
	
	if( !PyArg_ParseTupleAndKeywords( args, kw, "ii|iiiiiiid", kwlist,
		output_rate, input_rate, output_channels, input_channels,
		output_sample_format, input_sample_format,
		filter_length, log2_phase_count, linear, cutoff
		) ){
		return NULL;
	}
	
	self->pResampleCtx = av_audio_resample_init(
		output_channels, input_channels,
		output_rate, input_rate,
		output_sample_format, input_sample_format,
		filter_length, log2_phase_count, linear, cutoff);
	
	if( self->pResampleCtx == NULL ){
		PyErr_SetString(FfmpegResampleError, "could not initialize resampler");
		return NULL;
	}
	
	return (PyObject *)self;
}

static void ffmpeg_resampler_dealloc( ffmpegResamplerObject* self ){
	audio_resample_close(self->pResampleCtx);
}

static PyObject* ffmpeg_resampler_resample( ffmpegResamplerObject* self, PyObject* args ){
	/* int audio_resample(ReSampleContext *s, short *output, short *input, int nb_samples); */
	return Py_BuildValue("i", 1);
}

static PyMethodDef ffmpegResamplerObject_Methods[] = {
	{ "resample", (PyCFunction)ffmpeg_resampler_resample, METH_VARARGS, "resample(input)\nResample the input stream data." },
	{ NULL, NULL, 0, NULL }
};

static PyMemberDef ffmpegResamplerObject_Members[] = {
	{ NULL }
};

static PyTypeObject ffmpegResampler = {
	PyObject_HEAD_INIT(NULL)
	0,                         /*ob_size*/
	"ffmpeg.Resampler",          /*tp_name*/
	sizeof( ffmpegResamplerObject ),    /*tp_basicsize*/
	0,                         /*tp_itemsize*/
	(destructor)ffmpeg_resampler_dealloc,/*tp_dealloc*/
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
	RESAMPLER_DOCSTRING,         /* tp_doc */
	0,                         /* tp_traverse */
	0,                         /* tp_clear */
	0,                         /* tp_richcompare */
	0,                         /* tp_weaklistoffset */
	0,                         /* tp_iter */
	0,                         /* tp_iternext */
	ffmpegResamplerObject_Methods,      /* tp_methods */
	ffmpegResamplerObject_Members,      /* tp_members */
	0,                         /* tp_getset */
	0,                         /* tp_base */
	0,                         /* tp_dict */
	0,                         /* tp_descr_get */
	0,                         /* tp_descr_set */
	0,                         /* tp_dictoffset */
	0,                         /* tp_init */
	0,                         /* tp_alloc */
	(newfunc)ffmpeg_resampler_new,       /* tp_new */
};


/**
 *  Module initialization.
 */

static PyMethodDef ffmpegmodule_Methods[] = {
	{ NULL, NULL, 0, NULL }
};

#ifndef PyMODINIT_FUNC	/* declarations for DLL import/export */
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC init_ffmpeg(void){
	PyObject* module;
	
	if( PyType_Ready( &ffmpegDecoder ) < 0 ){
		return;
	}
	
	if( PyType_Ready( &ffmpegResampler ) < 0 ){
		return;
	}
	
	module = Py_InitModule3( "_ffmpeg", ffmpegmodule_Methods, MODULE_DOCSTRING );
	
	Py_INCREF( &ffmpegDecoder );
	PyModule_AddObject( module, "Decoder", (PyObject *)&ffmpegDecoder );
	
	Py_INCREF( &ffmpegResampler );
	PyModule_AddObject( module, "Resampler", (PyObject *)&ffmpegResampler );
	
	FfmpegDecodeError = PyErr_NewException("ffmpeg.DecodeError", NULL, NULL);
	Py_INCREF(FfmpegDecodeError);
	PyModule_AddObject( module, "DecodeError", FfmpegDecodeError );
	
	FfmpegResampleError = PyErr_NewException("ffmpeg.ResampleError", NULL, NULL);
	Py_INCREF(FfmpegResampleError);
	PyModule_AddObject( module, "ResampleError", FfmpegResampleError );
	
	FfmpegFileError = PyErr_NewException("ffmpeg.FileError", NULL, NULL);
	Py_INCREF(FfmpegFileError);
	PyModule_AddObject( module, "FileError", FfmpegFileError );
	
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_NONE );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_U8   );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_S16  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_S32  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_FLT  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_DBL  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_NB   );
	
	avcodec_register_all();
	av_register_all();
	avformat_network_init();
}


