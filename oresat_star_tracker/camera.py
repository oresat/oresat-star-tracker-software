"""Star tracker AR013x camera"""

import io
import os
from enum import Enum
from pathlib import Path
import cv2
import numpy as np
from olaf import logger


class CameraState(Enum):
    STANDBY = 1
    RUNNING = 2
    LOCKOUT = 3
    NOT_FOUND = 4
    ERROR = 5


class CameraError(Exception):
    """An error has occured with camera"""


class Camera:
    """Star tracker AR013x camera"""

    # these files are provided by the prucam-dkms debian package

    CAPTURE_PATH = Path("/dev/prucam")
    MAX_COLS = 1280
    MAX_ROWS = 960
    PIXEL_BYTES = MAX_COLS * MAX_ROWS

    def __init__(self, mock: bool = False):
        self._mock = mock
        self._state = CameraState.LOCKOUT
        self._image_size = (self.MAX_COLS, self.MAX_ROWS)
        self._mock_data = np.zeros((self.MAX_COLS, self.MAX_ROWS, 3), dtype=np.uint8)

        if self._mock:
            self._state = CameraState.RUNNING
            return

        if not self.CAPTURE_PATH.exists():
            self._state = CameraState.NOT_FOUND
            logger.error("Could not find capture path")
            return

        # no errors; attempt to read image
        self._state = CameraState.RUNNING
        self._image_size = self.read_image_size()
        logger.info("Camera is unlocked")

    def read_image_size(self):
        """Read dimensions of image from the camera"""
        if self._state != CameraState.RUNNING:
            raise CameraError(f"Camera error; state is {self._state}")
        if self._mock:
            return self._image_size
        x_size = self.read_context_setting("x_size")
        y_size = self.read_context_setting("y_size")
        return (y_size, x_size)

    def read_context_setting(self, name: str) -> int:
        """'Read a context setting."""
        if self._state != CameraState.RUNNING:
            raise CameraError(f"Camera error; state is {self._state}")
        context_path = "/sys/devices/platform/prucam/context_settings"
        with open(f"{context_path}/{name}", "r") as f:
            value = int(f.read())
            return value
        # path check

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

        if self._state != CameraState.RUNNING:
            raise CameraError(f"Camera error; state is {self._state}")

        if self._mock:
            return self._mock_data
        # Read raw data
        capture_path = str(self.CAPTURE_PATH)
        fd = os.open(capture_path, os.O_RDWR)
        fio = io.FileIO(fd, closefd=False)
        imgbuf = bytearray(self._image_size[0] * self._image_size[1])
        fio.readinto(imgbuf)
        fio.close()
        os.close(fd)

        # Convert to image
        img = np.frombuffer(imgbuf, dtype=np.uint8).reshape(
            self._image_size[0], self._image_size[1]
        )

        # Convert to color
        if color is True:
            return cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)

        return img

    @property
    def state(self) -> CameraState:
        return self._state
