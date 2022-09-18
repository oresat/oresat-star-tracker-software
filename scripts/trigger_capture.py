#!/usr/bin/env python3

import argparse
import os
import time

bus_id = "vcan0"
node_id = '0x2C'
capture_idx = '0x6002'

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Trigger a capture command.')

    parser.add_argument('-n', '--ntimes', help='Number of captures to trigger.',
                        type=int, default=1)
    parser.add_argument(
        '-s', '--sleep', help='Number of seconds to sleep between triggers.', type=int, default=None)

    args = parser.parse_args()

    for i in range(args.ntimes):
        os.system(f"sudo olaf-sdo-transfer {bus_id} {node_id} 'w' {capture_idx}  0 u8")

        if args.sleep:
            time.sleep(args.sleep)
