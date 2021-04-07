# snapper.py
# by Umair Khan, from the Portland State Aerospace Society

# Use this class to control the camera.

# Imports
from prucam import Camera, PRU

# Class definition
class Snapper:

    # Initialization -- set up logger
    def __init__(self, logger):
        self.logger = logger
        self.image_dir = None
        self.image_paths = None

    # Set the image directory
    def set_dir(self, dirpath):
        self.image_dir = dirpath
        self.image_paths = glob.glob(self.image_dir + "*")
        self.logger.info("Set image directory to {}".format(dirpath))

    # Capture an image (random choice from directory)
    def capture(self):
        path = random.choice(self.image_paths)
        self.logger.info("Grabbing image from {}".format(path))
        return path, cv2.imread(path)