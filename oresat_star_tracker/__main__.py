'''Star Tracker App'''

import os

from olaf import app, rest_api, olaf_setup, olaf_run, render_olaf_template

from .star_tracker_resource import StarTrackerResource


@rest_api.app.route('/camera')
def camera_template():
    return render_olaf_template('camera.html', name='Camera')


@rest_api.app.route('/star-track')
def star_tracker_template():
    return render_olaf_template('star_track.html', name='Star Track')


def main():
    path = os.path.dirname(os.path.abspath(__file__))

    args = olaf_setup(f'{path}/data/oresat_star_tracker.dcf')
    mock_args = [i.lower() for i in args.mock_hw]
    mock_camera = 'camera' in mock_args or 'all' in mock_args

    app.add_resource(StarTrackerResource(mock_camera))

    rest_api.add_template(f'{path}/templates/camera.html')
    rest_api.add_template(f'{path}/templates/star_track.html')

    olaf_run()


if __name__ == '__main__':
    main()
