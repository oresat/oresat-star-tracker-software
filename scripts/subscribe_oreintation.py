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


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Listen for Star Tracker Orientations.')

    parser.add_argument('-r', '--record-time',
                        help='Number of seconds to record for', type=int, default=10)
    parser.add_argument('-o', '--output-file',
                        help='Output file to recored orientations to ',
                        type=str, default="output.txt")
    parser.add_argument('-b', '--bus',
                        help='CAN bus identifier, defaults to virutal CAN bus vbus0',
                        type=str, default="vcan0")
    parser.add_argument('-n', '--node-id',
                        help='Node identifier for star tracker, defaults to 0x2C',
                        type=str, default="0x2C")
    parser.add_argument('-c', '--capture-idx',
                        help='Command index to subscribe to, defaults to 0x6002',
                        type=str, default="0x6002")

    args = parser.parse_args()

    record_time = args.record_time
    capture_idx = args.capture_idx
    bus_id = args.bus
    node_id = args.node_id

    node, network = connect()
    sdo = node.sdo

    # long timeout, due to connection and startup issues.
    sdo.RESPONSE_TIMEOUT = 5.0

    # Put startracker in tracking state
    set_star_tracker_state(sdo, StateCommand.STAR_TRACKING)

    # Initialize the tpdo
    node.tpdo.read()

    oreintations_received = []

    def orientation_callback(message):
        received_message = dict()
        for var in message:
            received_message[var.name] = var.raw
        print('received_masage', received_message)

        dec = received_message['Orienation.Declination']
        ra = received_message['Orienation.Right Ascension']
        ori = received_message['Orienation.Roll']

        oreintations_received.append([dec, ra, ori])
        print(f'orientation-received: dec:{dec}, ra:{ra}, ori:{ori}')

    received_timestamps = []

    def timestamp_callback(message):
        received_message = dict()
        for var in message:
            received_message[var.name] = var.raw

        timestamp = received_message["Orienation.Timestamp"]
        received_timestamps.append(timestamp)
        print(f'timestamp: {timestamp}')

    # star-tracker status:
    # This is the one which contains star tracker paremeters as tpdo
    node.tpdo[3].add_callback(orientation_callback)
    node.tpdo[4].add_callback(timestamp_callback)

    print(f'Recording orientations for {record_time} seconds.')

    time.sleep(record_time)

    print(f'Number of Orientations Received: {len(oreintations_received)}')
    print(f'Number of Timetamps Received: {len(received_timestamps)}')

    set_star_tracker_state(sdo, StateCommand.STANDBY)
