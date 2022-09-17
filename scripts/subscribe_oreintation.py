#!/usr/bin/env python3

import argparse
import os
import time

from oresat_star_tracker.star_tracker_resource import State as StarTrackerState
from oresat_star_tracker.star_tracker_resource import StateCommand


from oresat_star_tracker.client.star_tracker_client import connect
from oresat_star_tracker.client.star_tracker_client import trigger_capture_star_tracker
from oresat_star_tracker.client.star_tracker_client import get_star_tracker_state
from oresat_star_tracker.client.star_tracker_client import set_star_tracker_state
from oresat_star_tracker.client.star_tracker_client import is_valid_star_tracker_state
from oresat_star_tracker.client.star_tracker_client import fetch_files_fread
from oresat_star_tracker.client.star_tracker_client import read_image_file


bus_id="vcan0"
node_id='0x2C'
capture_idx='0x6002'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Listen for Star Tracker Orientations.')

    args = parser.parse_args()

    node, network = connect()
    sdo = node.sdo

    # long timeout, due to connection and startup issues.
    sdo.RESPONSE_TIMEOUT = 5.0

    # Put startracker in tracking state
    set_star_tracker_state(sdo, StateCommand.STAR_TRACKING)


    # Initialize the tpdo
    node.tpdo.read()

    num_updates_to_check = 100
    for  _ in range(num_updates_to_check):
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
        node.tpdo[3].add_callback(orientation_callback)

        # Orientation.Timestamp
        # This contains timestamp: Orientation.Timestamp
        # node.tpdo[4].add_callback(timestamp_callback)

        # Star Tracker Status:
        # This is the one which contains star tracker paremeters as tpdo
        node.tpdo[3].add_callback(orientation_callback)

        # Orientation.Timestamp
        # This contains timestamp: Orientation.Timestamp
        node.tpdo[4].add_callback(timestamp_callback)
        time.sleep(4)
        print('Waiting for orientation.')
        print(f'Received Orientation{received_timestamp["Orientation.Timestamp"]}:{received_orientation}'

    set_star_tracker_state(sdo, StateCommand.STANDBY)

