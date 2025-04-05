import base64
import os

import cv2
import numpy as np
from bottle import TEMPLATE_PATH, Bottle, request, template
from oresat_cand import NodeClient

from ..__init__ import __version__
from ..ar013x import Ar013x
from ..gen.star_tracker_od import StarTrackerEntry
from ..star_tracker import StarTracker

TEMPLATE_PATH.append(os.path.dirname(os.path.abspath(__file__)))


class Ui:
    def __init__(self, node: NodeClient, star_tracker: StarTracker):
        self.node = node
        self.star_tracker = star_tracker
        self.app = Bottle()

        self.app.route("/", "GET", self.get_index)
        self.app.route("/image", "GET", self.get_image)
        self.app.route("/data", "GET", self.get_data)
        self.app.route("/data", "PUT", self.put_data)

    def run(self):
        self.app.run(port=8000, quiet=True)

    def get_index(self):
        return template("index.tpl", version=__version__)

    def get_image(self) -> dict:
        if self.star_tracker.last_capture:
            raw = self.star_tracker.last_capture
            img = make_display_image(raw, downscale_factor=2)
        else:
            raw = np.zeros((Ar013x.MAX_ROWS, Ar013x.MAX_COLS, 3), dtype=np.uint8)
            img = make_display_image(raw, downscale_factor=2)
        return {"image": base64.encodebytes(img).decode("utf-8")}

    def get_data(self) -> dict:
        return {
            "status": self.node.od_read(StarTrackerEntry.STATUS).name,
            "capture": {
                "delay": self.node.od_read(StarTrackerEntry.CAPTURE_DELAY),
                "num_of_images": self.node.od_read(StarTrackerEntry.CAPTURE_NUM_OF_IMAGES),
                "save_captures": self.node.od_read(StarTrackerEntry.CAPTURE_SAVE_CAPTURES),
            },
        }

    def put_data(self):
        if "capture" in request.json:
            capture_data = request.json["capture"]
            if "delay" in capture_data:
                self.node.od_write(StarTrackerEntry.CAPTURE_DELAY, capture_data["delay"])
            if "num_of_images" in capture_data:
                self.node.od_write(
                    StarTrackerEntry.CAPTURE_NUM_OF_IMAGES, capture_data["num_of_images"]
                )
            if "save_captures" in capture_data:
                self.node.od_write(
                    StarTrackerEntry.CAPTURE_SAVE_CAPTURES, capture_data["save_captures"]
                )

        # do this last
        if "status" in request.json:
            self.star_tracker._set_state(request.json["status"])


def make_display_image(capture: np.ndarray, downscale_factor: int = 0) -> bytes:
    data = np.copy(capture)

    if downscale_factor > 0:
        data = data[::downscale_factor, ::downscale_factor]

    ok, encoded = cv2.imencode(".jpg", data)
    if not ok:
        raise ValueError("failed encode display image")

    return bytes(encoded)
