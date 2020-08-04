# main.py
# by Umair Khan, from the Portland State Aerospace Society

# Manages state and controls star tracker and camera.

"""
main.py
==============
The main coordinator for the star tracker system, which manages the state machine and
controls the camera and the solver.
"""

# Imports - built-ins
import time
import threading
import logging

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

# Server
class StarTracker:

    # XML definition
    dbus = """
    <node>
        <interface name='org.OreSat.StarTracker'>
            <signal name='error'>
                <arg type='s' />
            </signal>
            <property name='coor' type='(dddd)' access='read'>
                <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true" />
            </property>
            <property name='filepath' type='s' access='read'>
                <annotation name="org.freedesktop.DBus.Property.EmitsChangedSignal" value="true" />
            </property>
        </interface>
    </node>
    """

    # Error signal
    error = signal()
    PropertiesChanged = signal()

    # Initialize properties and worker thread
    def __init__(self):

        # Properties
        self.dec = 0.0
        self.ra = 0.0
        self.ori = 0.0
        self.l_solve = 0.0
        self.t_solve = 0.0
        self.p_solve = ""
        self.interface_name = "org.OreSat.StarTracker"

        # Set up camera
        self.camera = camera.Camera(logger)

        # Set up star tracker solver
        self.st = solver.Solver(logger)
        self.st_thread = threading.Thread(target = self.star_tracker)
        self.st_lock = threading.Lock()
        self.st_running = True

    # Star tracker thread
    def star_tracker(self):

        # Keep going while we're running
        while (self.st_running):

            # Capture an image
            self.st_lock.acquire()
            self.p_solve, img = self.camera.capture()
            # self.PropertiesChanged(self.interface_name, {"filepath": self.p_solve}, [])

            # Solve the image
            self.dec, self.ra, self.ori, self.l_solve = self.st.solve(img)
            # self.PropertiesChanged(self.interface_name, {"coor": self.dec}, []) #TODO need to handle the struct
            if self.dec == self.ra == self.ori == 0.0:
                self.st.error("bad solve")
                logger.error("bad solve (for {})".format(p_solve))
                error("bad solve")
                time.sleep(0.5)
                continue

            # Update the solution timestamp
            self.t_solve = time.time()
            self.st_lock.release()

            # Send property signal
            self.PropertiesChanged(self.interface_name, {"filepath": self.p_solve}, [])
            time.sleep(0.5)

    # Start up solver and server
    def start(self, median_path, config_path, db_path, sample_dir = None):

        # Start up camera
        self.camera.set_dir(sample_dir)

        # Start up star tracker
        self.st.startup(median_path, config_path, db_path)
        time.sleep(20)
        self.st_thread.start()
        logger.info("Started worker thread")

        # Start up D-Bus server
        bus = SystemBus()
        loop = GLib.MainLoop()
        bus.publish(self.interface_name, self)
        try:
            logger.info("Starting D-Bus loop...")
            loop.run()
        except KeyboardInterrupt as e:
            loop.quit()
            logger.info("Ended D-Bus loop")
            self.end()

    # Stop threads in preparation to exit
    def end(self):
        self.st_running = False
        if self.st_thread.is_alive():
            self.st_thread.join()

    # Coordinates
    @property
    def coor(self):
        self.st_lock.acquire()
        dec, ra, ori, t_solve = self.dec, self.ra, self.ori, self.t_solve
        self.st_lock.release()
        return (dec, ra, ori, t_solve)

    # Filepath of last solved image
    @property
    def filepath(self):
        self.st_lock.acquire()
        p_solve = self.p_solve
        self.st_lock.release()
        return p_solve

##########

# Test if run independently
if __name__ == "__main__":
    server = StarTracker()
    db_root = "/usr/share/oresat-star-tracker/data/"
    data_root = db_root + "downsample/"
    server.start(data_root + "median_image.png", data_root + "calibration.txt", db_root + "hip_main.dat", sample_dir = data_root + "samples/")