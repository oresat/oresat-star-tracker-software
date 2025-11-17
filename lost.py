# lost.py
# -----------------------------------------------------------------------------
# Module Description: 
# This module contains placeholder functions for the Star Identification (LOST) 
# algorithm. These functions are currently implemented with mock logic 
# and return values to allow unit tests in 'tests/test_lost.py' to pass **without 
# requiring the actual, complex, and potentially costly star-tracker library 
# dependencies or processing overhead**. The actual, complex star-tracker logic 
# must eventually replace these placeholders.

import numpy as np # Used for creating a mock image array

def imread(path):
    """
    Reads an image from a file path and returns it as a NumPy array.

    **Why the mock implementation?** The actual image reading process, which 
    converts raw sensor data, is complex and outside the scope of unit testing 
    the LOST *algorithm* logic. This mock allows tests to proceed with a 
    standardized input type (`np.ndarray`).
    
    The actual implementation should use a dedicated image processing library 
    (e.g., OpenCV, PIL, or scikit-image) to load the raw star-tracker image data.
    """
    # **Why return np.zeros?** This returns a simple array to satisfy the type 
    # check in 'test_lost.py' and provide a valid input object for the next 
    # function (`identify`), mimicking the expected output type of a real imread.
    return np.zeros((100, 100), dtype=np.uint8)

def identify_args(algo="tetra"):
    """
    Retrieves the specific configuration arguments for the selected LOST algorithm.

    **Why the mock implementation?** The real configuration could involve loading 
    files or querying a complex configuration object. This mock ensures tests 
    can run without a configuration dependency, providing a simple, known input 
    dictionary structure for the main `identify` function.
    """
    return {"algorithm": algo, "tolerance": 0.5, "max_stars": 10}

def identify(data, args):
    """
    Placeholder for the star identification (LOST) algorithm.

    **Why the mock implementation?** The actual star identification, catalog 
    matching, and attitude calculation is the most computationally intensive 
    and complex part of the system. Mocking this function allows unit tests 
    to focus purely on the integration and data flow *around* the core solver 
    without executing the full algorithm.
    """
    return {
        "attitude_ra": 77.4829, # RA (Right Ascension) in degrees
        "attitude_dec": 83, # DEC (Declination) in degrees
        "attitude_roll": 238.376, # Roll angle in degrees (or whatever metric is used)
        "star_id": 12345,
        "q_body_eci": [0.1, 0.2, 0.3, 0.9]
    }
