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
from .utils import  read_preprocess_image

logger.add(sys.stdout, level="DEBUG")

class TestSolver(unittest.TestCase):

    def setUp(self):
        '''
        Create and startup a solver.
        '''
        logger.debug("ENTRY::setUp")
        logger.debug("Creating Solver")
        config_path = '/home/debian/oresat-star-tracker-software/misc/test-data/exp1000/calibration.txt'
        median_path = '/home/debian/oresat-star-tracker-software/misc/test-data/exp1000/median_image.png'

        self._solver = Solver(config_path=config_path, median_path=median_path)
        logger.debug("Startup Solver")
        self._solver.startup()
        logger.debug("Startup Complete")
        logger.info("EXIT::setUp")


    def test_run(self):
        '''
        Test solution of images are solved to close approximate of last known solution.
        '''
        test_data_folder = '/home/debian/oresat-star-tracker-software/misc/test-data'
        exposures = ['exp1000', 'exp2500']
        paths = [ f'{test_data_folder}/exp1000/samples' ]
        duration = -1

        x_size = 1280
        y_size = 960

        expected_x_size = 1280 # 640
        expected_y_size = 960  # 480

        """


                1. [271.257311164, 74.798045847, 84.470568]
                2. [246.783421908, 26.4559966942, 131.84151]


                3.solved:RA_CENTER=226.95598348
                3.solved:DEC_CENTER=-10.929918586
                3.solved:ORIENTATION_CENTER=161.47508

                4.solved:RA_CENTER=176.127248319
                4.solved:DEC_CENTER=-1.89170292451
                4.solved:ORIENTATION_CENTER=-157.29154

                5.solved:RA_CENTER=122.156847972
                5.solved:DEC_CENTER=52.1052996922
                5.solved:ORIENTATION_CENTER=-118.22782

                6.solved:RA_CENTER=270.202436708
                6.solved:DEC_CENTER=49.3122891085
                6.solved:ORIENTATION_CENTER=112.54466

                7.solved:RA_CENTER=237.50518643
                7.solved:DEC_CENTER=1.44809534992
                7.solved:ORIENTATION_CENTER=151.45222

                8.solved:RA_CENTER=200.764441589
                8.solved:DEC_CENTER=-14.4507215149
                8.solved:ORIENTATION_CENTER=-177.89854
        """
        solutions = {
            # 1.bpm : incorrect expected [271.25, 74.781, 79.51]
            f'{test_data_folder}/exp1000/samples/1.bmp' : [ 339.28, 327.29, -141.00749 ],
            # 2.bmp : incorrect expected [246.783421908, 26.4559966942,131.84151 ]
            f'{test_data_folder}/exp1000/samples/8.bmp' : [ 35.0021, 232.023, 92.3595  ],
        }

        image_paths = [
            f'{test_data_folder}/exp1000/samples/1.bmp',
            f'{test_data_folder}/exp1000/samples/2.bmp',
            f'{test_data_folder}/exp1000/samples/3.bmp',
            f'{test_data_folder}/exp1000/samples/4.bmp',
            f'{test_data_folder}/exp1000/samples/5.bmp',
            f'{test_data_folder}/exp1000/samples/6.bmp',
            f'{test_data_folder}/exp1000/samples/7.bmp',
            f'{test_data_folder}/exp1000/samples/8.bmp'
        ]

        for image_path in image_paths:
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
