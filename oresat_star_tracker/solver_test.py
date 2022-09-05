import unittest
import sys
import os
import io
import cv2
import traceback
import numpy as np
from timeit import default_timer as timer
from olaf import logger
from .solver import Solver, SolverError
from .utils import read_image_file_to_numpy_buffer, read_preprocess_image

logger.add(sys.stdout, level="DEBUG")

"""
TODO:

    1. Make the calibration parameters configurable
    2. Allow for calibration file generation using old code.
    3. Provide the solver with calibration file.
    4. Refactor the tests to follow the 5 line rule.
    5. Test the pdo generation using mock image
    6. Create a test script and recording utilities for OMSCI visit.

"""
class TestSolver(unittest.TestCase):

    def setUp(self):
        """ setUp """
        logger.debug("ENTRY::setUp")
        logger.debug("Creating Solver")
        self._solver = Solver()
        logger.debug("Startup Solver")
        self._solver.startup()
        logger.debug("Startup Complete")
        logger.info("EXIT::setUp")


    def read_image(self, image_path, color=True,
                        x_size = 1280, y_size = 960,
                        expected_x_size = 640, expected_y_size = 480):
      ''' Read the image
      '''
      imgbuf = read_image_file_to_numpy_buffer(image_path, y_size, x_size)

      # Convert to color
      if color is True:
          img = cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)

      resized_img = cv2.resize(img, (expected_x_size, expected_y_size))

      return resized_img


    def test_run(self):
        '''Test solution of images.
        '''
        test_data_folder = '/home/debian/oresat-star-tracker-software/misc/test-data'
        exposures = ['exp1000', 'exp2500']
        paths = [ f'{test_data_folder}/exp1000/samples' ]
        duration = -1

        x_size = 1280
        y_size = 960

        expected_x_size = 640
        expected_y_size = 480

        solutions = {
            f'{test_data_folder}/exp1000/samples/1.bmp' : [ 339.28, 327.29, -141.00749 ],
            f'{test_data_folder}/exp1000/samples/8.bmp' : [ 35.0021, 232.023, 92.3595  ]
        }

        for path in paths:
            N = 9 # Number of samples
            for i in range(1, N):
                image_file_name = "%d.bmp" % i
                image_path = path + '/' + image_file_name
                logger.info(f'image_path: {image_path}')
                img_data = read_preprocess_image(image_path, y_size, x_size, expected_y_size, expected_x_size)

                solution = None
                if image_path in solutions:
                    logger.info(f'Found known solutions {solutions[image_path]}')
                    solution = solutions[image_path]
                try:
                    start = timer()
                    # Run the solver
                    if not solution:
                        self.assertRaises(SolverError, self._solver.solve, img_data)
                        logger.info(f'Unsuccessful solution {image_path}')
                    else:
                        ra, dec, ori = self._solver.solve(img_data)
                        if solution:
                            expected_ra, expected_dec, expected_ori = solution
                            self.assertTrue(np.isclose(ra, expected_ra), "ra is not close")
                            self.assertTrue(np.isclose(dec,expected_dec), "dec is not close")
                            self.assertTrue(np.isclose(ori, expected_ori), "ori is not close")
                            logger.info(f'Successful solution {image_path}')

                    stop = timer()
                    duration = stop - start
                    logger.info(f'Solve time[seconds]: {duration}')
                except:
                    traceback.print_exc()
                    logger.info("Failed to solve %s" % image_path)
                self.assertTrue(duration < 10)

if __name__ == """__main__""":
    unittest.main()
