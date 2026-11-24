"""

Do tests with images that are NOT a star field
"""

import os
import shutil

from oresat_star_tracker import camera


# SETUP AND TEARDOWN
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


def teardown_module(module):
    """Clears the binary file from dev/prucam"""
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")

    # TODO: check that file exists
    os.remove(prucam_dir)


def test_setup():
    """Ensures"""
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")

    with open(prucam_dir, 'rb') as fd:
        print(fd)
        print("Opened prucam dir!")


def test_basic_camera():
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")

    test_cam = camera.BasicCamera(
        cap_dev=prucam_dir,
    )

    test_cam._read_raw()
    test_cam.capture()


def test_grayscale_camera():
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")

    test_cam = camera.GrayscaleCamera(
        cap_dev=prucam_dir,
    )
    test_cam._read_raw()
    test_cam.capture()
    test_cam.capture_l()
    test_cam.capture_rgb()


def test_color_camera():
    prucam_dir = os.path.join(os.path.dirname(__file__), "dev", "prucam")

    test_cam = camera.ColorCamera(
        cap_dev=prucam_dir,
    )
    test_cam._read_raw()
    test_cam.capture()
    test_cam.capture_l()
    test_cam.capture_rgb()
