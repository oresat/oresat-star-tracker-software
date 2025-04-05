import glob
import io
import logging
import os
import platform
import subprocess
from enum import Enum
from threading import Timer
from time import monotonic, sleep

import cv2
import numpy as np


class Ar013xState(Enum):
    STANDBY = 1
    RUNNING = 2
    LOCKOUT = 3
    NOT_FOUND = 4
    ERROR = 5


class Ar013xError(Exception):
    """An error has occured with Ar013x"""


class Ar013x:
    # these files are provided by the prucam-dkms debian package

    CAPTURE_PATH = "/dev/prucam"
    MAX_COLS = 1280
    MAX_ROWS = 960
    PIXEL_BYTES = MAX_COLS * MAX_ROWS

    def __init__(self, mock: bool = False):
        self._mock = mock
        self._state = Ar013xState.LOCKOUT
        self._image_size = (self.MAX_COLS, self.MAX_ROWS)
        self._mock_data = np.zeros((self.MAX_COLS, self.MAX_ROWS, 3), dtype=np.uint8)

        if self._mock:
            logging.warning("mocking AR013X camera")

        uptimer = Timer(90.0 - monotonic(), self.unlock)
        uptimer.start()

    def unlock(self):
        if self._mock:
            self._state = Ar013xState.RUNNING
            return

        # check if kernel module is loaded
        mod_check = subprocess.run(
            "lsmod | grep prucam", capture_output=True, shell=True, check=False, text=True
        )
        if mod_check.returncode not in [0, 1]:  # error
            self._state = Ar013xState.ERROR
            logging.error("Ar013x module not found")
            return

        def load_kernel_module():
            logging.info("Building & installing kernel module")
            # if kernel module is not loaded; compile and insert it
            temp_path = glob.glob("/usr/src/prucam*")
            if len(temp_path) != 1:
                self._state = Ar013xState.ERROR
                logging.error("Kernel module install path not found")
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
                self._state = Ar013xState.ERROR
                logging.error("Error building/inserting kernel module")
                return

        if not mod_check.stdout:
            load_kernel_module()
            sleep(5)
            rm_mod = subprocess.run("rmmod prucam", capture_output=True, shell=True, check=False)
            if rm_mod.returncode != 0:
                self._state = Ar013xState.ERROR
                logging.error("Error removing kernel module")
                return
            load_kernel_module()

        sleep(0.5)
        if os.path.exists(self.CAPTURE_PATH):
            self._state = Ar013xState.NOT_FOUND
            logging.error("Could not find capture path")
            return

        # no errors; attempt to read image
        self._state = Ar013xState.RUNNING
        self._image_size = self.read_image_size()
        logging.info("Ar013x is unlocked")

    def read_image_size(self) -> tuple[int]:
        if self._state != Ar013xState.RUNNING:
            raise Ar013xError(f"Ar013x error; state is {self._state}")
        if self._mock:
            return self._image_size
        x_size = self.read_context_setting("x_size")
        y_size = self.read_context_setting("y_size")
        return (y_size, x_size)

    def read_context_setting(self, name: str) -> int:
        if self._state != Ar013xState.RUNNING:
            raise Ar013xError(f"Ar013x error; state is {self._state}")
        context_path = "/sys/devices/platform/prucam/context_settings"
        with open(f"{context_path}/{name}", "r") as f:
            value = int(f.read())
            return value
        # path check

    def capture(self, color: bool = True) -> np.ndarray:
        if self._state != Ar013xState.RUNNING:
            raise Ar013xError(f"Ar013x error; state is {self._state}")

        if self._mock:
            return self._mock_data
        # Read raw data
        fd = os.open(self.CAPTURE_PATH, os.O_RDWR)
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
    def state(self) -> Ar013xState:
        return self._state
