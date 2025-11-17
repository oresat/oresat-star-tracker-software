# OreSat Star Tracker Software

Like all OreSat software projects it is built using OLAF (OreSat Linux App
Framework), which it built ontop of [CANopen for Python]. See the
[oresat-olaf repo] for more info about OLAF.

Algorithmic solving implemented with University of Washington HuskySat's [LOST] 
star tracker program.

**NOTE:** The prucam-ar013x kernel module is required to use the camera and
will only work on the custom OreSat Star Tracker board. See the
[oresat-prucam-ar013x repo] for more info.

## Quickstart: Setting up the Development Environment

This project uses **`uv`** for fast dependency management and **`direnv`** to automatically create and activate a virtual environment when you enter the project directory.

### 1. Install `uv` and `direnv`

Ensure you have **`uv`** and **`direnv`** installed on your system.
(Installation methods vary by OS, but `pipx` for `uv` and your system's package manager for `direnv` are common.)

> Example `uv` installation via `pipx` (recommended):
> ```bash
> $ pipx install uv
> ```

> Example `direnv` installation on Debian/Ubuntu:
> ```bash
> $ sudo apt-get install direnv
> ```
### 2. Configure direnv in the Project Root

Navigate to the project's root directory (oresat-star-tracker-software/). You need to create a file named .envrc that instructs direnv to use uv to create and load a virtual environment named .venv.

> Run the following commands to create the .envrc file with the correct content:
> ```bash
> # 1. Start by setting the virtual environment name
> $ echo 'export VIRTUAL_ENV_NAME=".venv"' > .envrc
>
> # 2. Tell direnv to use the 'python' layout (which uses uv by default)
> # and set the directory and prompt name.
> $ echo 'layout python $VIRTUAL_ENV_NAME --prompt "(star-tracker)"' >> .envrc
>
> # OPTIONAL: Explicitly ensure direnv uses uv if it's set up to use venv/conda by default
> $ echo 'export DIRENV_DEFAULT_LAYOUT="uv"' >> .envrc
> ```
Result: The file .envrc in your project root will now contain:

> ```bash
> export VIRTUAL_ENV_NAME=".venv"
> layout python .venv --prompt "(star-tracker)"
> export DIRENV_DEFAULT_LAYOUT="uv"
> ```

### 3. Allow direnv to Load the Environment

The first time you create a new .envrc file, you must explicitly allow it. This will immediately execute the commands inside and create the virtual environment using uv.
> ```bash
> $ direnv allow
> ```
Upon running this, uv will automatically create the .venv directory and virtual environment, and your terminal prompt will change to show (star-tracker).

### 4. Install Python Dependencies

With the virtual environment now active (indicated by (star-tracker) in your terminal prompt), install the project and its development dependencies using uv.

```bash
$ uv pip install -e .[dev]
```

### 5. Create a virtual CAN bus

A virtual CAN bus is needed for testing and development.

```bash
$ sudo ip link add dev vcan0 type vcan
$ sudo ip link set vcan0 up
```

### 6. Run the Star Tracker app

The Python application can now be run from the activated environment:

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

# Unit Test and Coverage

Unit tests are managed using PyTest. The total number of test cases executed (currently over 20) includes parameterized tests which check multiple scenarios with a single function definition.

Run the unit tests and generate a report showing missing code lines. Ensure your (star-tracker) environment is active.

```bash
$ pytest
```

[LOST]: https://github.com/UWCubeSat/lost
[NASA-COTS]: https://github.com/nasa/COTS-Star-Tracker
[Flask]: https://flask.palletsprojects.com/en/latest/
[oresat-olaf repo]: https://github.com/oresat/oresat-olaf
[CANopen for Python]: https://github.com/christiansandberg/canopen
[oresat-prucam-ar013x repo]: https://github.com/oresat/oresat-prucam-ar013x
