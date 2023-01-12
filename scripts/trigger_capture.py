#!/usr/bin/env python3

import argparse
import os
import time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trigger a capture command.')

    parser.add_argument('-r', '--repeat-count', help='Number of captures to trigger.',
                        type=int, default=1)

    parser.add_argument('-b', '--bus', help='Number of captures to trigger.',
                        type=str, default='vcan0')

    parser.add_argument('-n', '--node-id', help='Number of captures to trigger.',
                        type=str, default='0x2C')

    parser.add_argument('-c', '--capture_idx', help='Number of captures to trigger.',
                        type=str, default='0x6002')

    parser.add_argument('-s', '--sleep',
                        help='Number of seconds to sleep between triggers.',
                        type=int, default=1)

    args = parser.parse_args()
    bus_id = args.bus
    node_id = args.node_id
    capture_idx = args.capture_idx

    for i in range(args.repeat_count):
        os.system(f"sudo olaf-sdo-transfer {bus_id} {node_id} 'w' {capture_idx}  0 u8")

        if args.sleep:
            time.sleep(args.sleep)
