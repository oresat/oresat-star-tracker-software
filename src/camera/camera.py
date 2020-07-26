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
    image_dir : str
        The path to the directory containing images to choose from. (Everything
        in the directory should be an OpenCV-readable image.)
    logger
        The logger to be used for all informational and error output,
        created with ``logging.getLogger()``.

    """

    # Initialization -- set up image directory and logger
    def __init__(self, image_dir, logger):
        self.image_dir = image_dir
        self.image_paths = glob.glob(self.image_dir + "*")
        self.logger = logger

    # Set the image directory
    def change_dir(self, new_dir):
        """Change the directory to pull images from.

        Parameters
        ----------
        new_dir : str
            Path to the new directory.

        """
        self.image_dir = new_dir
        self.image_paths = glob.glob(self.image_dir + "*")
        self.logger.info("Changed image directory to {}".format(new_dir))

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