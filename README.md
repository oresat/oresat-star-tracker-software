# OreSat Star Tracker Software

Like all OreSat software projects it is built using OLAF (OreSat Linux App
Framework), which it built ontop of [CANopen for Python]. See the
[oresat-olaf repo] for more info about OLAF.

Algorithmic solving implemented with University of Washington HuskySat's [LOST]
star tracker program.

**NOTE:** The prucam-ar013x kernel module is required to use the camera and
will only work on the custom OreSat Star Tracker board. See the
[oresat-prucam-ar013x repo] for more info.

## Quickstart

Install Python dependenies

```bash
$ pip3 install -e .[dev]
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

## Unit Test and Coverage

Unit tests are managed using PyTest. The total number of test cases executed (currently over 25) includes parameterized tests which check multiple scenarios with a single function definition.

Run the unit tests and generate a report showing missing code lines:

```bash
$ PYTHONPATH=. python3 -m pytest --cov=oresat_star_tracker --cov-report=term-missing
```
| Command | Purpose |
| :--- | :--- |
| `--cov=oresat_star_tracker` | Enables **code coverage** collection for the main package. |
| `--cov-report=term-missing`| Prints a summary to the terminal, including lines of code not covered by tests. |

[LOST]: https://github.com/UWCubeSat/lost
[Flask]: https://flask.palletsprojects.com/en/latest/
[oresat-olaf repo]: https://github.com/oresat/oresat-olaf
[CANopen for Python]: https://github.com/christiansandberg/canopen
[oresat-prucam-ar013x repo]: https://github.com/oresat/oresat-prucam-ar013x
