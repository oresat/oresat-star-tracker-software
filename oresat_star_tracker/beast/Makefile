.PHONY: beast clean

all:
	swig -python -py3 -c++ beast.i; \
	$(CC) -g -std=c++11 -Ofast -fPIC -c beast_wrap.cxx -o beast_wrap.o -lstdc++ $(shell pkg-config --cflags python3); \
	$(CC) -g -shared -fPIC beast_wrap.o -o _beast.so

clean:
	rm -f *.cxx *.o *.so beast.py
