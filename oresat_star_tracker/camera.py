"""Star tracker AR013x camera"""

from enum import Enum
from pathlib import Path
from importlib.resources import path

from PIL import Image
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
    MAX_COLS = 1280
    MAX_ROWS = 960
    PIXEL_BYTES = MAX_COLS * MAX_ROWS

    def __init__(self):
        if not self.CAPTURE_PATH.exists():
            self._image_size = (self.MAX_COLS, self.MAX_ROWS)
            self._state = CameraState.NOT_FOUND
            logger.error("Could not find capture path")
            return

        # no errors; attempt to read image
        context_path = Path("/sys/devices/platform/prudev/context_settings")
        x_size = int((context_path / "x_size").read_text())
        y_size = int((context_path / "y_size").read_text())
        self._image_size = (y_size, x_size)
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

        raw = np.fromfile(self.CAPTURE_PATH, dtype=(np.uint8, self._image_size), count=1)[0]

        # normalize, demosaicing expects float
        raw = raw.astype(np.float32) / 255

        # demosaicing, reconstruct full color
        # image from samples overlaid with a bayer filter
        rgb = demosaicing_CFA_Bayer_Malvar2004(raw)

        return np.clip(rgb * 255, 0, 255).astype(np.uint8)

    @property
    def state(self) -> CameraState:
        return self._state


class MockCamera(Camera):
    _mock_img: np.ndarray
    _bayered_mock_img: np.ndarray

    def __init__(self):

        with path("oresat_star_tracker.data", "mock_img.png") as mock_img:
            self._mock_img = np.array(Image.open(mock_img))

        with path("oresat_star_tracker.data", "bayered_mock_img.png") as bayered_mock_img:
            self._bayered_mock_img = np.array(Image.open(bayered_mock_img))

        self._state = CameraState.RUNNING

    def capture(self) -> np.ndarray:
        if self._state != CameraState.RUNNING:
            raise CameraError(f"Camera error; state is {self._state}")
        return self._mock_img
