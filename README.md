# oresat-star-tracker-software

### Introduction

This is a modified version of [OpenStarTracker](https://openstartracker.org), originally developed by Andrew Tennenbaum at the University at Buffalo. Some of the information below comes from the original README file in the [OpenStarTracker repository](https://github.com/UBNanosatLab/openstartracker).

### Dependencies

The following should be readily available from standard package repositories.

```
$ sudo apt install python3 python3-numpy python3-opencv python3-pydbus python3-systemd
```

In addition, this software depends on [python3-prucam](https://github.com/oresat/oresat-linux-prucam) and [swig](http://swig.org/) (version 4.0.1 or greater), both of which will likely have to be manually built and installed.

### Building

```
$ dpkg-buildpackage -us -uc
```

Running this from the root of the repository will create a `.deb` file (along with a bunch of other things) in the directory one level above.

### Installing

```
$ sudo dpkg -i [name].deb
```

### Usage

```
# Start the daemon
sudo systemctl start oresat-star-trackerd

# Stop the daemon
sudo systemctl stop oresat-star-trackerd
```

The star tracker runs as a daemon, which sends runtime details to `/var/log/syslog` and exposes the following methods and properties via D-Bus. Note that states are encoded as integers, where `0` represents the standby state and `1` represents the solving state.

- `CurrentState` -- Current state.
- `CapturePath` -- Filepath of last image manually captured.
- `SolvePath` -- Filepath of last image for which a solution was attempted.
- `Coor` -- The results of the last solution attempt, represented as (declination, right ascension, orientation, Unix timestamp). If the first three numbers are all 0, it means the solution attempt failed.
- `Capture()` -- A method to take a photo and update `CapturePath`. Only works when in standby.
- `ChangeState(NewState)` -- A method to change states.

### Behavior

After being started, the daemon will first load and filter the star database in memory and then go into standby mode. This process may take five minutes or more.

While in standby mode, images can be manually captured and saved using the `Capture()` function. If put in the solving state, the software will automatically take images and attempt to solve them continuously. In this state, calling the `Capture()` function will not do anything.

Images will be stored in `/usr/share/oresat-star-tracker/data/[snaps|solves]`, with the former being used for manual captures and the latter for automatic captures during star tracking. Each folder will contain (up to) the most recent fifty images, though `CapturePath` and `SolvePath` will only point to the most recent images.