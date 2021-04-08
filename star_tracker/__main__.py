# daemon.py - daemonizer for the star tracker
# by Umair Khan and Ryan Medick, from the Portland State Aerospace Society

# Imports (internal)
import sys
import os
from argparse import ArgumentParser

# Imports (external)
from star_tracker.main import StarTracker


def _daemonize(pid_file: str):
    """Daemonize the process

    Parameters
    ----------
    pid_file: str
        The path to the pid file for the daemon.
    """

    # Check for a pidfile to see if the daemon is already running
    try:
        with open(pid_file, 'r') as fptr:
            pid = int(fptr.read().strip())
    except IOError:
        pid = None

    if pid:
        sys.stderr.write("pid file {0} already exist".format(pid_file))
        sys.exit(1)

    try:
        pid = os.fork()
        if pid > 0:
            # exit from parent
            sys.exit(0)
    except OSError as err:
        sys.stderr.write('fork failed: {0}\n'.format(err))
        sys.exit(1)

    # decouple from parent environment
    os.chdir('/')
    os.setsid()
    os.umask(0)

    # redirect standard file descriptors
    sys.stdout.flush()
    sys.stderr.flush()
    stdin = open(os.devnull, 'r')
    stdout = open(os.devnull, 'a+')
    stderr = open(os.devnull, 'a+')

    os.dup2(stdin.fileno(), sys.stdin.fileno())
    os.dup2(stdout.fileno(), sys.stdout.fileno())
    os.dup2(stderr.fileno(), sys.stderr.fileno())

    pid = str(os.getpid())
    with open(pid_file, 'w+') as fptr:
        fptr.write(pid + '\n')


# Run script
if __name__ == "__main__":
    pid_file = "/run/oresat-star-trackerd.pid"

    parser = ArgumentParser()
    parser.add_argument("-d", "--daemon", action="store_true",
                        help="daemonize the process")
    args = parser.parse_args()

    if args.daemon:
        _daemonize(pid_file)

    data_dir = "/usr/share/oresat-star-tracker/data/"
    st = StarTracker()
    st.start(data_dir + "median-image.png", data_dir + "configuration.txt", data_dir + "hipparcos.dat")

    if args.daemon:
        os.remove(pid_file)  # clean up daemon
