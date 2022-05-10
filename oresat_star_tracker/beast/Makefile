.PHONY: clean all

all:
				swig -python -py3 -c++ beast.i
				$(CXX) -g -std=c++11 -Ofast -fPIC -c beast_wrap.cxx -o beast_wrap.o -lstdc++ $(shell pkg-config --cflags python3)
				$(CXX) -g -shared -fPIC beast_wrap.o -o _beast.so

clean:
				rm -f *.cpp *.cxx *.o *.so beast.py
