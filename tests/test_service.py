"""

Do tests with images that are NOT a star field
"""

import pytest

import os
import shutil
import numpy as np

from oresat_star_tracker import camera
from oresat_star_tracker.star_tracker_service import StarTrackerService

from olaf import CanNetwork, Node
from oresat_configs import Mission, OreSatConfig

from PIL import Image


def setup_module(module):
    """Sets up dev/prucam to be an image that is NOT a star field"""
    # TODO: if directory does not exist, stop
    images_dir = os.path.join(os.path.dirname(__file__), "images")

    # TODO: Make a mocking directory

    # TODO: If directory does not exist, stop
    work_dir = os.path.join(os.path.dirname(__file__), "dev")

    # move the binary to `dev/prucam`
    # TODO: check that file exists before trying to copy it
    shutil.copy(os.path.join(images_dir, "not_stars_img.bin"), os.path.join(work_dir, "prucam"))
    
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")


def teardown_module(module):
    """Clears the binary file from dev/prucam"""
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")

    # TODO: check that file exists
    os.remove(prucam_dir)



@pytest.fixture
def st_service():
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")

    # node
    config = OreSatConfig(Mission.default())
    od = config.od_db["star_tracker_1"]
    network = CanNetwork("virtual", "vcan0")
    node = Node(network, od)
    node._setup_node()
    node._destroy_node()

    # make service...
    service = StarTrackerService(prucam_dir)
    service._event.set()
    service.start(node)
    service.stop()

    return service


def test_file_setup():
    """Ensures the directory exists"""
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")

    with open(prucam_dir, 'rb') as fd:
        print(fd)
        print("Opened prucam dir!")


def test_service_capture_only_mode(st_service):
    st_service._capture_only_mode()

def test_service_star_track_mode(st_service):
    st_service._star_track()


