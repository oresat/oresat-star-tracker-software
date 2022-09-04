import unittest
import sys
import os
import io
import cv2
import numpy as np
from timeit import default_timer as timer
from olaf import logger
from .solver import Solver, SolverError

from .utils import read_file_to_buffer
from .utils import read_image_file_to_numpy_buffer, read_preprocess_image
import tempfile

logger.add(sys.stdout, level="DEBUG")


class TestUtils(unittest.TestCase):

    def test_read_file_to_buffer(self):
        test_file = tempfile.NamedTemporaryFile(mode="w",suffix=".txt",prefix="utils_test", delete=False)
        name = test_file.name

        for i in range(4096):
            test_file.write("test")
        test_file.close()

        bytes_to_read = 4
        buf = read_file_to_buffer(test_file.name, bytes_to_read)

        given = 'Given a file and a buffer size, '
        self.assertEqual(bytes_to_read, len(buf), f'{given}, we read the correct number of bytes from the file.')
        self.assertEqual('test', str(buf.decode()), f'{given}, we read the correct content from the file.')

        # Remove the test file
        os.remove(test_file.name)


    def test_read_preprocess_image(self):
        x_size = 1280
        y_size = 960

        expected_x_size = 640
        expected_y_size = 480

        image = read_preprocess_image('./oresat_star_tracker/data/mock.bmp', y_size, x_size)
        self.assertEqual((y_size, x_size, 3), image.shape)

if __name__ == """__main__""":
    unittest.main()
