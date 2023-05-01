import unittest
from time import time
from os.path import dirname, abspath

import cv2
import numpy as np
from olaf import logger
from oresat_star_tracker.solver import Solver, SolverError


class TestSolver(unittest.TestCase):

    def setUp(self):
        '''
        Create and startup a solver.
        '''
        logger.remove()  # remove logging to not mess with unittest output

        self.test_data_folder = dirname(abspath(__file__)) + "/../misc/test-data"

    def assert_image_matches_solution(self, image_path, solution, expect_to_fail=False):
        img_data = cv2.imread(image_path)

        if (not solution) or expect_to_fail:
            self.assertRaises(SolverError, self._solver.solve, img_data)
            return None, None, None
        else:
            # Run the solver
            dec, ra, ori = self._solver.solve(img_data)
            # print(f'dec: {dec}, ra:{ra}, ori:{ori}')
            if solution:
                expected_dec, expected_ra, expected_ori = solution

                expected_dec = expected_dec + 360 if expected_dec < 0 else expected_dec
                expected_ra = expected_ra + 360 if expected_ra < 0 else expected_ra
                expected_ori = expected_ori + 360 if expected_ori < 0 else expected_ori

                dec = dec + 360 if dec < 0 else dec
                ra = ra + 360 if ra < 0 else ra
                ori = ori + 360 if ori < 0 else ori

                self.assertTrue(np.isclose(ra, expected_ra, rtol=1e-01, atol=1e-01),
                                f'ra: {ra} expected: {expected_ra} is not close')
                self.assertTrue(np.isclose(dec, expected_dec, rtol=1e-01, atol=1e-01),
                                f'dec {dec} expected:{expected_dec} is not close')
                self.assertTrue(np.isclose(ori, expected_ori, rtol=1e-01, atol=1e-01),
                                f'ori {ori} expected:{expected_ori} is not close')

            return dec, ra, ori

    def test_exp1000(self):
        '''
        Test solution of images are solved to close approximate of last known solution.
        '''
        config_path = f'{self.test_data_folder}/exp1000/calibration.txt'
        median_path = f'{self.test_data_folder}/exp1000/median_image.png'

        self._solver = Solver(config_path=config_path, median_path=median_path, blur_kernel_size=5)
        self._solver.startup()

        # TODO: Find root cause as to why the expected solutions are not being
        #       produced by solver.
        #
        # dec, ra, ori
        expected_solutions = [
            [74.798045847, 271.257311164, 84.470568],
            [26.4559966942, 246.783421908, 131.84151],
            [-10.929918586, 226.95598348, 161.47508],
            [-1.89170292451, 176.127248319, -157.29154],
            [52.1052996922, 122.156847972, -118.22782],
            [49.3122891085, 270.202436708, 112.54466],
            [1.44809534992, 237.50518643, 151.45222],
            [-14.4507215149, 200.764441589, -177.89854]]

        image_paths = [
            f'{self.test_data_folder}/exp1000/samples/1.bmp',
            f'{self.test_data_folder}/exp1000/samples/2.bmp',
            f'{self.test_data_folder}/exp1000/samples/3.bmp',
            f'{self.test_data_folder}/exp1000/samples/4.bmp',
            f'{self.test_data_folder}/exp1000/samples/5.bmp',
            f'{self.test_data_folder}/exp1000/samples/6.bmp',
            f'{self.test_data_folder}/exp1000/samples/7.bmp',
            f'{self.test_data_folder}/exp1000/samples/8.bmp'
        ]

        failing_indexes = []

        duration = -1
        for idx, image_path in enumerate(image_paths):
            solution = expected_solutions[idx]
            expect_to_fail = idx in failing_indexes
            start = time()
            # Run the solver
            self.assert_image_matches_solution(image_path, solution, expect_to_fail)
            stop = time()
            duration = stop - start
            self.assertTrue(duration < 10)

    def test_run_2500(self):
        '''
        Test solution of images are solved to close approximate of last known solution.
        '''
        config_path = f'{self.test_data_folder}/exp2500/calibration.txt'
        median_path = f'{self.test_data_folder}/exp2500/median_image.png'

        self._solver = Solver(config_path=config_path,
                              median_path=median_path, blur_kernel_size=10)
        self._solver.startup()

        # dec, ra, ori
        expected_solutions = [
            [72.8920685767, 262.419524915, -102.963],
            [44.7749205456, 247.450049403, -69.678617],
            [17.8821827493, 238.612030831, -35.154497],
            [32.8398399237, 166.294216383, 53.720769],
            [-7.28448172686, 202.785409144, 2.7043533],
            [6.68097353669, 225.179744445, -18.913663],
            [13.5862063459, 223.278502629, -19.569697]]

        image_paths = [
            f'{self.test_data_folder}/exp2500/samples/1.bmp',
            f'{self.test_data_folder}/exp2500/samples/2.bmp',
            f'{self.test_data_folder}/exp2500/samples/3.bmp',
            f'{self.test_data_folder}/exp2500/samples/4.bmp',
            f'{self.test_data_folder}/exp2500/samples/5.bmp',
            f'{self.test_data_folder}/exp2500/samples/6.bmp',
            f'{self.test_data_folder}/exp2500/samples/7.bmp',
        ]

        failing_indexes = []
        duration = -1
        for idx, image_path in enumerate(image_paths):
            solution = expected_solutions[idx]
            expect_to_fail = idx in failing_indexes
            # Run the solver
            start = time()
            self.assert_image_matches_solution(image_path, solution, expect_to_fail)
            stop = time()
            duration = stop - start
            self.assertTrue(duration < 10)
