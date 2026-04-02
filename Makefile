
all: ui_failplay.py myffmpeg/_ffmpeg.cpython-312-x86_64-linux-gnu.so

ui_failplay.py: failplay.ui
	pyuic5 -o $@ $^

myffmpeg/_ffmpeg.cpython-312-x86_64-linux-gnu.so: myffmpeg/ffmpegmodule.c
	cd myffmpeg && python3 setup.py build_ext --inplace

