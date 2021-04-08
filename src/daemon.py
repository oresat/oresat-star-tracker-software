# startracker_daemon.py - daemonizer for the star tracker
# by Umair Khan and Ryan Medick, from the Portland State Aerospace Society

# Imports (internal)
import sys
import os
import time
import atexit
import signal

# Imports (external)
import main

# Class definition
class StarTrackerDaemon:

    # Initialize PID file and data directory
    def __init__(self, pidfile):
        self.pidfile = pidfile
        self.data_dir = None

    # Daemonize the class by forking
    def daemonize(self):

        # Make the first child (the parent exits)
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #1 failed: {0}\n'.format(err))
            sys.exit(1)

        # Decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)

        # Make the second child (the parent exits)
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as err:
            sys.stderr.write('fork #2 failed: {0}\n'.format(err))
            sys.exit(1)

        # Redirect file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')

        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

        # Write PID file
        atexit.register(self.delpid)
        pid = str(os.getpid())
        with open(self.pidfile,'w+') as f:
            f.write(pid + '\n')

    # Delete PID file
    def delpid(self):
        os.remove(self.pidfile)

    # Start the daemon
    def start(self, data_dir):

        # Set the working directory
        self.data_dir = data_dir

        # Check for a pidfile to see if the daemon is already running
        try:
            with open(self.pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        # If so, don't do anything
        if pid:
            message = "pidfile {0} already exists. Daemon already running?\n".format(self.pidfile)
            sys.stderr.write(message)
            sys.exit(1)

        # Start the daemon
        self.daemonize()
        self.run()

    # Stop the daemon
    def stop(self):

        # Get the pid from the pidfile
        try:
            with open(self.pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None

        if not pid:
            message = "pidfile {0} does not exist. Daemon not running?\n".format(self.pidfile)
            sys.stderr.write(message)
            return

        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if e.find("No such process") > 0:
                if os.path.exists(self.pidfile):
                    os.remove(self.pidfile)
            else:
                print(str(err.args))
                sys.exit(1)

    # Restart the daemon
    def restart(self, data_dir):
        self.stop()
        self.start(data_dir)

    # Run the star tracker
    def run(self):
        st = main.StarTracker()
        st.start(self.data_dir + "median-image.png", self.data_dir + "configuration.txt", self.data_dir + "hipparcos.dat")

# Run script
if __name__ == "__main__":
    assert len(sys.argv) > 1, "usage:\t{0} start\n\t\t\t{0} stop\n\t\t\t{0} restart".format(sys.argv[0])
    daemon = StarTrackerDaemon('/run/oresat-star-tracker.pid')
    data_dir = "/usr/share/oresat-star-tracker/data/"
    if 'start' == sys.argv[1]:
        daemon.start(data_dir)
    elif 'stop' == sys.argv[1]:
        daemon.stop()
    elif 'restart' == sys.argv[1]:
        daemon.restart(data_dir)
    else:
        print("Unknown command")
        sys.exit(2)
    sys.exit(0)
