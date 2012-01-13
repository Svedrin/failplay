
all: ui_failplay.py

ui_failplay.py: failplay.ui
	pyuic4 -o $@ $^

