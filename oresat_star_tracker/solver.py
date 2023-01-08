'''solver.py

by Umair Khan, from the Portland State Aerospace Society
based on OpenStarTracker from Andrew Tennenbaum at the University of Buffalo
openstartracker.org
'''
import time

from typing import Tuple
from os.path import abspath, dirname

import numpy as np
import cv2

from olaf import logger, scet_int_from_time

from .beast import beast


class SolverError(Exception):
    '''An error has occur for the :py:class:`solver`'''


class Solver:
    '''Solve star trackr images'''

    def __init__(self,
                 db_path=None,
                 config_path=None,
                 median_path=None,
                 blur_kernel_size=None,
                 trace_intermediate_images=False):

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

        # Enable blur kernel
        self.blur_kernel_size = blur_kernel_size if blur_kernel_size else None

        # Enable tracing intermediate processing steps for debugging.
        self.trace_intermediate_images = \
            trace_intermediate_images if trace_intermediate_images else None

        logger.debug(f'Median Path: {self.median_path}')
        logger.debug(f'DB Path:{self.db_path}')
        logger.debug(f'Config Path:{self.config_path}')

    def startup(self):
        '''Start up sequence. Loads median image, loads config file, and setups database.

        Seperate from :py:func:`__init__` as it take time to setup database.

        Raises
        -------
        SolverError
            start up failed
        '''
        try:
            # Load star database
            self.S_DB = beast.star_db()  # 0 seconds
            self.S_DB.load_catalog(self.db_path, self.YEAR)  # 7 seconds

            # Filter stars
            self.SQ_RESULTS = beast.star_query(self.S_DB)  # 1 sec
            self.SQ_RESULTS.kdmask_filter_catalog()  # 8 seconds

            self.SQ_RESULTS.kdmask_uniform_density(beast.cvar.REQUIRED_STARS)  # 23 seconds!

            self.S_FILTERED = self.SQ_RESULTS.from_kdmask()

            # Set up constellation database
            self.C_DB = beast.constellation_db(
                self.S_FILTERED, 2 + beast.cvar.DB_REDUNDANCY, 0)  # 1 second

        except Exception as exc:
            raise SolverError(f'Startup sequence failed with {exc}')

    def _preprocess_img(self, orig_img, trace_id=None):
        '''
        Preprocess an input image, resize it to expected size, blur it if required,
        subtract a calibrated median image, finally convert it to
        a grey scale image of expected dimensions.

        Return
        ------
        Grey scale image of dimensions IMG_X x IMG_Y
        '''

        if self.trace_intermediate_images:
            cv2.imwrite(f'/tmp/solver-original-{trace_id}.png', orig_img)

        # Ensure images are always processed on calibration size.
        orig_img = cv2.resize(orig_img, (beast.cvar.IMG_X, beast.cvar.IMG_Y))

        if self.trace_intermediate_images:
            cv2.imwrite(f'/tmp/solver-resized-{trace_id}.png', orig_img)

        # Blur the image if a blur is specified.
        if self.blur_kernel_size:
            orig_img = cv2.blur(orig_img, (self.blur_kernel_size, self.blur_kernel_size))
            if self.trace_intermediate_images:
                cv2.imwrite(f'/tmp/solver-blurred-{trace_id}.png', orig_img)

        # Process the image for solving
        logger.info(f"start image pre-processing-{trace_id}")
        tmp = orig_img.astype(np.int16) - self.MEDIAN_IMAGE
        img = np.clip(tmp, a_min=0, a_max=255).astype(np.uint8)
        img_grey = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

        if self.trace_intermediate_images:
            cv2.imwrite(f'/tmp/solver-grey-{trace_id}.png', img_grey)

        return img_grey

    def _find_contours(self, img_grey, trace_id=None):
        '''
        Find the contors of the possible stars in the thresholded binary image. The
        thresholding limit depends on configured IMAGE_VARIANCE and THRESH_FACTOR.

        Return
        ------
        List of contours for points which could be stars and meet our brightness threshold.
        '''
        logger.info(f'entry: solve():{beast.cvar.IMG_X}, {beast.cvar.IMG_Y}')

        # Remove areas of the image that don't meet our brightness threshold and then extract
        # contours
        ret, thresh = cv2.threshold(img_grey, beast.cvar.THRESH_FACTOR * beast.cvar.IMAGE_VARIANCE,
                                    255, cv2.THRESH_BINARY)

        if self.trace_intermediate_images:
            cv2.imwrite(f'/tmp/solver-thresh-{trace_id}.png', thresh)
        logger.info("finished image pre-processing")

        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if self.trace_intermediate_images:
            contours_img = cv2.drawContours(img_grey, contours, -1, (0, 255, 0), 1)
            cv2.imwrite(f'/tmp/solver-contours-{trace_id}.png', contours_img)

        logger.info(f"Number of  contours: {len(contours)}")
        return contours

    def _find_stars(self, img_grey, contours):
        '''
        Convert the contour list into an array of stars with corresponding
        x,y positions of the stars and flux value for brightness of the star
        from the grey scale image generated.

        Return
        ------
        np.array of shape (num_stars, 3) : [x, y, flux]
            x - position of the star in image coordinates.
            y - position of the star in image coordinates.
            flux - luminosity of the star as it appears in grey scale image.
        '''
        star_list = []
        for c in contours:
            M = cv2.moments(c)
            if M['m00'] > 0:
                # this is how the x and y position are defined by cv2
                cx = M['m10'] / M['m00']
                cy = M['m01'] / M['m00']
                flux = float(cv2.getRectSubPix(img_grey, (1, 1), (cx, cy))[0, 0])

                # Add the list to star_list
                star_list.append([cx, cy, flux])
        return np.array(star_list)

    def _star_list_to_beast_stars_db(self, star_list):
        '''
        Convert list of stars to beast internal representation of stars. Star image
        coordinates are translated to be relative to the center pixel of the image.

        Return
        ------
        Returns beast star list.
        '''
        img_stars = beast.star_db()
        image_center = (beast.cvar.IMG_X / 2.0, beast.cvar.IMG_Y / 2.0)
        number_of_stars = star_list.shape[0]

        for idx in range(number_of_stars):
            cx, cy, flux = star_list[idx]
            cx_center, cy_center = image_center
            # The center pixel is used as the approximation of the brightest pixel
            img_stars += beast.star(cx - cx_center, cy - cy_center, flux, -1)
        return img_stars

    def _generate_match(self, lis, img_stars):
        '''
        Returns the nearest match from the result of a db_match.

        Return
        ------
        match
        '''
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

        nearest_match = beast.db_match(fov_db, img_const)

        if nearest_match.p_match > self.P_MATCH_THRESH:
            return nearest_match
        else:
            return None

    def _extract_match_orientation(self, match):
        '''
        Calculate and extract the oreintation from the top match after
        star database search.

        Return
        ------
        float, float, float
            dec - rotation about the y-axis,
            ra  - rotation about the z-axis,
            ori - rotation about the camera axis
        '''
        match.winner.calc_ori()
        dec = match.winner.get_dec()
        ra = match.winner.get_ra()
        ori = match.winner.get_ori()
        return dec, ra, ori

    def _solve_orientation(self, star_list):
        '''
        Given a list of star positions with brightness values find the
        estimated orientation by search the star database.

        Return
        ------
        float, float, float
            dec - rotation about the y-axis,
            ra  - rotation about the z-axis,
            ori - rotation about the camera axis
        None
            match was invalid.
        '''
        img_stars = self._star_list_to_beast_stars_db(star_list)

        # Find the constellation matches
        img_stars_n_brightest = img_stars.copy_n_brightest(
            beast.cvar.MAX_FALSE_STARS + beast.cvar.REQUIRED_STARS)

        img_const_n_brightest = beast.constellation_db(img_stars_n_brightest,
                                                       beast.cvar.MAX_FALSE_STARS + 2, 1)

        lis = beast.db_match(self.C_DB, img_const_n_brightest)

        # Generate the match
        match = None
        if lis.p_match > self.P_MATCH_THRESH and lis.winner.size() >= beast.cvar.REQUIRED_STARS:
            match = self._generate_match(lis, img_stars)

        if match is None:
            raise SolverError('Cannot extract orientation from empty match. Solution failed for image!')

        orientation = self._extract_match_orientation(match)

        if orientation is None:
            logger.info('Unable to find orientation for image!')
            raise SolverError('Solution failed for image')

        return orientation

    def solve(self, orig_img) -> Tuple[float, float, float]:
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
            No matches found.
        '''

        correlation_timestamp = scet_int_from_time(time.time())  # Record the timestamp

        # Preprocess the image for solving
        img_grey = self._preprocess_img(orig_img, trace_id=correlation_timestamp)

        # Find the contours of the stars from binary image.
        contours = self._find_contours(img_grey, trace_id=correlation_timestamp)

        # Find most promising star coordinates to search with
        # from brightness contours.
        star_list = self._find_stars(img_grey, contours)

        # Find orientation using given stars.
        orientation = self._solve_orientation(star_list)

        return orientation
