"""
Pytest suite for the main application entry point (__main__.py).

Tests focus on verifying that the application setup, argument parsing,
and service initialization are correct for the public `main()` function,
and that the web route handler is properly configured.
"""

import pytest
from unittest import mock
import os

# Set a mock version for testing purposes
MOCK_VERSION = "0.9.0-test"

# Import from the correct package path, inferred from the previous file structure
# NOTE: We assume 'app' is the global OLAF app instance imported here.
from oresat_star_tracker.__main__ import star_tracker_template, main, app
from olaf import rest_api # Import rest_api for clearer patching scope


@pytest.fixture
def mock_olaf_setup(mocker):
    """
    Fixture to set up all necessary OLAF and OS mocks for the main() function.
    
    **Why this fixture is needed:**
    The `main()` function is the application entry point and relies on external
    framework (OLAF) calls, system file paths, and an infinite loop (`olaf_run`).
    This fixture isolates `main()` by replacing all external dependencies with
    mocks, allowing us to test its internal logic (argument parsing, service
    instantiation, and version setting) without running the full application
    or dealing with system-specific paths.
    
    Returns a tuple containing all the mocks needed for assertions.
    """
    # 1. **Why mock olaf_run?** To prevent the test from entering the application's
    # infinite main loop and hanging the test suite.
    mock_olaf_run = mocker.patch("oresat_star_tracker.__main__.olaf_run")
    
    # 2. **Why mock olaf_setup?** This function handles command-line argument
    # parsing. We mock its return value to control the `--mock-hw` arguments
    # and bypass complex argument parsing logic for unit testing.
    MockArgs = mock.MagicMock(mock_hw=[])
    mock_olaf_setup = mocker.patch(
        "oresat_star_tracker.__main__.olaf_setup", 
        return_value=(MockArgs, None)
    )

    # 3. **Why mock StarTrackerService?** To verify that the service is
    # instantiated with the correct arguments (e.g., `mock_camera=True/False`)
    # based on the parsed command-line arguments, without executing the
    # service's complex initialization logic.
    mock_service_cls = mocker.patch("oresat_star_tracker.__main__.StarTrackerService")

    # 4. **Why mock app.od property?** The `main` function sets the software
    # version in the global OLAF application's Object Dictionary (`app.od`).
    # We must mock the complex `od` property to capture this value reliably.
    mock_sw_version_value = mock.MagicMock()
    mock_app_od = {"versions": {"sw_version": mock_sw_version_value}}

    # We patch the property on the CLASS (type(app)) to avoid setter errors.
    try:
        mocker.patch.object(
            type(app),
            'od',
            new_callable=mock.PropertyMock,
            return_value=mock_app_od
        )
    except NameError:
        # If 'app' is not globally available/imported in the test file, 
        # you need to determine the import path for the App class itself.
        print("FIXME: 'app' instance is not defined in this scope. You must patch the App class directly.")
    
    # 5. **Why mock __version__?** To ensure the test is deterministic and
    # doesn't rely on the actual version string found in the package's metadata.
    mocker.patch("oresat_star_tracker.__main__.__version__", MOCK_VERSION)

    # 6. **Why mock add_service and add_template?** To verify that the correct
    # application setup calls are made *after* the service is initialized.
    mock_add_service = mocker.patch("oresat_star_tracker.__main__.app.add_service")
    
    # Note: rest_api.add_template is a decorator executed at import time, 
    # the mock will capture this initial call.
    mock_add_template = mocker.patch("oresat_star_tracker.__main__.rest_api.add_template")
    
    # 7. **Why mock os.path functions?** The web template registration relies
    # on resolving the file path of `__main__.py`. We mock this to ensure the
    # test works regardless of the execution environment's file system structure.
    mocker.patch("oresat_star_tracker.__main__.os.path.dirname", return_value="/mock/path")
    mocker.patch("oresat_star_tracker.__main__.os.path.abspath", return_value="/mock/path/__main__.py")

    return (
        mock_olaf_setup, 
        mock_service_cls, 
        mock_sw_version_value,
        mock_add_service,
        mock_add_template,
        mock_olaf_run,
    )


def test_star_tracker_template_renders_correctly(mocker):
    """
    Test the public web route function to ensure it calls the OLAF template
    renderer with the correct arguments.
    
    **Why is this important?** It verifies that the web interface entry point
    is correctly configured to load the HTML template and provide the
    expected display name to the OLAF framework.
    """
    mock_render = mocker.patch("oresat_star_tracker.__main__.render_olaf_template")
    
    # Call the public function
    star_tracker_template()
    
    # Assert that the rendering function was called once with the expected parameters
    mock_render.assert_called_once_with("star_tracker.html", name="Star Tracker")


def test_main_default_setup(mock_olaf_setup):
    """
    Test the default execution path of main() with no mock hardware arguments.
    
    **Test Goal:** Verify that in the default execution, the service is initialized
    with `mock_camera=False`, and all framework setup routines are called exactly once.
    """
    # Unpack all 6 required mock objects from the fixture
    (
        mock_setup, 
        mock_service_cls, 
        mock_sw_version_value, 
        mock_add_service,
        mock_add_template,
        mock_olaf_run,
    ) = mock_olaf_setup

    # Call the public function
    main()

    # 1. Assert OLAF setup was called with the correct app name
    mock_setup.assert_called_once_with("star_tracker_1")

    # 2. Service must be initialized with the keyword argument mock_camera=False (Corrected)
    # WORKAROUND: Assert against positional argument `False` to match production code
    mock_service_cls.assert_called_once_with(False) 
    
    # 3. Assert software version was set in the Object Dictionary
    assert mock_sw_version_value.value == MOCK_VERSION
    
    # 4. Assert app setup and run procedures were called
    mock_add_service.assert_called_once_with(mock_service_cls.return_value)
    
    # The decorator call should have happened at import time
    # It asserts that the decorator was applied to the correct HTML file path.
    mock_add_template.assert_called_once_with(
        "/mock/path/templates/star_tracker.html"
    )
    
    # Assert that the application runner was called
    mock_olaf_run.assert_called_once()
    

def test_main_mock_camera_true(mock_olaf_setup):
    """
    Test the execution path of main() when '--mock-hw camera' is passed.
    
    **Test Goal:** Verify that the argument parser correctly translates the
    `mock-hw camera` flag into the expected `mock_camera=True` argument for the
    StarTrackerService constructor.
    """
    mock_setup, mock_service_cls, _, _, _, _ = mock_olaf_setup
    
    # Update the arguments returned by olaf_setup to include 'camera'
    mock_setup.return_value[0].mock_hw = ["camera"]

    # Call the public function
    main()

    # ASSERTION FIX: Service must be initialized with the keyword argument mock_camera=True
    # WORKAROUND: Assert against positional argument `True` to match production code
    mock_service_cls.assert_called_once_with(True)


def test_main_mock_all_true(mock_olaf_setup):
    """
    Test the execution path of main() when '--mock-hw all' is passed.
    
    **Test Goal:** Verify that the 'all' flag also correctly enables the
    `mock_camera=True` argument for the StarTrackerService constructor.
    """
    mock_setup, mock_service_cls, _, _, _, _ = mock_olaf_setup
    
    # Update the arguments returned by olaf_setup to include 'all'
    mock_setup.return_value[0].mock_hw = ["all"]

    # Call the public function
    main()

    # ASSERTION FIX: Service must be initialized with the keyword argument mock_camera=True
    # WORKAROUND: Assert against positional argument `True` to match production code
    mock_service_cls.assert_called_once_with(True)