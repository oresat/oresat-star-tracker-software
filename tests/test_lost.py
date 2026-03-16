"""
Tests for the LOST attitude solver functionality.

This file contains unit tests for the functions intended to integrate with 
the LOST (Lost-in-Space Star Tracker) star identification algorithm. 
Note: The imported 'lost' module currently uses mock placeholders.
*must use sudo for Lost program to work
"""

import os
import unittest
import lost


class TestLost(unittest.TestCase):
    """
    Test suite for the star attitude solving process provided by the 'lost' module.
    
    This suite verifies that the data flow and function outputs (using mock data 
    from lost.py) are correct and as expected by the system.
    """
    def setUp(self):
        """
        Setup method to prepare mock input data and execute the target functions 
        before each test case is run.
        """
        # --- Arrange: Setup necessary file path ---
        # Define a mock image file path for the imread function to consume.
        # Define path
        self.img_file = "./images/capture-2022-09-25-09-40-25.png"
        self.current_dir = os.path.dirname(__file__)
        self.path = os.path.join(self.current_dir, self.img_file)

        # --- Act: Execute the LOST pipeline functions with mock data ---

        # 1. Read Image: Simulate loading the star-tracker image.
        self.data = lost.imread(self.path)
    
        # 2. Get Arguments: Simulate configuring the star identification algorithm.
        self.lost_args = lost.identify_args(algo="tetra")

        # 3. Identify Attitude: Execute the core identification function. 
        self.lost_data = lost.identify(self.data, self.lost_args)

    def test_identify_attritude_values(self):
        """
        Tests that the Lost identify function returns the expected mock attitude values 
        (Right Ascension, Declination, and Roll) from the core processing pipeline.
        
        Since 'lost.py' uses hardcoded mock return values, this test verifies 
        the integration and the structure of the data returned by 'identify'.
        """
        # --- Assert: Verify the results from the setup execution ---
        
        # Check Right Ascension (RA): attitude_ra
        # The test checks the integer part to tolerate minor floating-point errors 
        # or differences in precision, verifying the core value (77.4829 -> 77).
   
        expected_ra_int = 77
        actual_ra_int = int(self.lost_data.get("attitude_ra", 0))
        self.assertEqual(actual_ra_int, expected_ra_int, "RA integer value mismatch")

        # Check Declination (Dec): attitude_dec
        # Verifies the integer part of the Declination value (83.0 -> 83).

        expected_dec_int = 83
        actual_dec_int = int(self.lost_data.get("attitude_dec", 0))
        self.assertEqual(actual_dec_int, expected_dec_int, "Dec integer value mismatch")

        # Check Roll Angle: attitude_roll
        # Verifies the integer part of the Roll Angle (238.376 -> 238).

        expected_roll_int = 238
        actual_roll_int = int(self.lost_data.get("attitude_roll", 0))
        self.assertEqual(actual_roll_int, expected_roll_int, "Roll integer value mismatch")