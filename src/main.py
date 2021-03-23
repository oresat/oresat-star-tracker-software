# main.py
# by Umair Khan, from the Portland State Aerospace Society

# Manages state and controls star tracker and camera.

# Imports - built-ins
import time
import threading
import logging
from enum import Enum

# Imports - external
from pydbus.generic import signal
from pydbus import SystemBus
from gi.repository import GLib
from systemd import journal

# Imports - custom modules
import camera
import solver

# Set up systemd logger
# modified from https://medium.com/@trstringer/logging-to-systemd-in-python-45150662440a
logger = logging.getLogger("org.OreSat.StarTracker")
journald_handler = journal.JournalHandler()
journald_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
logger.addHandler(journald_handler)
logger.setLevel(logging.DEBUG)

# State definitions
class State(Enum):
    STANDBY = 0
    STAR_TRACKING = 1
    CAPTURE = 2
    ERROR = 3

# Server
class StarTracker:

    # D-Bus XML definition
    # TODO: use method for state change
    dbus = """
    <node>
        <interface name='org.OreSat.StarTracker'>
            <signal name='Error'>
                <arg type='s' />
            </signal>
            <property name='capture_filepath' type='s' access='read'>
                <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true" />
            </property>
            <property name='capture_time' type='d' access='read'>
                <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true" />
            </property>
            <property name='coor' type='(dddd)' access='read'>
                <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true" />
            </property>
            <property name='solve_filepath' type='s' access='read'>
                <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true" />
            </property>
            <method name='set_state'>
                <arg type='i' name='new_state' direction='in' />
            </method>
            <method name='get_state'>
                <arg type='i' name='curr_state' direction='out' />
            </method>
        </interface>
    </node>
    """

    # Initialization
    def __init__(self):

        # D-Bus variables
        self.interface_name = "org.OreSat.StarTracker"
        self.Error = signal()
        self.PropertiesChanged = signal()

        # Set up initial state
        self.state = STANDBY

        # Set up booleans to control threads
        self.solving = False
        self.capturing = False

        # Properties
        self.capture_time = 0.0
        self.capture_path = ""
        self.dec = 0.0
        self.ra = 0.0
        self.ori = 0.0
        self.solve_length = 0.0
        self.solve_time = 0.0
        self.solve_path = ""

        # Set up capture thread
        self.camera = None
        self.c_thread = threading.Thread(target = self.capture_thread)
        self.c_lock = threading.Lock()

        # Set up solver thread
        self.solver = None
        self.s_thread = threading.Thread(target = self.solve_thread)
        self.s_lock = threading.Lock()

    # Startup
    # TODO: maybe pass in camera instead of dir? be agnostic to mock vs. real
    def start(self, sample_dir, median_path, config_path, db_path):

        # Always return to standby
        self.state_change(STANDBY)

        # Start up camera
        self.camera = camera.Camera(logger)
        self.camera.set_dir(sample_dir)

        # Start up solver
        # TODO: don't use sleep here
        self.solver = solver.Solver(logger)
        self.solver.startup(median_path, config_path, db_path)
        time.sleep(30)

        # Start threads
        self.c_thread.start()
        logger.info("Started capture thread.")
        self.s_thread.start()
        logger.info("Started solver thread.")

        # Start up D-Bus server
        bus = SystemBus()
        loop = GLib.MainLoop()
        bus.publish(self.interface_name, self)
        try:
            logger.info("Starting D-Bus loop...")
            loop.run()
        except KeyboardInterrupt as e:
            loop.quit()
            logger.info("Ended D-Bus loop.")
            self.end()

    # Change states
    # TODO: hold locks while changing
    def state_change(self, new_state):

        # Ignore invalid or reflexive transitions
        if not (STANDBY <= new_state <= ERROR) or new_state == self.state:
            return

        # Change state
        self.state == new_state
        if self.state == STANDBY or self.state == ERROR:
            self.solving = False
            self.capturing = False
        elif self.state == STAR_TRACKING:
            self.solving = True
            self.capturing = False
        elif self.state == CAPTURE:
            self.solving = False
            self.capturing = True

    # Change states
    # TODO: hold locks while changing
    def set_state(self, new_state):

        # Acquire locks
        self.s_lock.acquire()
        self.c_lock.acquire()

        # Ignore invalid or reflexive transitions
        ns = State(new)
        if not (State.STANDBY <= new_state <= ERROR) or new_state == self.state:
            return

        # Change state
        self.state == new_state
        if self.state == STANDBY or self.state == ERROR:
            self.solving = False
            self.capturing = False
        elif self.state == STAR_TRACKING:
            self.solving = True
            self.capturing = False
        elif self.state == CAPTURE:
            self.solving = False
            self.capturing = True

        # Release locks
        self.c_lock.release()
        self.s_lock.release()

    # Capture thread
    def capture_thread(self):

        # Keep going while this boolean is true
        # TODO: should not be while
        while (self.capturing):

            # Capture an image and update timestamp
            self.c_lock.acquire()
            self.capture_path, img = self.camera.capture()
            self.capture_time = time.time()
            self.c_lock.release()

            # Send property change signals
            # TODO: put in locked area
            self.PropertiesChanged(self.interface_name, {"capture_filepath": self.capture_path}, [])
            self.PropertiesChanged(self.interface_name, {"capture_time": self.capture_time}, [])
            time.sleep(0.5)

    # Solver thread
    def solver_thread(self):

        # Keep going while this boolean is true
        # TODO: should not be while
        while (self.solving):

            # Capture an image
            self.s_lock.acquire()
            self.solve_path, img = self.camera.capture()

            # Solve the image
            self.dec, self.ra, self.ori, self.solve_length = self.solver.solve(img)
            if self.dec == self.ra == self.ori == 0.0:
                logger.error("Bad solve ({}).".format(self.solve_path))
                self.Error("Bad solve ({})".format(self.solve_path))
                time.sleep(0.5)
                continue

            # Update the solution timestamp
            self.solve_time = time.time()
            self.st_lock.release()

            # Send property change signals
            # TODO: put in locked area
            self.PropertiesChanged(self.interface_name, {"coor": (self.dec, self.ra, self.ori, self.solve_time)}, [])
            self.PropertiesChanged(self.interface_name, {"solve_filepath": self.solve_path}, [])
            time.sleep(0.5)

    # Stop threads in preparation to exit
    def end(self):
        self.state_change(STANDBY)
        if self.c_thread.is_alive():
            self.c_thread.join()
        if self.s_thread.is_alive():
            self.s_thread.join()

    # Filepath of last captured image
    @property
    def capture_filepath(self):
        self.c_lock.acquire()
        capture_path = self.capture_path
        self.c_lock.release()
        return capture_path

    # Timestamp of last captured image
    @property
    def capture_time(self):
        self.c_lock.acquire()
        capture_time = self.capture_time
        self.c_lock.release()
        return capture_time

    # Coordinates
    @property
    def coor(self):
        self.s_lock.acquire()
        dec, ra, ori, solve_time = self.dec, self.ra, self.ori, self.solve_time
        self.s_lock.release()
        return (dec, ra, ori, solve_time)

    # Filepath of last solved image
    @property
    def solve_filepath(self):
        self.s_lock.acquire()
        solve_path = self.solve_path
        self.s_lock.release()
        return solve_path

##########

# # Test if run independently
# if __name__ == "__main__":
#     server = StarTracker()
#     db_root = "/usr/share/oresat-star-tracker/data/"
#     data_root = db_root + "downsample/"
#     server.start(data_root + "median_image.png", data_root + "calibration.txt", db_root + "hip_main.dat", sample_dir = data_root + "samples/")