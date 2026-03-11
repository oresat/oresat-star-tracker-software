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

    # these files are provided by the prucam-dkms debian package

    CAPTURE_PATH = Path("/dev/prucam")
    CONTEXT_PATH = Path("/sys/devices/platform/prudev/context_settings")
    MAX_COLS = 1280
    MAX_ROWS = 960
    PIXEL_BYTES = MAX_COLS * MAX_ROWS

    def __init__(self):
        if not self.CAPTURE_PATH.exists():
            self._state = CameraState.NOT_FOUND
            logger.error("Could not find capture path")
            return

        self._state = CameraState.RUNNING
        logger.info("Camera is unlocked")

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
        with open(self.CAPTURE_PATH, 'rb') as cam:
            data = cam.read(self.PIXEL_BYTES)

        return np.frombuffer(data, np.uint8).reshape(self.MAX_ROWS, self.MAX_COLS)

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
