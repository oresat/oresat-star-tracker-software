'''Star Tracker App'''

from os.path import dirname, abspath
from olaf import app, olaf_run
from .star_tracker_resource import StarTrackerResource


def main():
    app.add_resource(StarTrackerResource)

    eds_file = dirname(abspath(__file__)) + '/data/star_tracker.dcf'
    olaf_run(eds_file)


if __name__ == '__main__':
    main()
