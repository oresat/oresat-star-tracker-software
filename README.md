# OreSat Star Tracker Software

Algorithmic solving implemented with University of Washington HuskySat's [LOST]
star tracker program.

**NOTE:** The prucam-ar013x kernel module is required to use the camera and
will only work on the custom OreSat Star Tracker board. See the
[oresat-prucam-ar013x repo] for more info.

## Quickstart

Install Python dependenies

```bash
pip3 install .
```

Make a virtual CAN bus

```bash
sudo ip link add dev vcan0 type vcan
sudo ip link set vcan0 up
```

Run the Star Tracker app

```bash
python3 -m oresat_star_tracker
```

Can mock hardware by using the `-m HARDWARE` flag.

See other options with `-h` flag.

A basic [Bottle]-based website for development and integration can be found at
`http://localhost:8000` when the software is running.

## Unit Test

Run the unit tests

```bash
python3 -m unittest
```

[LOST]: https://github.com/UWCubeSat/lost
[Bottle]: https://flask.palletsprojects.com/en/latest/
[oresat-prucam-ar013x repo]: https://github.com/oresat/oresat-prucam-ar013x
