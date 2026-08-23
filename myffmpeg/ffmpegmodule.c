/**
 *  Python Module to decode audio files using FFmpeg's lavc.
 *
 *  Copyright © 2012, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
 *
 *  Updated for Python 3 and modern FFmpeg (4.x+).
 *
 *  To compile this file into a Python module, run `python setup.py build`.
 *  The compiled binary will be put into build/lib.<platform>/_ffmpeg.so.
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
#include <libswresample/swresample.h>
#include <libavutil/avutil.h>
#include <libavutil/opt.h>
#include <libavutil/mathematics.h>
#include <libavutil/samplefmt.h>
#include <libavutil/channel_layout.h>


#define MODULE_DOCSTRING "Python Module that decodes audio using FFmpeg's lavc."
#define DECODER_DOCSTRING ""\
	"This class handles decoding audio frames.\n"\
	"\n"\
	"   Decoder(fpath)\n"\
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
	"   Resampler(output_rate, input_rate, \n"\
	"             output_channel_layout=AV_CH_LAYOUT_STEREO, \n"\
	"             input_channel_layout=AV_CH_LAYOUT_STEREO, \n"\
	"             output_sample_format=AV_SAMPLE_FMT_S16, \n"\
	"             input_sample_format=AV_SAMPLE_FMT_S16 \n"\
	"   )\n"\
	""


static PyObject *FfmpegDecodeError;
static PyObject *FfmpegResampleError;
static PyObject *FfmpegFileError;


/**
 * DECODER
 */

typedef struct {
	PyObject_HEAD
	char *infile;
	AVFormatContext *pFormatCtx;
	AVCodecContext  *pCodecCtx;
	AVStream        *pStream;
	AVPacket        *pkt;
	AVFrame         *frame;
} ffmpegDecoderObject;

static PyObject* ffmpeg_decoder_new( PyTypeObject* type, PyObject* args ){
	ffmpegDecoderObject* self;
	const AVCodec *codec;
	int streamIdx;
	int err = 0;

	self = (ffmpegDecoderObject *) type->tp_alloc( type, 0 );

	if( self == NULL )
		return NULL;

	self->pFormatCtx = NULL;
	self->pCodecCtx  = NULL;
	self->pkt        = NULL;
	self->frame      = NULL;

	const char *infile_arg;
	if( !PyArg_ParseTuple( args, "s", &infile_arg ) ){
		err = 1;
	}

	if( !err ){
		self->infile = av_strdup(infile_arg);
		if( self->infile == NULL ){
			PyErr_NoMemory();
			err = 1;
		}
	}

	if( !err && avformat_open_input(&self->pFormatCtx, self->infile, NULL, NULL) < 0){
		PyErr_SetString(FfmpegFileError, "could not open infile");
		err = 2;
	}

	if( !err && avformat_find_stream_info(self->pFormatCtx, NULL) < 0) {
		PyErr_SetString(FfmpegDecodeError, "could not find stream information");
		err = 3;
	}

	if( !err ){
		streamIdx = av_find_best_stream(self->pFormatCtx, AVMEDIA_TYPE_AUDIO, -1, -1, &codec, 0);
		if( streamIdx < 0 ){
			PyErr_SetString(FfmpegDecodeError, "could not find an audio stream");
			err = 4;
		}
	}

	if( !err ){
		self->pStream = self->pFormatCtx->streams[streamIdx];

		self->pCodecCtx = avcodec_alloc_context3(codec);
		if( self->pCodecCtx == NULL ){
			PyErr_SetString(FfmpegDecodeError, "could not allocate codec context");
			err = 5;
		}
	}

	if( !err && avcodec_parameters_to_context(self->pCodecCtx, self->pStream->codecpar) < 0 ){
		PyErr_SetString(FfmpegDecodeError, "could not copy codec parameters");
		err = 6;
	}

	if( !err && avcodec_open2(self->pCodecCtx, codec, NULL) < 0 ){
		PyErr_SetString(FfmpegDecodeError, "could not open codec");
		err = 7;
	}

	if( !err ){
		self->pkt = av_packet_alloc();
		self->frame = av_frame_alloc();
		if( self->pkt == NULL || self->frame == NULL ){
			PyErr_NoMemory();
			err = 8;
		}
	}

	if( err > 4 && self->pCodecCtx != NULL ){
		avcodec_free_context(&self->pCodecCtx);
	}

	if( err > 2 ){
		avformat_close_input(&self->pFormatCtx);
	}

	if( err > 0 ){
		if( self->pkt )   av_packet_free(&self->pkt);
		if( self->frame ) av_frame_free(&self->frame);
		av_free(self->infile);
		type->tp_free( self );
		self = NULL;
	}

	return (PyObject *)self;
}

static void ffmpeg_decoder_dealloc( ffmpegDecoderObject* self ){
	if( self->pCodecCtx ) avcodec_free_context(&self->pCodecCtx);
	if( self->pFormatCtx ) avformat_close_input(&self->pFormatCtx);
	if( self->pkt )   av_packet_free(&self->pkt);
	if( self->frame ) av_frame_free(&self->frame);
	av_free(self->infile);
	Py_TYPE(self)->tp_free((PyObject*)self);
}

static PyObject* ffmpeg_decoder_dump_format( ffmpegDecoderObject* self ){
	av_dump_format(self->pFormatCtx, 0, self->infile, 0);
	Py_RETURN_NONE;
}

static PyObject* ffmpeg_decoder_get_bitrate( ffmpegDecoderObject* self ){
	return PyLong_FromLong( self->pCodecCtx->bit_rate );
}

static PyObject* ffmpeg_decoder_get_samplerate( ffmpegDecoderObject* self ){
	return PyLong_FromLong( self->pCodecCtx->sample_rate );
}

static PyObject* ffmpeg_decoder_get_samplefmt( ffmpegDecoderObject* self ){
	return PyLong_FromLong( self->pCodecCtx->sample_fmt );
}

static PyObject* ffmpeg_decoder_get_channels( ffmpegDecoderObject* self ){
	return PyLong_FromLong( self->pCodecCtx->ch_layout.nb_channels );
}

static PyObject* ffmpeg_decoder_get_channel_layout( ffmpegDecoderObject* self ){
	return PyLong_FromLong( (long)self->pCodecCtx->ch_layout.u.mask );
}

static PyObject* ffmpeg_decoder_get_codec( ffmpegDecoderObject* self ){
	return PyUnicode_FromString( self->pCodecCtx->codec->name );
}

static PyObject* ffmpeg_decoder_get_duration( ffmpegDecoderObject* self ){
	return PyFloat_FromDouble( self->pFormatCtx->duration / (double)AV_TIME_BASE );
}

static PyObject* ffmpeg_decoder_get_path( ffmpegDecoderObject* self ){
	return PyUnicode_FromString( self->infile );
}

static PyObject* ffmpeg_decoder_get_metadata( ffmpegDecoderObject* self ){
	PyObject* metadict = PyDict_New();
	AVDictionaryEntry *metaent = NULL;
	while( (metaent = av_dict_get(self->pFormatCtx->metadata, "", metaent, AV_DICT_IGNORE_SUFFIX)) != NULL ){
		PyObject* str = PyUnicode_FromString(metaent->value);
		PyDict_SetItemString(metadict, metaent->key, str);
		Py_DECREF(str);
	}
	metaent = NULL;
	while( (metaent = av_dict_get(self->pStream->metadata, "", metaent, AV_DICT_IGNORE_SUFFIX)) != NULL ){
		PyObject* str = PyUnicode_FromString(metaent->value);
		PyDict_SetItemString(metadict, metaent->key, str);
		Py_DECREF(str);
	}
	return metadict;
}


static PyObject* ffmpeg_decoder_read( ffmpegDecoderObject* self ){
	int nb_channels;
	int data_size;
	int i;
	int ret;
	PyObject* result = NULL;

	/* Read packets until we receive a decoded frame. */
	while( 1 ){
		ret = av_read_frame(self->pFormatCtx, self->pkt);
		if( ret < 0 ){
			/* EOF or error: flush the decoder */
			avcodec_send_packet(self->pCodecCtx, NULL);
			ret = avcodec_receive_frame(self->pCodecCtx, self->frame);
			if( ret < 0 ){
				PyErr_SetString(PyExc_StopIteration, "no more frames to read");
				return NULL;
			}
			break;
		}

		if( avcodec_send_packet(self->pCodecCtx, self->pkt) < 0 ){
			av_packet_unref(self->pkt);
			continue;
		}
		av_packet_unref(self->pkt);

		ret = avcodec_receive_frame(self->pCodecCtx, self->frame);
		if( ret == AVERROR(EAGAIN) ){
			continue;  /* need more packets */
		}
		if( ret < 0 ){
			PyErr_SetString(FfmpegDecodeError, "decoding failed");
			return NULL;
		}
		break;
	}

	nb_channels = self->frame->ch_layout.nb_channels;
	data_size = av_samples_get_buffer_size(
		NULL, nb_channels, self->frame->nb_samples,
		(enum AVSampleFormat)self->frame->format, 1
	);

	if( av_sample_fmt_is_planar((enum AVSampleFormat)self->frame->format) ){
		/* planar data: return each channel separately */
		result = PyTuple_New(nb_channels);
		for( i = 0; i < nb_channels; i++ ){
			PyTuple_SetItem(result, i, PyBytes_FromStringAndSize(
				(const char*)self->frame->extended_data[i],
				data_size / nb_channels
			));
		}
	}
	else{
		result = PyTuple_New(1);
		PyTuple_SetItem(result, 0, PyBytes_FromStringAndSize(
			(const char*)self->frame->data[0], data_size
		));
	}

	av_frame_unref(self->frame);

	return result;
}


static PyMethodDef ffmpegDecoderObject_Methods[] = {
	{ "read",           (PyCFunction)ffmpeg_decoder_read,           METH_NOARGS, "read()\nRead the next frame and return its data." },
	{ "dump_format",    (PyCFunction)ffmpeg_decoder_dump_format,    METH_NOARGS, "dump_format()\nDump a bit of info about the file to stdout." },
	{ "get_path",       (PyCFunction)ffmpeg_decoder_get_path,       METH_NOARGS, "get_path()\nReturn the path to the input file." },
	{ "get_bitrate",    (PyCFunction)ffmpeg_decoder_get_bitrate,    METH_NOARGS, "get_bitrate()\nReturn the bit rate of the decoded file." },
	{ "get_samplerate", (PyCFunction)ffmpeg_decoder_get_samplerate, METH_NOARGS, "get_samplerate()\nReturn the sample rate of the decoded file." },
	{ "get_samplefmt",  (PyCFunction)ffmpeg_decoder_get_samplefmt,  METH_NOARGS, "get_samplefmt()\nReturn the sample format of the decoded file." },
	{ "get_channels",   (PyCFunction)ffmpeg_decoder_get_channels,   METH_NOARGS, "get_channels()\nReturn the number of channels in the decoded file." },
	{ "get_channel_layout", (PyCFunction)ffmpeg_decoder_get_channel_layout, METH_NOARGS, "get_channel_layout()\nReturn the channel layout." },
	{ "get_duration",   (PyCFunction)ffmpeg_decoder_get_duration,   METH_NOARGS, "get_duration()\nReturn the duration of the decoded file in seconds." },
	{ "get_metadata",   (PyCFunction)ffmpeg_decoder_get_metadata,   METH_NOARGS, "get_metadata()\nReturn a dict containing the file's meta data." },
	{ "get_codec",      (PyCFunction)ffmpeg_decoder_get_codec,      METH_NOARGS, "get_codec()\nReturn the name of the codec being used." },
	{ NULL, NULL, 0, NULL }
};

static PyMemberDef ffmpegDecoderObject_Members[] = {
	{ NULL }
};

static PyTypeObject ffmpegDecoder = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_name      = "ffmpeg.Decoder",
	.tp_basicsize = sizeof( ffmpegDecoderObject ),
	.tp_dealloc   = (destructor)ffmpeg_decoder_dealloc,
	.tp_flags     = Py_TPFLAGS_DEFAULT,
	.tp_doc       = DECODER_DOCSTRING,
	.tp_methods   = ffmpegDecoderObject_Methods,
	.tp_members   = ffmpegDecoderObject_Members,
	.tp_new       = (newfunc)ffmpeg_decoder_new,
};


/**
 * RESAMPLER
 */

typedef struct {
	PyObject_HEAD
	SwrContext *pResampleCtx;
	int output_rate;
	int input_rate;
	int64_t output_channel_layout;
	int64_t input_channel_layout;
	enum AVSampleFormat output_sample_format;
	enum AVSampleFormat input_sample_format;
} ffmpegResamplerObject;

static PyObject* ffmpeg_resampler_new( PyTypeObject* type, PyObject* args, PyObject* kw ){
	ffmpegResamplerObject* self;

	static char *kwlist[] = {
		"output_rate", "input_rate", "output_channel_layout", "input_channel_layout",
		"output_sample_format", "input_sample_format",
		NULL};

	self = (ffmpegResamplerObject *) type->tp_alloc( type, 0 );

	if( self == NULL )
		return NULL;

	self->output_rate = 0;
	self->input_rate  = 0;
	self->output_channel_layout = AV_CH_LAYOUT_STEREO;
	self->input_channel_layout  = AV_CH_LAYOUT_STEREO;
	self->output_sample_format = AV_SAMPLE_FMT_S16;
	self->input_sample_format  = AV_SAMPLE_FMT_S16;

	if( !PyArg_ParseTupleAndKeywords( args, kw, "ii|LLii", kwlist,
		&self->output_rate,           &self->input_rate,
		&self->output_channel_layout, &self->input_channel_layout,
		&self->output_sample_format,  &self->input_sample_format
		) ){
		type->tp_free( self );
		return NULL;
	}

	AVChannelLayout in_ch_layout  = AV_CHANNEL_LAYOUT_MASK(
		av_popcount64(self->input_channel_layout),
		self->input_channel_layout
	);
	AVChannelLayout out_ch_layout = AV_CHANNEL_LAYOUT_MASK(
		av_popcount64(self->output_channel_layout),
		self->output_channel_layout
	);

	self->pResampleCtx = NULL;
	int ret = swr_alloc_set_opts2(
		&self->pResampleCtx,
		&out_ch_layout, self->output_sample_format, self->output_rate,
		&in_ch_layout,  self->input_sample_format,  self->input_rate,
		0, NULL
	);

	if( ret < 0 || self->pResampleCtx == NULL ){
		PyErr_SetString(FfmpegResampleError, "could not initialize resampler");
		type->tp_free( self );
		return NULL;
	}

	if( swr_init(self->pResampleCtx) < 0 ){
		swr_free(&self->pResampleCtx);
		PyErr_SetString(FfmpegResampleError, "could not open resampler");
		type->tp_free( self );
		return NULL;
	}

	return (PyObject *)self;
}

static void ffmpeg_resampler_dealloc( ffmpegResamplerObject* self ){
	swr_free(&self->pResampleCtx);
	Py_TYPE(self)->tp_free((PyObject*)self);
}


static PyObject* ffmpeg_resampler_resample( ffmpegResamplerObject* self, PyObject* args ){
	const uint8_t **indata = NULL;
	int i;
	int innb;
	int inlen;
	int inplanes;
	uint8_t **outbuf = NULL;
	int outnb;
	int outplanes = 0;
	PyObject* in  = NULL;
	PyObject* ret = NULL;

	if( !PyArg_ParseTuple( args, "O!", &PyTuple_Type, &in ) )
		return NULL;

	inplanes = (int)PyTuple_Size(in);

	indata = (const uint8_t**)malloc( sizeof(uint8_t*) * inplanes );
	if( indata == NULL ){
		PyErr_SetString(FfmpegResampleError, "out of memory");
		return NULL;
	}
	for( i = 0; i < inplanes; i++ ){
		PyObject *item = PyTuple_GetItem(in, i);
		indata[i] = (const uint8_t*)PyBytes_AsString(item);
	}

	inlen = (int)PyBytes_Size(PyTuple_GetItem(in, 0));
	innb  = inlen / av_get_bytes_per_sample(self->input_sample_format);

	outnb = (int)av_rescale_rnd(
		innb + swr_get_delay(self->pResampleCtx, self->input_rate),
		self->output_rate, self->input_rate, AV_ROUND_UP
	);

	int out_channels = av_popcount64(self->output_channel_layout);

	if( av_samples_alloc_array_and_samples(&outbuf, NULL,
			out_channels, outnb, self->output_sample_format, 0) < 0 ){
		free(indata);
		PyErr_SetString(FfmpegResampleError, "out of memory");
		return NULL;
	}

	int converted = swr_convert(self->pResampleCtx, outbuf, outnb, indata, innb);
	if( converted < 0 ){
		PyErr_SetString(FfmpegResampleError, "resampling failed");
	}
	else{
		int outlen = av_samples_get_buffer_size(NULL, out_channels, converted,
		                                        self->output_sample_format, 1);
		outplanes = 1;
		if( av_sample_fmt_is_planar(self->output_sample_format) )
			outplanes = out_channels;
		ret = PyTuple_New(outplanes);
		for( i = 0; i < outplanes; i++ )
			PyTuple_SetItem(ret, i, PyBytes_FromStringAndSize(
				(const char*)outbuf[i], outlen / outplanes
			));
	}

	free(indata);
	av_freep(&outbuf[0]);
	av_freep(&outbuf);

	return ret;
}

static PyMethodDef ffmpegResamplerObject_Methods[] = {
	{ "resample", (PyCFunction)ffmpeg_resampler_resample, METH_VARARGS, "resample(input)\nResample the input stream data." },
	{ NULL, NULL, 0, NULL }
};

static PyMemberDef ffmpegResamplerObject_Members[] = {
	{ NULL }
};

static PyTypeObject ffmpegResampler = {
	PyVarObject_HEAD_INIT(NULL, 0)
	.tp_name      = "ffmpeg.Resampler",
	.tp_basicsize = sizeof( ffmpegResamplerObject ),
	.tp_dealloc   = (destructor)ffmpeg_resampler_dealloc,
	.tp_flags     = Py_TPFLAGS_DEFAULT,
	.tp_doc       = RESAMPLER_DOCSTRING,
	.tp_methods   = ffmpegResamplerObject_Methods,
	.tp_members   = ffmpegResamplerObject_Members,
	.tp_new       = (newfunc)ffmpeg_resampler_new,
};


/**
 *  Module initialization.
 */

static PyObject* ffmpeg_get_sample_fmt_name( PyObject* module, PyObject* args ){
	enum AVSampleFormat sample_fmt;
	const char* fmt_name;

	if( !PyArg_ParseTuple( args, "i", &sample_fmt ) )
		return NULL;

	if( (fmt_name = av_get_sample_fmt_name(sample_fmt)) != NULL )
		return PyUnicode_FromString( fmt_name );

	PyErr_SetString(PyExc_KeyError, "Sample format not recognized");
	return NULL;
}

static PyObject* ffmpeg_get_bytes_per_sample( PyObject* module, PyObject* args ){
	enum AVSampleFormat sample_fmt;
	int bps;

	if( !PyArg_ParseTuple( args, "i", &sample_fmt ) )
		return NULL;

	if( (bps = av_get_bytes_per_sample(sample_fmt)) )
		return PyLong_FromLong( bps );

	PyErr_SetString(PyExc_KeyError, "Sample format not recognized");
	return NULL;
}

static PyMethodDef ffmpegmodule_Methods[] = {
	{ "get_sample_fmt_name",  (PyCFunction)ffmpeg_get_sample_fmt_name,  METH_VARARGS, "get_sample_fmt_name(format)\nReturn the given sample format's name."},
	{ "get_bytes_per_sample", (PyCFunction)ffmpeg_get_bytes_per_sample, METH_VARARGS, "get_bytes_per_sample(format)\nReturn the size of one sample in bytes."},
	{ NULL, NULL, 0, NULL }
};

static struct PyModuleDef ffmpegmodule = {
	PyModuleDef_HEAD_INIT,
	"_ffmpeg",
	MODULE_DOCSTRING,
	-1,
	ffmpegmodule_Methods
};

PyMODINIT_FUNC PyInit__ffmpeg(void){
	PyObject* module;

	if( PyType_Ready( &ffmpegDecoder ) < 0 )
		return NULL;

	if( PyType_Ready( &ffmpegResampler ) < 0 )
		return NULL;

	module = PyModule_Create( &ffmpegmodule );
	if( module == NULL )
		return NULL;

	Py_INCREF( &ffmpegDecoder );
	PyModule_AddObject( module, "Decoder", (PyObject *)&ffmpegDecoder );

	Py_INCREF( &ffmpegResampler );
	PyModule_AddObject( module, "Resampler", (PyObject *)&ffmpegResampler );

	FfmpegDecodeError = PyErr_NewException("_ffmpeg.DecodeError", NULL, NULL);
	Py_INCREF(FfmpegDecodeError);
	PyModule_AddObject( module, "DecodeError", FfmpegDecodeError );

	FfmpegResampleError = PyErr_NewException("_ffmpeg.ResampleError", NULL, NULL);
	Py_INCREF(FfmpegResampleError);
	PyModule_AddObject( module, "ResampleError", FfmpegResampleError );

	FfmpegFileError = PyErr_NewException("_ffmpeg.FileError", NULL, NULL);
	Py_INCREF(FfmpegFileError);
	PyModule_AddObject( module, "FileError", FfmpegFileError );

	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_NONE );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_U8   );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_S16  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_S32  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_FLT  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_DBL  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_U8P  );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_S16P );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_S32P );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_FLTP );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_DBLP );
	PyModule_AddIntMacro( module, AV_SAMPLE_FMT_NB   );

	PyModule_AddIntMacro( module, AV_CH_LAYOUT_STEREO         );
	PyModule_AddIntMacro( module, AV_CH_LAYOUT_2POINT1        );
	PyModule_AddIntMacro( module, AV_CH_LAYOUT_2_1            );
	PyModule_AddIntMacro( module, AV_CH_LAYOUT_SURROUND       );
	PyModule_AddIntMacro( module, AV_CH_LAYOUT_2_2            );
	PyModule_AddIntMacro( module, AV_CH_LAYOUT_QUAD           );
	PyModule_AddIntMacro( module, AV_CH_LAYOUT_STEREO_DOWNMIX );

	avformat_network_init();

	return module;
}
