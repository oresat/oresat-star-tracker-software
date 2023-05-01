import time
import traceback
import unittest

from oresat_star_tracker.star_tracker_resource import State as StarTrackerState
from oresat_star_tracker.star_tracker_resource import StateCommand

from oresat_star_tracker.client.star_tracker_client import connect
from oresat_star_tracker.client.star_tracker_client import trigger_capture_star_tracker
from oresat_star_tracker.client.star_tracker_client import get_star_tracker_state
from oresat_star_tracker.client.star_tracker_client import set_star_tracker_state
from oresat_star_tracker.client.star_tracker_client import is_valid_star_tracker_state
from oresat_star_tracker.client.star_tracker_client import fetch_files_fread


class TestStarTrackerCanInterface(unittest.TestCase):

    def setUp(self):
        '''Connect to remote can node  for Star Tracker'''
        self.node, self.network = connect()
        self.sdo = self.node.sdo
        # long timeout, due to connection and startup issues.
        self.sdo.RESPONSE_TIMEOUT = 5.0

    def tearDown(self):
        '''
        Disconnect from rmeote can node.
        '''
        self.network.disconnect()

    def test_get_state(self):
        '''
        Given a star tracker in active state which we are connected to,
        Then we can retreive its current state with an SDO and the
        state is one of the valid states
        '''
        state = get_star_tracker_state(self.sdo)
        self.assertTrue(is_valid_star_tracker_state(state))

    def test_switch_states_standby_capture(self):
        '''
        Given a star tracker in active state which we are connected to,
        Then we can switch beteween states as follows:
            Original State -> Capture  -> Star Tracking -> Standby -> Original State
        '''
        # 1. Retreive the original state
        save_original_state = get_star_tracker_state(self.sdo)
        self.assertTrue(is_valid_star_tracker_state(save_original_state))

        # 2. Ensure can set to CAPTURE state
        set_star_tracker_state(self.sdo, StateCommand.CAPTURE)
        # set_star_tracker_capture(self.sdo)
        # set_star_tracker_state(self.sdo, StarTrackerState.CAPTURE)
        decoded_state = get_star_tracker_state(self.sdo)
        self.assertEqual(decoded_state, StarTrackerState.CAPTURE.value)
        time.sleep(5)

        # 3. Ensure can set to STAR_TRACKING state
        set_star_tracker_state(self.sdo, StateCommand.STAR_TRACKING)
        # set_star_tracker_star_tracking(self.sdo)
        decoded_state = get_star_tracker_state(self.sdo)
        self.assertEqual(decoded_state, StarTrackerState.STAR_TRACKING.value)
        time.sleep(5)

        # 4. Ensure can set to STANDBY state
        set_star_tracker_state(self.sdo, StateCommand.STANDBY)
        # set_star_tracker_standby(self.sdo)

        decoded_state = get_star_tracker_state(self.sdo)
        self.assertEqual(decoded_state, StarTrackerState.STANDBY.value)
        time.sleep(5)

        # 5. Revert to original state.
        set_star_tracker_state(self.sdo, StateCommand.command(save_original_state))

    def test_list_files_fread_cache(self):
        '''
        Test listing fread cache.
        '''
        max_files = 5
        capture_files = fetch_files_fread(self.sdo, 'capture', max_files)
        num_capture_files = len(capture_files)
        self.assertTrue(num_capture_files > 0 and num_capture_files <= max_files)
        for capture_file in capture_files:
            self.assertTrue(capture_file.startswith('oresat-dev_capture'))
            self.assertTrue(capture_file.endswith('bmp'))

    def test_invoke_capture(self):
        '''
        Test invoke capture
        '''
        trigger_capture_star_tracker(self.sdo)

    def test_orientation_tpdo(self):
        '''
        Given that the star tracker is put into star tracking mode.
        Then, we can subscribe to and receive callbacks for tpdo, for
        orientation updates.

        Note: This test is likely to fail if the star tracker is not
        pointing to valid star field image.
        '''
        # Put startracker in tracking state
        set_star_tracker_state(self.sdo, StateCommand.STAR_TRACKING)

        # Initialize the tpdo
        self.node.tpdo.read()

        num_updates_to_check = 3
        for _ in range(num_updates_to_check):
            received_orientation = dict()

            def orientation_callback(message):
                for var in message:
                    received_orientation[var.name] = var.raw

            received_timestamp = dict()

            def timestamp_callback(message):
                for var in message:
                    received_timestamp[var.name] = var.raw

            # Star Tracker Status:
            # This is the one which contains star tracker paremeters as tpdo
            self.node.tpdo[3].add_callback(orientation_callback)

            # Orientation.Timestamp
            # This contains timestamp: Orientation.Timestamp
            # self.node.tpdo[4].add_callback(timestamp_callback)

            # Sleep for 5 sec
            time.sleep(5)
            # Validate the parameters received from tpdo
            # This fails when the star tracker is not pointing to a solvable region
            self.assertTrue(len(received_orientation) > 0,
                            f'Empty oreintation received: {received_orientation}')
            self.assertTrue('Star tracker status' in received_orientation)
            self.assertTrue('Orienation.Right Ascension' in received_orientation)
            self.assertTrue('Orienation.Declination' in received_orientation)

            # self.assertTrue('Orienation.Timestamp' in received_timestamp)

        set_star_tracker_state(self.sdo, StateCommand.STANDBY)
