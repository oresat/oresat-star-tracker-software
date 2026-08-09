from pathlib import Path

import numpy as np
import numpy.typing as npt
from PIL import Image

from .camera import Camera, CameraError

capture_path = Path("/dev/prucam")

try:
    print("capturing")
    cam = Camera()
    cap: npt.NDArray[np.uint8] = cam._read_raw()
    img = Image.fromarray(cap)
    img.save("test.png")
except CameraError:
    print("Error reading from file")
