.PHONY: clean all

LDFLAGS =
ifeq ($(shell uname -s), Darwin)
	LDFLAGS += -Wl,-ld_classic -undefined dynamic_lookup
endif

OBJS = $(PYLIB_SOURCES:%.cpp=$(BUILD_DIR)/%.o) $(LIBB6_SOURCES:%.cc=$(BUILD_DIR)/%.o)
all:
	swig -python -c++ beast.i
	$(CXX) -g -std=c++11 -Ofast -fPIC -c beast_wrap.cxx -o beast_wrap.o -lstdc++ $(shell pkg-config --cflags python3)
	$(CXX) -g -shared -fPIC  $(LDFLAGS) beast_wrap.o -o _beast.so

clean:
	rm -f *.cpp *.cxx *.o *.so beast.py
