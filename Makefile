.PHONY: beast
.PHONY: package
.PHONY: clean-beast
.PHONY: clean-package
CC = g++

beast:
	cd star_tracker/beast; \
	swig -python -py3 -c++ beast.i; \
	$(CC) -g -std=c++11 -Ofast -fPIC -c beast_wrap.cxx -o beast_wrap.o -lstdc++ $(shell pkg-config --cflags python3); \
	$(CC) -g -shared -fPIC beast_wrap.o -o _beast.so

package:
	bash package.sh

clean-beast:
	cd star_tracker/beast; \
	rm -f beast_wrap.cxx beast_wrap.o _beast.so beast.py; \
	rm -rf __pycache__

clean-package:
	rm -rf oresat-star-tracker*

clean: clean-beast clean-package
