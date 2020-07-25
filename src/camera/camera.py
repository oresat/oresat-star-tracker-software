# camera.py
# by Umair Khan, from the Portland State Aerospace Society

# Use this class to control the camera.

# Imports
import glob
import random

# Class definition
class Camera:

    # Initialization -- set up image directory and logger
    def __init__(self, image_dir, logger):
        self.image_dir = image_dir
        self.image_paths = glob.glob(self.image_dir + "*")
        self.logger = logger

    # Set the image directory
    def change_dir(self, new_dir):
        self.image_dir = new_dir
        self.image_paths = glob.glob(self.image_dir + "*")
        self.logger.info("Changed image directory to {}".format(new_dir))

    # Capture an image (random choice from directory)
    def capture(self):
        path = random.choice(self.image_paths)
        self.logger.info("Grabbing image from {}".format(path))
        return path, cv2.imread(path)