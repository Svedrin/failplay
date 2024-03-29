/**
 *  Python Module to decode audio files using FFmpeg's lavc.
 *
 *  Copyright © 2012, Michael "Svedrin" Ziegler <diese-addy@funzt-halt.net>
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
#include <libavresample/avresample.h>
#include <libavutil/avutil.h>
#include <libavutil/opt.h>
#include <libavutil/mathematics.h>


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
	"             input_sample_format=AV_SAMPLE_FMT_S16, \n"\
	"             filter_length=16, log2_phase_count=10, \n"\
	"             linear=0, cutoff=1 \n"\
	"   )\n"\
	""


static PyObject *FfmpegDecodeError;
static PyObject *FfmpegResampleError;
static PyObject *FfmpegFileError;


// I'd really like this thing to support streams. I just don't know if it will ever
// happen. Anyway, here's a coupl'a links on how this seems to work with libav:
//
// ffurl_open/close  → https://ffmpeg.org/doxygen/1.0/avio_8c-source.html#l00234
// open_input_stream → https://ffmpeg.org/doxygen/1.0/ffserver_8c-source.html#l02138
// http_connect      → https://ffmpeg.org/doxygen/1.0/http_8c-source.html#l00377

/**
 * HACK UNTIL DEBIAN UPDATES LIBAV
 */

#define av_sample_format_is_planar(fmt) ((fmt) >= AV_SAMPLE_FMT_U8P && (fmt) <= AV_SAMPLE_FMT_DBLP)

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
	int err = 0;
	
	self = (ffmpegDecoderObject *) type->tp_alloc( type, 0 );
	
	if( self == NULL )
		return NULL;
	
	self->pFormatCtx = NULL;
	self->pCodecCtx  = NULL;
	
	if( !PyArg_ParseTuple( args, "s", &self->infile ) ){
		err = 1;
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
		self->pStream   = self->pFormatCtx->streams[streamIdx];
		self->pCodecCtx = self->pFormatCtx->streams[streamIdx]->codec;
		
		if( avcodec_open2(self->pCodecCtx, codec, NULL) < 0 ){
			PyErr_SetString(FfmpegDecodeError, "could not open codec");
			err = 5;
		}
	}
	
	if( err > 2 ){
		avformat_close_input(&self->pFormatCtx);
	}
	
	if( err > 0 ){
		type->tp_free( self );
		self = NULL;
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
	return PyInt_FromLong( self->pCodecCtx->bit_rate );
}

static PyObject* ffmpeg_decoder_get_samplerate( ffmpegDecoderObject* self ){
	return PyInt_FromLong( self->pCodecCtx->sample_rate );
}

static PyObject* ffmpeg_decoder_get_samplefmt( ffmpegDecoderObject* self ){
	return PyInt_FromLong( self->pCodecCtx->sample_fmt );
}

static PyObject* ffmpeg_decoder_get_channels( ffmpegDecoderObject* self ){
	return PyInt_FromLong( self->pCodecCtx->channels );
}

static PyObject* ffmpeg_decoder_get_channel_layout( ffmpegDecoderObject* self ){
	return PyInt_FromLong( self->pCodecCtx->channel_layout );
}

static PyObject* ffmpeg_decoder_get_codec( ffmpegDecoderObject* self ){
	return PyString_FromString( self->pCodecCtx->codec->name );
}

static PyObject* ffmpeg_decoder_get_duration( ffmpegDecoderObject* self ){
	return PyFloat_FromDouble( self->pFormatCtx->duration / (double)AV_TIME_BASE );
}

static PyObject* ffmpeg_decoder_get_path( ffmpegDecoderObject* self ){
	return PyString_FromString( self->infile );
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


static PyObject* ffmpeg_decoder_read( ffmpegDecoderObject* self ){
	AVPacket avpkt;
	AVFrame *avfrm;
	int got_frame;
	int data_size;
	int i;
	PyObject* ret = NULL;
	
	if( av_read_frame(self->pFormatCtx, &avpkt) < 0 ){
		PyErr_SetString(PyExc_StopIteration, "no more frames to read");
		return NULL;
	}
	
	if( (avfrm = av_frame_alloc()) == NULL ){
		PyErr_SetString(FfmpegDecodeError, "out of memory");
		av_packet_unref(&avpkt);
		return NULL;
	}
	
	got_frame = 0;
	if( avcodec_decode_audio4(self->pCodecCtx, avfrm, &got_frame, &avpkt) < 0 || !got_frame ){
		PyErr_SetString(FfmpegDecodeError, "decoding failed");
	}
	else{
		data_size = av_samples_get_buffer_size(
			NULL, self->pCodecCtx->channels, avfrm->nb_samples, self->pCodecCtx->sample_fmt, 1
		);
		if( av_sample_format_is_planar(self->pCodecCtx->sample_fmt) ){
			// planar data. read all the streams and return their data as a tuple.
			ret = PyTuple_New(self->pCodecCtx->channels);
			for( i = 0; i < self->pCodecCtx->channels; i++ ){
				PyTuple_SetItem(ret, i, PyString_FromStringAndSize( (const char*)avfrm->extended_data[i], data_size / self->pCodecCtx->channels ));
			}
		}
		else{
			ret = PyTuple_New(1);
			PyTuple_SetItem(ret, 0, PyString_FromStringAndSize( (const char*)avfrm->data[0], data_size ));
		}
	}
	
	av_packet_unref(&avpkt);
	av_free(avfrm);
	
	return ret;
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
	PyObject_HEAD_INIT(NULL)
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
	AVAudioResampleContext *pResampleCtx;
	int output_rate;
	int input_rate;
	int output_channel_layout;
	int input_channel_layout;
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
	
	if( !PyArg_ParseTupleAndKeywords( args, kw, "ii|iiii", kwlist,
		&self->output_rate,           &self->input_rate,
		&self->output_channel_layout, &self->input_channel_layout,
		&self->output_sample_format,  &self->input_sample_format
		) ){
		type->tp_free( self );
		return NULL;
	}
	
	self->pResampleCtx = avresample_alloc_context();
	
	if( self->pResampleCtx == NULL ){
		PyErr_SetString(FfmpegResampleError, "could not initialize resampler");
		type->tp_free( self );
		return NULL;
	}
	
	av_opt_set_int(self->pResampleCtx, "in_channel_layout",  self->input_channel_layout,  0);
	av_opt_set_int(self->pResampleCtx, "out_channel_layout", self->output_channel_layout, 0);
	av_opt_set_int(self->pResampleCtx, "in_sample_rate",     self->input_rate,            0);
	av_opt_set_int(self->pResampleCtx, "out_sample_rate",    self->output_rate,           0);
	av_opt_set_int(self->pResampleCtx, "in_sample_fmt",      self->input_sample_format,   0);
	av_opt_set_int(self->pResampleCtx, "out_sample_fmt",     self->output_sample_format,  0);
	
	avresample_open(self->pResampleCtx);
	
	return (PyObject *)self;
}

static void ffmpeg_resampler_dealloc( ffmpegResamplerObject* self ){
	avresample_free(&self->pResampleCtx);
}


// For some reason, Debian insists on packaging a version that doesn't have this, so the following is
// shamelessly stolen from samplefmt.c.
// see http://www.ffmpeg.org/doxygen/trunk/samplefmt_8c_source.html
int av_samples_alloc_array_and_samples(uint8_t ***audio_data, int *linesize, int nb_channels,
					int nb_samples, enum AVSampleFormat sample_fmt, int align)
{
	int ret, nb_planes = av_sample_fmt_is_planar(sample_fmt) ? nb_channels : 1;

	*audio_data = av_mallocz(nb_planes * sizeof(**audio_data));
	if (!*audio_data)
		return AVERROR(ENOMEM);
	ret = av_samples_alloc(*audio_data, linesize, nb_channels,
				nb_samples, sample_fmt, align);
	if (ret < 0)
		av_freep(audio_data);
	return ret;
}


static PyObject* ffmpeg_resampler_resample( ffmpegResamplerObject* self, PyObject* args ){
	const char** indata = NULL;
	int i;
	int innb;
	int inlen;
	int inplanes;
	uint8_t **outbuf;
	int outnb;
	int outlen;
	int outplanes = 0;
	PyObject* in  = NULL;
	PyObject* ret = NULL;
	
	if( !PyArg_ParseTuple( args, "O!", &PyTuple_Type, &in ) )
		return NULL;
	
	inplanes = PyTuple_Size(in);
	
	indata = malloc( sizeof(const char*) * inplanes );
	if( indata == NULL ){
		PyErr_SetString(FfmpegResampleError, "out of memory");
		return NULL;
	}
	for( i = 0; i < inplanes; i++ ){
		indata[i] = PyString_AsString(PyTuple_GetItem(in, i));
	}
	
	inlen = PyString_Size(PyTuple_GetItem(in, 0));
	innb  = inlen / av_get_bytes_per_sample(self->input_sample_format);
	
	outnb  = av_rescale_rnd(innb + avresample_get_delay(self->pResampleCtx),
				self->output_rate, self->input_rate, AV_ROUND_UP);
	
	outlen = av_samples_get_buffer_size(
		NULL, av_get_channel_layout_nb_channels(self->output_channel_layout),
		outnb, self->output_sample_format, 1
	);
	
	if( av_samples_alloc_array_and_samples(&outbuf, NULL,
			av_get_channel_layout_nb_channels(self->output_channel_layout),
			outnb, self->output_sample_format, 0) < 0 ){
		PyErr_SetString(FfmpegResampleError, "out of memory");
	}
	else if( avresample_convert(self->pResampleCtx, outbuf, 0, outnb, (uint8_t **)indata, 0, innb) < 0 ){
		PyErr_SetString(FfmpegResampleError, "resampling failed");
	}
	else{
		outplanes = 1;
		if(av_sample_fmt_is_planar(self->output_sample_format))
			outplanes = av_get_channel_layout_nb_channels(self->output_channel_layout);
		ret = PyTuple_New(outplanes);
		for( i = 0; i < outplanes; i++ )
			PyTuple_SetItem(ret, i, PyString_FromStringAndSize( (const char*)outbuf[i], outlen ));
	}
	
	free(indata);
	
	for( i = 0; i < outplanes; i++ ){
		free(outbuf[i]);
	}
	
	free(outbuf);
	
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
	PyObject_HEAD_INIT(NULL)
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
		return PyString_FromString( fmt_name );
	
	PyErr_SetString(PyExc_KeyError, "Sample format not recognized");
	return NULL;
}

static PyObject* ffmpeg_get_bytes_per_sample( PyObject* module, PyObject* args ){
	enum AVSampleFormat sample_fmt;
	int bps;
	
	if( !PyArg_ParseTuple( args, "i", &sample_fmt ) )
		return NULL;
	
	if( (bps = av_get_bytes_per_sample(sample_fmt)) )
		return PyInt_FromLong( bps );
	
	PyErr_SetString(PyExc_KeyError, "Sample format not recognized");
	return NULL;
}

static PyMethodDef ffmpegmodule_Methods[] = {
	{ "get_sample_fmt_name", (PyCFunction)ffmpeg_get_sample_fmt_name, METH_VARARGS, "get_sample_fmt_name(format)\nReturn the given sample format's name."},
	{ "get_bytes_per_sample", (PyCFunction)ffmpeg_get_bytes_per_sample, METH_VARARGS, "get_sample_fmt_name(format)\nReturn the size of one sample in bytes."},
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
	
	avcodec_register_all();
	av_register_all();
	avformat_network_init();
}


