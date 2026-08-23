
all: ui_failplay.py myffmpeg/_ffmpeg.cpython-312-x86_64-linux-gnu.so

dep:
	sudo apt-get update
	sudo apt-get install -y \
		build-essential \
		python3-dev \
		python3-setuptools \
		python3-pyqt5 \
		pyqt5-dev-tools \
		python3-pyao \
		libao-dev \
		libavcodec-dev \
		libavformat-dev \
		libavutil-dev \
		libswresample-dev \
		python3-behave \
		python3-requests

test: all
	QT_QPA_PLATFORM=offscreen behave

ui_failplay.py: failplay.ui
	pyuic5 -o $@ $^

myffmpeg/_ffmpeg.cpython-312-x86_64-linux-gnu.so: myffmpeg/ffmpegmodule.c
	cd myffmpeg && python3 setup.py build_ext --inplace

