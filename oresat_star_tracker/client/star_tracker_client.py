from argparse import ArgumentParser
from enum import IntEnum, Enum, auto
from os.path import abspath, dirname
from struct import pack, unpack

import canopen
import numpy as np

from olaf import Resource, new_oresat_file, scet_int_from_time
from oresat_star_tracker.star_tracker_resource import State as StarTrackerState
from oresat_star_tracker.star_tracker_resource import StateCommand

DEFAULT_BUS_ID = 'vcan0'
STARTRACKER_NODE_ID = 0x2C

EDS_FILE = dirname(abspath(__file__)) + '/../../oresat_star_tracker/data/star_tracker.eds'


def connect(bus_id=DEFAULT_BUS_ID, node_id=STARTRACKER_NODE_ID):
    '''
    Connect to to the startracker node
    '''
    network = canopen.Network()
    node = canopen.RemoteNode(node_id, EDS_FILE)
    network.add_node(node)
    network.connect(bustype='socketcan', channel=bus_id)
    return node, network


def trigger_capture_star_tracker(sdo):
    '''
    Send the capture command.
    '''
    sdo[0x6002].phys = 1


def get_star_tracker_state(sdo):
    ''' Retreive tracker state.  '''
    decoded_state = sdo[0x6000].phys
    return decoded_state


def set_star_tracker_state(sdo, state_command):
    sdo[0x6000].phys = state_command.value
    return True


def is_valid_star_tracker_state(state):
    '''
    Check that tracker is in valid state.
    '''
    valid_states = np.array(sorted(StarTrackerState), dtype=np.int8)
    result = np.where(valid_states == state)
    return np.shape(result) == (1, 1)


def fetch_files_fread(sdo, keyword='capture', max_files=None):
    '''
    Fetch all the tracker files from the fread cache.
    '''
    FCACHE_INDEX = 0x3002
    sdo[FCACHE_INDEX][3].phys = 0  # on_write:file_cahce

    # 2. Clear any preset filters. # on_write_filter
    sdo[FCACHE_INDEX][4].raw = keyword.encode()  # b'capture'  # Clear filter

    # b'\00'  # Clear filter

    # QOD: Why is list files returning 0 ?

    capture_files = []

    for i in range(sdo[FCACHE_INDEX][5].phys):
        if max_files and i >= max_files:
            break
        # 4. Set the read index.
        sdo[FCACHE_INDEX][6].phys = i
        # 5. Print the file name at the index.
        file_name = sdo[FCACHE_INDEX][7].phys
        capture_files.append(file_name)
    return capture_files
