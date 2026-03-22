"""Star tracker AR013x camera"""

from enum import Enum
from pathlib import Path
from colour_demosaicing import demosaicing_CFA_Bayer_Malvar2004
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

    cap_dev = Path("/dev/prucam")

    # defaults to the resolution of the AR013x image sensor
    x_size = 1280
    y_size = 960

    # assumes one pixel corresponds to one byte
    n_pixels = x_size * y_size

    def __init__(self):
        if not self.cap_dev.exists():
            self._state = CameraState.NOT_FOUND
            logger.error("Could not find capture device")
            return

        self._state = CameraState.RUNNING
        logger.info("Camera is unlocked")

        # read camera paramaters from sysfs
        dev_ctx = Path("/sys/devices/platform/prudev/context_settings")
        self.x_size = int((dev_ctx / "x_size").read_text())
        self.y_size = int((dev_ctx / "y_size").read_text())
        self.n_pixels = self.x_size * self.y_size

        logger.debug(f"Camera resolution is {self.x_size}x{self.y_size}")

    def capture(self) -> np.ndarray:
        """Capture an image

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
        logger.info("capturing image")

        raw = self._read_raw()
        rgb = self._demosaic(raw)

        return np.clip(rgb * 255, 0, 255).astype(np.uint8)

    def _read_raw(self) -> np.ndarray:
        with open(self.cap_dev, 'rb') as cam:
            data = cam.read(self.n_pixels)

        return np.frombuffer(data, np.uint8).reshape(self.x_size, self.y_size)

    def _demosaic(self, raw: np.ndarray) -> np.ndarray:
        raw = raw.astype(np.float32) / 255
        return demosaicing_CFA_Bayer_Malvar2004(raw)

    @property
    def state(self) -> CameraState:
        return self._state


class MockCamera(Camera):
    def __init__(self):
        self._mock_data = np.zeros((self.MAX_COLS, self.MAX_ROWS, 3), dtype=np.uint8)
        self._state = CameraState.RUNNING

    def capture(self) -> np.ndarray:
        if self._state != CameraState.RUNNING:
            raise CameraError(f"Camera error; state is {self._state}")
        return self._mock_data
