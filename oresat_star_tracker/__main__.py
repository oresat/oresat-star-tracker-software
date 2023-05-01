'''Star Tracker App'''

import os

from olaf import app, olaf_setup, olaf_run

from .star_tracker_resource import StarTrackerResource


def main():
    path = os.path.dirname(os.path.abspath(__file__))

    args = olaf_setup(f'{path}/data/oresat_star_tracker.dcf')
    mock_args = [i.lower() for i in args.mock_hw]
    mock_camera = 'camera' in mock_args or 'all' in mock_args


    app.add_resource(StarTrackerResource(mock_camera))

    olaf_run()

if __name__ == '__main__':
    main()
