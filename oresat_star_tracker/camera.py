"""Star tracker AR013x camera"""

from enum import Enum
from pathlib import Path
from importlib.resources import path

from PIL import Image
import numpy as np
import numpy.typing as npt
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
        numpy.ndarray[np.uint8]
            image data in numpy array
        """

        if self._state != CameraState.RUNNING:
            raise CameraError(f"Camera error; state is {self._state}")
        logger.info("capturing image")

        raw = self._read_raw()
        return _demosaicing_CFA_Bayer_bilinear(raw)

    def _read_raw(self) -> np.ndarray:
        with open(self.cap_dev, 'rb') as cam:
            data = cam.read(self.n_pixels)

        return np.frombuffer(data, np.uint8).reshape(self.x_size, self.y_size)

    @property
    def state(self) -> CameraState:
        return self._state


class MockCamera(Camera):
    _mock_img: npt.NDArray[np.uint8]
    _bayered_mock_img: npt.NDArray[np.uint8]

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


def _demosaicing_CFA_Bayer_bilinear(CFA: npt.NDArray[np.uint8]) -> npt.NDArray[np.uint8]:
    """
    Bilinear Bayer CFA Demosaicing

    *Bayer* CFA (Color Filter Array) bilinear demosaicing.

    Parameters
    ----------
    CFA : np.ndarray[np.uint8]
        raw bayer filtered bytes

    References
    ----------
    -   :cite:`Losson2010c` : Losson, O., Macaire, L., & Yang, Y. (2010).
        Comparison of Color Demosaicing Methods. In Advances in Imaging and
        Electron Physics (Vol. 162, pp. 173-265). doi:10.1016/S1076-5670(10)62005-8
    """

    __copyright__ = "Copyright 2015 Colour Developers"
    __license__ = "BSD-3-Clause - https://opensource.org/licenses/BSD-3-Clause"

    # increase width to prevent overflow
    cfa_int = CFA.astype(np.int32)

    # pixels on the boundary lack color information from their neighbors,
    # so we crop the image when demosaicing.
    img = cfa_int[1:-1, 1:-1]
    h, w = img.shape

    # create non-copying shifted views of the interior matrix
    up = cfa_int[0:-2, 1:-1]
    down = cfa_int[2:, 1:-1]
    left = cfa_int[1:-1, 0:-2]
    right = cfa_int[1:-1, 2:]

    # diagonal views for Red/Blue cross-interpolation
    ul = cfa_int[0:-2, 0:-2]
    ur = cfa_int[0:-2, 2:]
    dl = cfa_int[2:, 0:-2]
    dr = cfa_int[2:, 2:]

    # initialize empty native channels for the cropped size
    R = np.zeros((h, w), dtype=np.int32)
    G = np.zeros((h, w), dtype=np.int32)
    B = np.zeros((h, w), dtype=np.int32)

    # mask out red, green, and blue channels from the cropped image
    B[0::2, 0::2] = img[0::2, 0::2]
    G[0::2, 1::2] = img[0::2, 1::2]
    G[1::2, 0::2] = img[1::2, 0::2]
    R[1::2, 1::2] = img[1::2, 1::2]

    # interpolate green channel (average 4 orthogonal neighbors)
    G_smooth = (up + down + left + right) // 4
    G[0::2, 0::2] = G_smooth[0::2, 0::2]  # Fill missing Green at Blue sites
    G[1::2, 1::2] = G_smooth[1::2, 1::2]  # Fill missing Green at Red sites

    # interpolate blue channel
    B[0::2, 1::2] = (left + right)[0::2, 1::2] // 2  # at G1 sites -> horizontal neighbors
    B[1::2, 0::2] = (up + down)[1::2, 0::2] // 2  # at G2 sites -> vertical neighbors
    B[1::2, 1::2] = (ul + ur + dl + dr)[1::2, 1::2] // 4  # at Red sites -> 4 diagonal neighbors

    # interpolate red channel
    R[0::2, 1::2] = (up + down)[0::2, 1::2] // 2  # At G1 sites -> vertical neighbors
    R[1::2, 0::2] = (left + right)[1::2, 0::2] // 2  # At G2 sites -> horizontal neighbors
    R[0::2, 0::2] = (ul + ur + dl + dr)[0::2, 0::2] // 4  # At Blue sites -> 4 diagonal neighbors

    # stack channels and clip to uint8
    return np.dstack(
        [
            np.clip(R, 0, 255).astype(np.uint8),
            np.clip(G, 0, 255).astype(np.uint8),
            np.clip(B, 0, 255).astype(np.uint8),
        ]
    )
