# OreSat Star Tracker Software

Like all OreSat software projects it is built using OLAF (OreSat Linux App
Framework), which it built ontop of [CANopen for Python]. See the
[oresat-olaf repo] for more info about OLAF.

**NOTE:** The prucam-ar013x kernel module is required to use the camera and
will only work on the custom OreSat Star Tracker board. See the
[oresat-prucam-ar013x repo] for more info.

## Quickstart

Install Linux dependenies

```bash
$ sudo apt install swig
```

Install Python dependenies

```bash
$ pip3 install -r requirements.txt
```

Make a virtual CAN bus

```bash
$ sudo ip link add dev vcan0 type vcan
$ sudo ip link set vcan0 up
```

Run the Star Tracker app

```bash
$ python3 -m oresat_star_tracker
```

Can select the CAN bus to use (`vcan0`, `can0`, etc) with the `-b BUS` arg.

Can mock hardware by using the `-m HARDWARE` flag.

- The`-m all` flag can be used to mock all hardware (CAN bus is always
required).
- The `-m camera` flag would only mock camera.

See other options with `-h` flag.

A basic [Flask]-based website for development and integration can be found at
`http://localhost:8000` when the software is running.

## Unit Test

Run the unit tests

```bash
$ python3 -m unittest
```

[OpenStarTracker]: https://openstartracker.org
[OpenStarTracker repo]: https://github.com/UBNanosatLab/openstartracker
[Flask]: https://flask.palletsprojects.com/en/latest/
[oresat-olaf repo]: https://github.com/oresat/oresat-olaf
[CANopen for Python]: https://github.com/christiansandberg/canopen
[oresat-prucam-ar013x repo]: https://github.com/oresat/oresat-prucam-ar013x
