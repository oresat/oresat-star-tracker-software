"""Star tracker AR013x camera"""

from enum import Enum
from pathlib import Path
from colour_demosaicing import demosaicing_CFA_Bayer_bilinear
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
        context_path = Path("/sys/devices/platform/prucam/context_settings")
        x_size = int((context_path / "x_size").read_text())
        y_size = int((context_path / "y_size").read_text())
        self._image_size = (y_size, x_size)
        self._state = CameraState.RUNNING
        logger.info("Camera is unlocked")

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

        img = np.fromfile(self.CAPTURE_PATH, dtype=(np.uint8, self._image_size), count=1)[0]
        raw = img if img.ndim == 2 else img[..., 0]

        # normalize
        raw = raw.astype(np.float32)
        raw /= raw.max()

        # demosaic
        rgb = demosaicing_CFA_Bayer_bilinear(raw)

        # apply white balancing
        rgb[..., 0] *= 1.4  # R gain
        rgb[..., 1] *= 1.0  # G gain
        rgb[..., 2] *= 1.7  # B gain

        # clip
        rgb = np.clip(rgb, 0, 1)

        return (rgb * 255).astype(np.uint8)

    @property
    def state(self) -> CameraState:
        return self._state


class MockCamera(Camera):
    def __init__(self):
        self._mock_data = np.zeros((self.MAX_COLS, self.MAX_ROWS, 3), dtype=np.uint8)
        self._state = CameraState.RUNNING

    def capture(self, color: bool = True) -> np.ndarray:
        if self._state != CameraState.RUNNING:
            raise CameraError(f"Camera error; state is {self._state}")
        return self._mock_data
