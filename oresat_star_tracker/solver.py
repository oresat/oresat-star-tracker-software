'''solver.py

by Umair Khan, from the Portland State Aerospace Society
based on OpenStarTracker from Andrew Tennenbaum at the University of Buffalo
openstartracker.org
'''
import uuid
import sys
import time
import datetime

from  datetime import datetime
from os.path import abspath, dirname

import numpy as np
import cv2

from olaf import logger

from .beast import beast


class SolverError(Exception):
    '''An erro has occur for the :py:class:`solver`'''


class Solver:
    '''Solve star trackr images'''

    def __init__(self, db_path=None, config_path=None, median_path=None):
        # Prepare constants
        self.P_MATCH_THRESH = 0.99
        self.YEAR = 1991.25
        self.MEDIAN_IMAGE = None
        self.S_DB = None
        self.SQ_RESULTS = None
        self.S_FILTERED = None
        self.C_DB = None

        self.data_dir = dirname(abspath(__file__)) + '/data'
        self.median_path = median_path if median_path else f'{self.data_dir}/median-image.png'
        self.config_path = config_path if config_path else f'{self.data_dir}/configuration.txt'
        self.db_path = db_path if db_path else f'{self.data_dir}/hipparcos.dat'
        # Load median image
        self.MEDIAN_IMAGE = cv2.imread(self.median_path)

        # Load configuration
        beast.load_config(self.config_path)

        logger.debug(f'__init__:Solver \n Median Path: {self.median_path}\n DB Path:{self.db_path}\n Config Path:{self.config_path}')


    def startup(self):
        '''Start up sequence. Loads median image, loads config file, and setups database.

        Seperate from :py:func:`__init__` as it take time to setup database.

        Raises
        -------
        SolverError
            start up failed
        '''

        data_dir = dirname(abspath(__file__)) + '/data'

        try:
            # Load median image
            self.MEDIAN_IMAGE = cv2.imread(self.median_path)

            # Load configuration
            beast.load_config(self.config_path)

            # Load star database
            self.S_DB = beast.star_db() # 0 seconds
            self.S_DB.load_catalog(self.db_path, self.YEAR) # 7 seconds

            # Filter stars
            self.SQ_RESULTS = beast.star_query(self.S_DB) # 1 sec
            self.SQ_RESULTS.kdmask_filter_catalog() # 8 seconds

            self.SQ_RESULTS.kdmask_uniform_density(beast.cvar.REQUIRED_STARS) # 23 seconds!

            self.S_FILTERED = self.SQ_RESULTS.from_kdmask()

            # Set up constellation database
            self.C_DB = beast.constellation_db(self.S_FILTERED, 2 + beast.cvar.DB_REDUNDANCY, 0) # 1 second

        except Exception as exc:
            raise SolverError(f'Startup sequence failed with {exc}')


    def _preprocess_img(self, orig_img, guid=None):
        if not guid:
            guid = str(uuid.uuid4())
        cv2.imwrite(f'/tmp/solver-original-{guid}.png', orig_img)
        # Ensure images are always processed on calibration size.
        orig_img = cv2.resize(orig_img, (beast.cvar.IMG_X, beast.cvar.IMG_Y))
        cv2.imwrite(f'/tmp/solver-resized-{guid}.png', orig_img)
        # Process the image for solving
        logger.info(f"start image pre-processing- {guid}")
        tmp = orig_img.astype(np.int16) - self.MEDIAN_IMAGE
        img = np.clip(tmp, a_min=0, a_max=255).astype(np.uint8)
        img_grey = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        cv2.imwrite(f'/tmp/solver-grey-{guid}.png', img_grey)
        return img_grey

    def _find_contours(self, img_grey, guid=None):
        if not guid: guid = str(uuid.uuid4())
        logger.info(f'entry: solve():{beast.cvar.IMG_X}, {beast.cvar.IMG_Y}')

        # Remove areas of the image that don't meet our brightness threshold and then extract
        # contours
        ret, thresh = cv2.threshold(img_grey, beast.cvar.THRESH_FACTOR * beast.cvar.IMAGE_VARIANCE,
                                    255, cv2.THRESH_BINARY)
        cv2.imwrite(f'/tmp/solver-thresh-{guid}.png', thresh)
        logger.info("finished image pre-processing")

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # contours_img = cv2.drawContours(img_grey, contours, -1, (0,255,0), 1)
        # cv2.imwrite(f'/tmp/solver-countours-{guid}.png', contours_img)
        logger.info(f"Number of  countours: {len(contours)}")

        return contours

    def _find_stars(self, img_grey, contours, guid = None):
        if not guid:
            guid = str(uuid.uuid4())
        i = 0
        star_list = []
        for c in contours:
            M = cv2.moments(c)
            #logger.info(f"found momments: {M}")
            if M['m00'] > 0:
                # this is how the x and y position are defined by cv2
                cx = M['m10'] / M['m00']
                cy = M['m01'] / M['m00']
                flux = float(cv2.getRectSubPix(img_grey, (1, 1), (cx, cy))[0, 0])

                # Add the list to star_list
                star_list.append([cx, cy,flux])

                # The center pixel is used as the approximation of the brightest pixel
                logger.info(f'Adding star {i} at cx,cy : ({cx}, {cy})')
                logger.info(f'Adding star {i} at flux: {flux}')
                logger.info(f'Adding star {i} at {cx - beast.cvar.IMG_X / 2.0}  , {cy - beast.cvar.IMG_Y / 2.0}, flux: {float(cv2.getRectSubPix(img_grey, (1, 1), (cx, cy))[0, 0])}')
                i+=1

        return np.array(star_list)


    def _foo(self):
        pass

    def solve(self, orig_img) -> (float, float, float):
        '''
        Return
        ------
        float, float, float
            dec - rotation about the y-axis,
            ra  - rotation about the z-axis,
            ori - rotation about the camera axis

        Raises
        -------
        SolverError
            start up failed
        '''
        guid = str(uuid.uuid4())
        logger.info(f'entry: solve():{beast.cvar.IMG_X}, {beast.cvar.IMG_Y}')

        cv2.imwrite(f'/tmp/solver-original-{guid}.png', orig_img)
        # Ensure images are always processed on calibration size.
        orig_img = cv2.resize(orig_img, (beast.cvar.IMG_X, beast.cvar.IMG_Y))

        cv2.imwrite(f'/tmp/solver-resized-{guid}.png', orig_img)
        # Create and initialize variables
        img_stars = beast.star_db()
        match = None
        fov_db = None

        # Process the image for solving
        logger.info(f"start image pre-processing- {guid}")
        tmp = orig_img.astype(np.int16) - self.MEDIAN_IMAGE
        img = np.clip(tmp, a_min=0, a_max=255).astype(np.uint8)
        img_grey = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        cv2.imwrite(f'/tmp/solver-grey-{guid}.png', img_grey)

        # Remove areas of the image that don't meet our
        # brightness threshold and then extract contours.
        ret, thresh = cv2.threshold(img_grey, beast.cvar.THRESH_FACTOR * beast.cvar.IMAGE_VARIANCE,
                                    255, cv2.THRESH_BINARY)

        cv2.imwrite(f'/tmp/solver-thresh-{guid}.png', thresh)
        logger.info("finished image pre-processing")

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        #cv2.imwrite(f'/tmp/solver-countours-{guid}.png', contours)

        # Process the contours
        i = 0
        for c in contours:

            M = cv2.moments(c)

            #logger.info(f"found momments: {M}")

            if M['m00'] > 0:

                # this is how the x and y position are defined by cv2
                cx = M['m10'] / M['m00']
                cy = M['m01'] / M['m00']

                # See https://alyssaq.github.io/2015/computing-the-axes-or-orientation-of-a-blob/
                # for how to convert these into eigenvectors/values
                u20 = M['m20'] / M['m00'] - cx ** 2
                u02 = M['m02'] / M['m00'] - cy ** 2
                u11 = M['m11'] / M['m00'] - cx * cy

                # The center pixel is used as the approximation of the brightest pixel
                img_stars += beast.star(cx - beast.cvar.IMG_X / 2.0,
                                        cy - beast.cvar.IMG_Y / 2.0,
                                        float(cv2.getRectSubPix(img_grey, (1, 1), (cx, cy))[0, 0]),
                                        -1)
                logger.info(f'Adding star {i} at cx,cy : ({cx}, {cy})')
                logger.info(f'Adding star {i} at flux: (float(cv2.getRectSubPix(img_grey, (1, 1), (cx, cy))[0, 0]))')
                logger.info(f'Adding star {i} at {cx - beast.cvar.IMG_X / 2.0}  , {cy - beast.cvar.IMG_Y / 2.0}, flux: {float(cv2.getRectSubPix(img_grey, (1, 1), (cx, cy))[0, 0])}')
                i+=1

        # We only want to use the brightest MAX_FALSE_STARS + REQUIRED_STARS
        logger.info(f'Copying {beast.cvar.MAX_FALSE_STARS + beast.cvar.REQUIRED_STARS} brightest')
        img_stars_n_brightest = img_stars.copy_n_brightest(
            beast.cvar.MAX_FALSE_STARS + beast.cvar.REQUIRED_STARS)

        logger.info(f"img_stars_n_brightest {img_stars_n_brightest}")

        img_const_n_brightest = beast.constellation_db(img_stars_n_brightest,
                                                       beast.cvar.MAX_FALSE_STARS + 2, 1)

        logger.info(f"img_const_n_brightest: {img_const_n_brightest}")

        lis = beast.db_match(self.C_DB, img_const_n_brightest)

        # Generate the match
        if lis.p_match > self.P_MATCH_THRESH and lis.winner.size() >= beast.cvar.REQUIRED_STARS:
            x = lis.winner.R11
            y = lis.winner.R21
            z = lis.winner.R31
            r = beast.cvar.MAXFOV / 2
            self.SQ_RESULTS.kdsearch(x, y, z, r,
                                     beast.cvar.THRESH_FACTOR * beast.cvar.IMAGE_VARIANCE)

            # Estimate density for constellation generation
            self.C_DB.results.kdsearch(x, y, z, r,
                                       beast.cvar.THRESH_FACTOR * beast.cvar.IMAGE_VARIANCE)
            fov_stars = self.SQ_RESULTS.from_kdresults()
            fov_db = beast.constellation_db(fov_stars, self.C_DB.results.r_size(), 1)
            self.C_DB.results.clear_kdresults()
            self.SQ_RESULTS.clear_kdresults()

            img_const = beast.constellation_db(img_stars, beast.cvar.MAX_FALSE_STARS + 2, 1)
            near = beast.db_match(fov_db, img_const)

            if near.p_match > self.P_MATCH_THRESH:
                match = near

        if match is not None:
            match.winner.calc_ori()
            dec = match.winner.get_dec()
            ra = match.winner.get_ra()
            ori = match.winner.get_ori()
        else:
            logger.info("Unable to find orientation for image!")
            raise SolverError('Solution failed for image')

        logger.info(f'exit: solve(): dec:{dec} ra:{ra}, ori:{ori}')

        return dec, ra, ori
