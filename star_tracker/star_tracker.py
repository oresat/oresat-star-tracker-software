# main.py
# by Umair Khan, from the Portland State Aerospace Society

# Manages state and controls star tracker and camera.

# Imports - built-ins
import time
import threading
import logging
from enum import Enum

# Imports - external
from pydbus import SystemBus
from gi.repository import GLib
from systemd import journal

# Imports - custom modules
from star_tracker.snapper import Snapper
from star_tracker.solver import Solver

# Set up systemd logger
# modified from https://trstringer.com/systemd-logging-in-python/
logger = logging.getLogger("org.OreSat.StarTracker")
journald_handler = journal.JournalHandler()
journald_handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
logger.addHandler(journald_handler)
logger.setLevel(logging.DEBUG)

# State definitions
class State(Enum):
    STANDBY = 0
    SOLVE = 1

# Server
class StarTracker:

    # D-Bus XML definition
    dbus = """
    <node>
        <interface name='org.OreSat.StarTracker'>
            <property name='CapturePath' type='s' access='read' />
            <property name='SolvePath' type='s' access='read' />
            <property name='Coor' type='(dddd)' access='read' />
            <method name='Capture' />
            <method name='ChangeState'>
                <arg type='i' name='NewState' direction='in' />
            </method>
        </interface>
    </node>
    """

    # Initialization
    def __init__(self):

        # Set up interface name and initial state
        self.interface_name = "org.OreSat.StarTracker"
        self.state = State.STANDBY

        # Set up properties
        self.capture_path = ""
        self.solve_path = ""
        self.dec = 0.0
        self.ra = 0.0
        self.ori = 0.0
        self.solve_time = 0.0

        # Set up snapper variables
        self.snapper = None

        # Set up solver variables
        self.solver = None
        self.stop_thread = False
        self.s_thread = threading.Thread(target = self.solver_thread)
        self.s_lock = threading.Lock()

        # Set up counting variables
        self.snap_count = 0
        self.solve_count = 0

    # Change states
    def set_state(self, new_state):

        # Acquire lock
        self.s_lock.acquire()

        # Ignore reflexive or invalid transitions
        ns = State(new_state)
        if (ns == self.state) or not (ns == State.STANDBY or ns == State.SOLVE):
            self.s_lock.release()
            logger.info("New state is either invalid or matches current state.")
            return

        # Change state and release lock
        self.state = ns
        self.s_lock.release()

        # Log the new state
        logger.info(f"State set to {self.state}.")

    # Startup sequence
    def start(self, median_path, config_path, db_path):

        # Always start in standby
        self.set_state(State.STANDBY)

        # Start up camera
        self.snapper = Snapper(logger)

        # Start up solver
        self.solver = Solver(logger)
        self.solver.startup(median_path, config_path, db_path)

        # Start solver thread
        self.s_thread.start()
        logger.info("Started solver thread.")

        # Start up D-Bus server
        bus = SystemBus()
        loop = GLib.MainLoop()
        bus.publish(self.interface_name, self)
        try:
            logger.info("Starting D-Bus loop.")
            loop.run()
        except KeyboardInterrupt as e:
            loop.quit()
            logger.info("Ended D-Bus loop.")
            self.end()

    # Stop solver thread in preparation to exit
    def end(self):
        self.set_state(State.STANDBY)
        self.stop_thread = True
        self.s_thread.join()

    # Solver thread
    def solver_thread(self):

        # Keep going until the thread exits
        while True:

            # If we're in the solve state, capture and solve an image
            if self.state == State.SOLVE:

                # Acquire lock
                self.s_lock.acquire()

                # Capture an image and set property
                cap_path = self.snapper.capture_solve(self.solve_count)
                self.solve_count += 1
                self.solve_path = cap_path

                # Solve the image and set properties
                self.dec, self.ra, self.ori, self.solve_time = self.solver.solve(cap_path)

                # Release lock
                self.s_lock.release()

            # If it's time to exit, break
            if self.stop_thread:
                break

            # Sleep for half a second (target solve rate is 2Hz)
            time.sleep(0.5)

    # Take a snap (D-Bus method)
    def Capture(self):

        # Make sure we're in the standby state
        if self.state != State.STANDBY:
            return

        # Take a photo and set properties
        cap_path = self.snapper.capture_snap(self.snap_count)
        self.snap_count += 1
        self.capture_path = cap_path

    # Change the state from outside (D-Bus method)
    def ChangeState(self, NewState):
        self.set_state(NewState)

    # Filepath of last captured snap
    @property
    def CapturePath(self):
        return self.capture_path

    # Filepath of last solved image
    @property
    def SolvePath(self):
        self.s_lock.acquire()
        solve_path = self.solve_path
        self.s_lock.release()
        return solve_path

    # Coordinates
    @property
    def Coor(self):
        self.s_lock.acquire()
        dec, ra, ori, solve_time = self.dec, self.ra, self.ori, self.solve_time
        self.s_lock.release()
        return (dec, ra, ori, solve_time)
