# camera.py
# by Umair Khan, from the Portland State Aerospace Society

# Use this class to control the camera.

"""
camera.py
==============
The core of the camera module, located in src/camera.
"""

# Imports
import glob
import random

# Class definition
class Camera:
    """This class contains all camera functionality.

    At the moment, the "camera" simply chooses a random image from a provided
    directory to simulate capturing a real image.

    Parameters
    ----------
    logger
        The logger to be used for all informational and error output,
        created with ``logging.getLogger()``.

    """

    # Initialization -- set up logger
    def __init__(self, logger):
        self.logger = logger
        self.image_dir = None
        self.image_paths = None

    # Set the image directory
    def set_dir(self, dirpath):
        """Set the directory to pull images from.

        Parameters
        ----------
        dirpath : str
            The path to the directory containing images to choose from. (Everything
            in the directory should be an OpenCV-readable image.)

        """
        self.image_dir = dirpath
        self.image_paths = glob.glob(self.image_dir + "*")
        self.logger.info("Set image directory to {}".format(dirpath))

    # Capture an image (random choice from directory)
    def capture(self):
        """Grab an image from the directory.

        Returns
        -------
        OpenCV image array
            A random image from the currently-chosen directory.

        """
        path = random.choice(self.image_paths)
        self.logger.info("Grabbing image from {}".format(path))
        return path, cv2.imread(path)