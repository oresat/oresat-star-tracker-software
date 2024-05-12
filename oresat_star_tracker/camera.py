"""Star tracker AR013x camera"""

import sys
import io
import os
from os.path import abspath, dirname
from enum import Enum

import cv2
import numpy as np
from olaf import logger


class CameraError(Exception):
    """An error has occured with camera"""


class Camera:
    """Star tracker AR013x camera"""

    # these files are provide by the prucam-dkms debian package

    def __init__(self, mock: bool = False):
        self._mock = mock
        
        if self._mock:
            self.state = CameraState.MOCK
            self._capture_path = f"{dirname(abspath(__file__))}/data/mock.bmp"
        else:
            self._capture_path = "/dev/prucam"
            try:
                self.image_size = self.read_image_size()
            except FileNotFoundError:
                self.state = CameraState.NOT_FOUND
                logger.debug("Camera device not found")
            else:
                self.state = CameraState.RUNNING

    def read_image_size(self):
        """Read dimensions of image from the camera"""
        x_size = self.read_context_setting("x_size")
        y_size = self.read_context_setting("y_size")
        return (y_size, x_size)

    def read_context_setting(self, name: str) -> int:
        """'Read a context setting."""
        context_path = "/sys/devices/platform/prucam/context_settings"
        with open(f"{context_path}/{name}", "r") as f:
            value = int(f.read())
            return value

    def capture(self, color: bool = True) -> np.ndarray:
        """Capture an image

        Parameters
        ----------
        color: bool
            enable color

        Raises
        ------
        CameraError
            failed to capture image

        Returns
        -------
        numpy.ndarray
            image data in numpy array
        """

        if self._mock:
            img = cv2.imread(self._capture_path, cv2.IMREAD_COLOR)
        else:
            # Read raw data
            fd = os.open(self._capture_path, os.O_RDWR)
            fio = io.FileIO(fd, closefd=False)
            imgbuf = bytearray(self.image_size[0] * self.image_size[1])
            fio.readinto(imgbuf)
            fio.close()
            os.close(fd)

            # Convert to image
            img = np.frombuffer(imgbuf, dtype=np.uint8).reshape(
                self.image_size[0], self.image_size[1]
            )

            # Convert to color
            if color is True:
                img = cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)

        return img
