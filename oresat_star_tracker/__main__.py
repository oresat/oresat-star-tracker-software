"""Star Tracker App"""

import os

from olaf import app, olaf_run, olaf_setup, render_olaf_template, rest_api
from oresat_configs import NodeId

from . import __version__
from .star_tracker_service import StarTrackerService


@rest_api.app.route("/star-tracker")
def star_tracker_template():
    """Render the star tracker web page."""
    return render_olaf_template("star_tracker.html", name="Star Tracker")


def main():
    """Star Tracker OLAF app main."""
    path = os.path.dirname(os.path.abspath(__file__))

    args, _ = olaf_setup(NodeId.STAR_TRACKER_1)
    mock_args = [i.lower() for i in args.mock_hw]
    mock_camera = "camera" in mock_args or "all" in mock_args

    app.od["versions"]["sw_version"].value = __version__

    app.add_service(StarTrackerService(mock_camera))

    rest_api.add_template(f"{path}/templates/star_tracker.html")

    olaf_run()


if __name__ == "__main__":
    main()
