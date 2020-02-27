.PHONY: beast
CC = g++
INSTALL_DIR = /opt/oresat-star-tracker/

install-conf:
	cp configs/org.OreSat.StarTracker.conf /usr/share/dbus-1/system.d/
	cp configs/oresat-startrackerd.service /usr/lib/systemd/system/

install:
	mkdir -p $(INSTALL_DIR)
	cp -r beast $(INSTALL_DIR)
	cp -r datasets $(INSTALL_DIR)
	cp hip_main.dat $(INSTALL_DIR)
	cp startracker.py $(INSTALL_DIR)
	cp startracker_daemon.py $(INSTALL_DIR)

beast:
	cd beast; \
	swig -python -py3 -c++ beast.i; \
	$(CC) -g -std=c++11 -Ofast -fPIC -c beast_wrap.cxx -o beast_wrap.o -lstdc++ $(shell pkg-config --cflags python3); \
	$(CC) -g -shared -fPIC beast_wrap.o -o _beast.so

clean:
	cd beast; \
	rm beast_wrap.cxx beast_wrap.o _beast.so beast.py; \
	rm -r __pycache__
