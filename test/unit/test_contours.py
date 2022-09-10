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

from .utils import  read_preprocess_image

class TestContours(unittest.TestCase):
    def setUp(self):
        '''
        Create and startup a solver.
        '''

        self.test_data_folder = '/home/debian/oresat-star-tracker-software/misc/test-data'

        config_path = f'{self.test_data_folder}/exp1000/calibration.txt'
        median_path = f'{self.test_data_folder}/exp1000/median_image.png'

        self._solver = Solver(config_path=config_path, median_path=median_path)


    def test_find_stars(self):
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
            # overlay countours on original image.
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

    def test_find_contours(self):
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






