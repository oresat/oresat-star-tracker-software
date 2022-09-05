
import unittest
import sys

# Needs to be fixed
# sys.path.append('.')
from os.path import abspath, dirname

from .solver import Solver, SolverError
from .beast import beast

import datetime
from  datetime import datetime

def now(): return datetime.now()

class TestBeast(unittest.TestCase):


    def beast_setup(self):

        # Prepare constants
        self.P_MATCH_THRESH = 0.99
        self.YEAR = 1991.25
        self.MEDIAN_IMAGE = None
        self.S_DB = None
        self.SQ_RESULTS = None
        self.S_FILTERED = None
        self.C_DB = None

        data_dir = dirname(abspath(__file__)) + '/data'
        config_path = f'{data_dir}/configuration.txt'

        """https://heasarc.gsfc.nasa.gov/W3Browse/all/hipparcos.html"""
        db_path = f'{data_dir}/hipparcos.dat'

        # Load configuration
        beast.load_config(config_path)
        # Load star database
        print(now().strftime("%Y-%m-%d %H:%M:%S")+" entry beast.star_db()")
        self.S_DB = beast.star_db() # 0 seconds
        print(now().strftime("%Y-%m-%d %H:%M:%S")+" entry load_catalog()")

        # This will load the 51 Mb hipparcos data file as created by
        # European Space Agency.

        # This can be purely done by preprocessing, there
        # is no reason do do it at every startup.
        self.S_DB.load_catalog(db_path, self.YEAR) # 7 seconds
        print(now().strftime("%Y-%m-%d %H:%M:%S")+" exit load_catalog()")

        # Filter stars
        print(now().strftime("%Y-%m-%d %H:%M:%S")+" entry star_query()")
        self.SQ_RESULTS = beast.star_query(self.S_DB) # 1 sec
        print(now().strftime("%Y-%m-%d %H:%M:%S")+" exit star_query()")
        self.SQ_RESULTS.kdmask_filter_catalog() # 8 secons

        print(now().strftime("%Y-%m-%d %H:%M:%S")+" entry kdmask_uniform_density()")
        self.SQ_RESULTS.kdmask_uniform_density(beast.cvar.REQUIRED_STARS) # 23 seconds!!!!
        print(now().strftime("%Y-%m-%d %H:%M:%S")+" exit kdmask_uniform_density()")
        self.S_FILTERED = self.SQ_RESULTS.from_kdmask()

        # Set up constellation database
        print (now().strftime("%Y-%m-%d %H:%M:%S")+" entry constallation_db()")
        self.C_DB = beast.constellation_db(self.S_FILTERED, 2 + beast.cvar.DB_REDUNDANCY, 0) # 1 second
        print (now().strftime("%Y-%m-%d %H:%M:%S")+" exit constallation_db()")



    def setUp(self):
        """ setUp """
        print("ENTERY::setUp")
        self.beast_setup()
        print("EXIT::setUp")

    def test_run(self):
        """ test_run """
        print(self.S_DB)

if __name__ == """__main__""":
    unittest.main()
