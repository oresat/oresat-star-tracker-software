import unittest
from time import time
from os.path import dirname, abspath

import cv2
import numpy as np
from olaf import scet_int_from_time, logger
from oresat_star_tracker.solver import Solver


class TestContours(unittest.TestCase):
    def setUp(self):
        '''
        Create and startup a solver.
        '''

        logger.remove()  # remove logging to not mess with unittest output

        self.test_data_folder = dirname(abspath(__file__)) + "/../misc/test-data"

        self.config_path = f'{self.test_data_folder}/exp1000/calibration.txt'
        self.median_path = f'{self.test_data_folder}/exp1000/median_image.png'

    def assert_is_valid_solution(self, solution, expected_solution):
        dec, ra, ori = solution
        expected_dec, expected_ra, expected_ori = expected_solution

        expected_dec = expected_dec + 360 if expected_dec < 0 else expected_dec
        expected_ra = expected_ra + 360 if expected_ra < 0 else expected_ra
        expected_ori = expected_ori + 360 if expected_ori < 0 else expected_ori

        dec = dec + 360 if dec < 0 else dec
        ra = ra + 360 if ra < 0 else ra
        ori = ori + 360 if ori < 0 else ori

        self.assertTrue(
            np.isclose(ra, expected_ra, rtol=1e-01, atol=1e-01),
            f'ra: {ra} expected: {expected_ra} is not close',
        )
        self.assertTrue(
            np.isclose(dec, expected_dec, rtol=1e-01, atol=1e-01),
            f'dec {dec} expected:{expected_dec} is not close',
        )
        self.assertTrue(
            np.isclose(ori, expected_ori, rtol=1e-01, atol=1e-01),
            f'ori {ori} expected:{expected_ori} is not close',
        )

    def _test_find_matches(self):
        '''

        find_matches:
        '''
        trace_id = scet_int_from_time(time())  # Record the timestamp

        solver = Solver(
            config_path=self.config_path, median_path=self.median_path, blur_kernel_size=5
        )

        expected_solutions = [
            [74.798045847, 271.257311164, 84.470568],
            [26.4559966942, 246.783421908, 131.84151],
            [-10.929918586, 226.95598348, 161.47508],
            [-1.89170292451, 176.127248319, -157.29154],
            [52.1052996922, 122.156847972, -118.22782],
            [49.3122891085, 270.202436708, 112.54466],
            [1.44809534992, 237.50518643, 151.45222],
            [-14.4507215149, 200.764441589, -177.89854],
        ]

        image_paths = [
            f'{self.test_data_folder}/exp1000/samples/1.bmp',
            f'{self.test_data_folder}/exp1000/samples/2.bmp',
            f'{self.test_data_folder}/exp1000/samples/3.bmp',
            f'{self.test_data_folder}/exp1000/samples/4.bmp',
            f'{self.test_data_folder}/exp1000/samples/5.bmp',
            f'{self.test_data_folder}/exp1000/samples/6.bmp',
            f'{self.test_data_folder}/exp1000/samples/7.bmp',
            f'{self.test_data_folder}/exp1000/samples/8.bmp',
        ]

        # initialized the db
        solver.startup()

        for idx, image_path in enumerate(image_paths):
            img_data = cv2.imread(image_path)

            img_grey = solver._preprocess_img(img_data)

            # find the countours
            contours = solver._find_contours(img_grey, trace_id=trace_id)

            # Create star list.
            star_list = solver._find_stars(img_grey, contours)

            # Find constellation
            solution = solver._solve_orientation(star_list)

            # esnure it is within expected solutions
            self.assert_is_valid_solution(solution, expected_solutions[idx])

    def test_find_stars(self):
        """
        Find and mark the stars with a circle. Not all stars are marked.
        """
        trace_id = scet_int_from_time(time())  # Record the timestamp

        solver = Solver(
            config_path=self.config_path,
            median_path=self.median_path,
            trace_intermediate_images=False,
        )

        image_paths = [
            f'{self.test_data_folder}/exp1000/samples/1.bmp',
            f'{self.test_data_folder}/exp1000/samples/2.bmp',
            f'{self.test_data_folder}/exp1000/samples/3.bmp',
            f'{self.test_data_folder}/exp1000/samples/4.bmp',
            f'{self.test_data_folder}/exp1000/samples/5.bmp',
            f'{self.test_data_folder}/exp1000/samples/6.bmp',
            f'{self.test_data_folder}/exp1000/samples/7.bmp',
            f'{self.test_data_folder}/exp1000/samples/8.bmp',
        ]

        expected_star_counts = [41, 36, 34, 44, 77, 46, 44, 48]

        for idx, image_path in enumerate(image_paths):
            img_data = cv2.imread(image_path)
            img_grey = solver._preprocess_img(img_data)
            img_height, img_width = img_grey.shape
            contours = solver._find_contours(img_grey, trace_id=trace_id)

            star_list = solver._find_stars(img_grey, contours)
            num_stars = star_list.shape[0]
            self.assertEqual(num_stars, expected_star_counts[idx])

            for idx in range(star_list.shape[0]):
                star = star_list[idx]
                cx, cy, _ = int(star[0]), int(star[1]), int(star[2])
                self.assertTrue(0 <= cx < img_width)
                self.assertTrue(0 <= cy < img_height)

    def test_find_contours(self):
        '''
        Given a starfiled test that the number of countours
        for the image match the number of stars in the image.
        '''
        solver = Solver(config_path=self.config_path, median_path=self.median_path)

        image_paths = [
            f'{self.test_data_folder}/exp1000/samples/1.bmp',
            f'{self.test_data_folder}/exp1000/samples/2.bmp',
            f'{self.test_data_folder}/exp1000/samples/3.bmp',
            f'{self.test_data_folder}/exp1000/samples/4.bmp',
            f'{self.test_data_folder}/exp1000/samples/5.bmp',
            f'{self.test_data_folder}/exp1000/samples/6.bmp',
            f'{self.test_data_folder}/exp1000/samples/7.bmp',
            f'{self.test_data_folder}/exp1000/samples/8.bmp',
        ]

        expected_contours = [188, 220, 321, 249, 1243, 523, 758, 731]

        for idx, image_path in enumerate(image_paths):
            trace_id = scet_int_from_time(time())  # Record the timestamp
            expected_num_contours = expected_contours[idx]
            img_data = cv2.imread(image_path)
            img_grey = solver._preprocess_img(img_data, trace_id=trace_id)
            contours = solver._find_contours(img_grey, trace_id=trace_id)
            self.assertEqual(expected_num_contours, len(contours))
