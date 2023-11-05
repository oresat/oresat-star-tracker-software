import unittest
from os.path import abspath, dirname

from oresat_star_tracker.beast import beast


class TestBeast(unittest.TestCase):
    @classmethod
    def beast_setup(cls):
        # Prepare constants
        cls.YEAR = 1991.25
        cls.MEDIAN_IMAGE = None

        data_dir = dirname(abspath(__file__)) + "/../oresat_star_tracker/data"
        config_path = f"{data_dir}/configuration.txt"

        db_path = f"{data_dir}/hipparcos.dat"

        # Load configuration
        beast.load_config(config_path)

        # Load star database - duration: 0 second(s)
        cls.S_DB = beast.star_db()

        # This will load the 51 Mb hipparcos data file as
        # created by  European Space Agency:
        #   https://heasarc.gsfc.nasa.gov/W3Browse/all/hipparcos.html

        # This can be purely done by preprocessing, there
        # is no reason do it at every startup. duration 7 second(s)
        cls.S_DB.load_catalog(db_path, cls.YEAR)

        # Duration 1 second(s)
        cls.SQ_RESULTS = beast.star_query(cls.S_DB)

        # Duration 8 second(s)
        cls.SQ_RESULTS.kdmask_filter_catalog()

        # Duration 23 seconds!
        cls.SQ_RESULTS.kdmask_uniform_density(beast.cvar.REQUIRED_STARS)

        cls.S_FILTERED = cls.SQ_RESULTS.from_kdmask()

        # Set up constellation database, Duration 1 second(s)
        cls.C_DB = beast.constellation_db(cls.S_FILTERED, 2 + beast.cvar.DB_REDUNDANCY, 0)

    @classmethod
    def setUpClass(cls):
        """ """
        cls.beast_setup()

    def test_constellation_db_successfully_constructed(self):
        self.assertTrue(TestBeast.C_DB is not None, "constellation database was not constructed.")

    def test_star_db_successfully_constructed(self):
        self.assertTrue(TestBeast.S_DB is not None, "star database was not constructed.")
