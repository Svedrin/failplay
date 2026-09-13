
all: ui_failplay.py myffmpeg/_ffmpeg.cpython-312-x86_64-linux-gnu.so webfft/fft.wasm

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
		python3-requests \
		dbus-daemon \
		dbus-bin \
		emscripten \
		qrencode

test: all
	QT_QPA_PLATFORM=offscreen behave

ui_failplay.py: failplay.ui
	pyuic5 -o $@ $^

myffmpeg/_ffmpeg.cpython-312-x86_64-linux-gnu.so: myffmpeg/ffmpegmodule.c
	cd myffmpeg && python3 setup.py build_ext --inplace

# Standalone wasm module (no Emscripten JS runtime) used by the mobile web UI
# to render the FFT client-side. See webfft/fft.c for the exported ABI.
webfft/fft.wasm: webfft/fft.c
	emcc -O2 --target=wasm32 -nostdlib -Wl,--no-entry -Wl,--strip-all \
		-Wl,--allow-undefined -mbulk-memory \
		-o $@ $^

