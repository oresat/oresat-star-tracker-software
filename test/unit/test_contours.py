import unittest
import sys
import os
import io
import traceback
import uuid

import cv2
import numpy as np
from timeit import default_timer as timer

from oresat_star_tracker.solver import Solver, SolverError

class TestContours(unittest.TestCase):

    def setUp(self):
        '''
        Create and startup a solver.
        '''
        self.test_data_folder = '/home/debian/oresat-star-tracker-software/misc/test-data'

        config_path = f'{self.test_data_folder}/exp1000/calibration.txt'
        median_path = f'{self.test_data_folder}/exp1000/median_image.png'

        self._solver = Solver(config_path=config_path, median_path=median_path, blur_kernel_size=5)


    def assert_is_valid_solution(self, solution, expected_solution):
        dec, ra, ori = solution
        expected_dec, expected_ra, expected_ori = expected_solution

        expected_dec = expected_dec + 360 if expected_dec < 0 else expected_dec
        expected_ra  = expected_ra  + 360 if expected_ra  < 0 else expected_ra
        expected_ori = expected_ori + 360 if expected_ori < 0 else expected_ori

        dec = dec + 360 if dec < 0 else dec
        ra =  ra  + 360 if ra < 0  else ra
        ori = ori + 360 if ori < 0 else ori

        self.assertTrue(np.isclose(ra,  expected_ra,  rtol=1e-01, atol=1e-01), f'ra: {ra} expected: {expected_ra} is not close')
        self.assertTrue(np.isclose(dec, expected_dec, rtol=1e-01, atol=1e-01), f'dec {dec} expected:{expected_dec} is not close')
        self.assertTrue(np.isclose(ori, expected_ori, rtol=1e-01, atol=1e-01), f'ori {ori} expected:{expected_ori} is not close')


    def test_find_matches(self):
        '''

        find_matches:
        '''
        guid = str(uuid.uuid4())

        expected_solutions = [
            [ 74.798045847, 271.257311164, 84.470568   ],
            [ 26.4559966942, 246.783421908, 131.84151  ],
            [ -10.929918586, 226.95598348, 161.47508   ],
            [ -1.89170292451, 176.127248319, -157.29154],
            [ 52.1052996922, 122.156847972, -118.22782 ],
            [ 49.3122891085, 270.202436708, 112.54466  ],
            [ 1.44809534992, 237.50518643, 151.45222   ],
            [ -14.4507215149, 200.764441589, -177.89854]]


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


        # initialized the db
        self._solver.startup()

        for idx, image_path in enumerate(image_paths):
            img_data = cv2.imread(image_path)

            img_grey  = self._solver._preprocess_img(img_data)

            # find the countours
            contours = self._solver._find_contours(img_grey, guid=guid)

            # Overlay countours on original image.  # find countours of the image.
            contours_img = cv2.drawContours(img_data, contours, -1, (0,255,0), 1)
            cv2.imwrite(f'/tmp/solver-countours-{guid}.png', contours_img)

            # Create star list.
            star_list = self._solver._find_stars(img_grey, contours, guid)

            # Find constellation
            solution  = self._solver._find_constellation_matches(star_list)

            # esnure it is withing expected solutions
            self.assert_is_valid_solution(solution, expected_solutions[idx])

    def _test_find_stars(self):
        """
        Find and mark the stars with a circle. Not all stars are marked.
        """
        guid = str(uuid.uuid4())

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

        expected_star_counts = [
            41, 36, 34, 44, 77, 46, 44, 48
        ]

        for idx, image_path in enumerate(image_paths):
            img_data = cv2.imread(image_path)
            img_grey  = self._solver._preprocess_img(img_data)
            contours = self._solver._find_contours(img_grey, guid=guid)

            # Overlay countours on original image.
            contours_img = cv2.drawContours(img_data, contours, -1, (0,255,0), 1)
            cv2.imwrite(f'/tmp/solver-countours-{guid}.png', contours_img)

            star_list = self._solver._find_stars(img_grey, contours, guid)
            num_stars = star_list.shape[0]
            star_image = img_data
            self.assertEqual(num_stars, expected_star_counts[idx])

            for idx in range(star_list.shape[0]):
                star = star_list[idx]
                cx, cy, flux = int(star[0]), int(star[1]), int(star[2])
                star_image = cv2.circle(star_image, (cx, cy), radius=int(flux/10), color=(0, 0, 255), thickness=1)
            cv2.imwrite(f'/tmp/solver-stars-{guid}.png', star_image)

    def _test_find_contours(self):
        '''
        Given a starfiled test that the number of countours
        for the image match the number of stars in the image.
        '''
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

        expected_contours = [
            188, 220, 321, 249, 1243, 523, 758, 731
        ]

        for idx, image_path in enumerate(image_paths):
            guid = str(uuid.uuid4())
            expected_num_contours = expected_contours[idx]
            img_data = cv2.imread(image_path)
            img_grey  = self._solver._preprocess_img(img_data, guid =guid)
            contours = self._solver._find_contours(img_grey, guid=guid)
            self.assertEqual(expected_num_contours, len(contours))

