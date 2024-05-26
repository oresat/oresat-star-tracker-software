"""Star tracker AR013x camera"""

import glob
import io
import os
import platform
import subprocess
from enum import Enum
from pathlib import Path
from threading import Timer
from time import monotonic, sleep

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
        self._mock_data = np.zeros(self._image_size, dtype=np.uint8)

        uptimer = Timer(90.0 - monotonic(), self.unlock)
        uptimer.start()

    def unlock(self):
        if self._mock:
            self._state = CameraState.RUNNING
            return

        # check if kernel module is loaded
        mod_check = subprocess.run(
            "lsmod | grep prucam", capture_output=True, shell=True, check=False, text=True
        )
        if mod_check.returncode not in [0, 1]:  # error
            self._state = CameraState.ERROR
            logger.error("Camera module not found")
            return

        if not mod_check.stdout:
            logger.info("Building & installing kernel module")
            # if kernel module is not loaded; compile and insert it
            temp_path = glob.glob("/usr/src/prucam*")
            if len(temp_path) != 1:
                self._state = CameraState.ERROR
                logger.error("Kernel module install path not found")
                return
            install_path = temp_path[0]

            base_path = os.path.basename(install_path)
            dkms_module = base_path.replace("-", "/")
            release = platform.release()
            build_path = f"/var/lib/dkms/{dkms_module}/{release}/armv7l/module/prucam.ko.xz"
            build_mod = subprocess.run(
                f"dkms build {dkms_module}",
                capture_output=True,
                shell=True,
                check=False,
            )
            ins_mod = subprocess.run(
                f"insmod {build_path}", capture_output=True, shell=True, check=False
            )
            if build_mod.returncode != 0 or ins_mod.returncode != 0:
                self._state = CameraState.ERROR
                logger.error("Error building/inserting kernel module")
                return

        sleep(0.5)
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
            img = cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)

        return img

    @property
    def state(self) -> CameraState:
        return self._state
