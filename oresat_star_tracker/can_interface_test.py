import random
from argparse import ArgumentParser
from enum import IntEnum
from time import time
import sys
from argparse import ArgumentParser
from struct import pack, unpack
from enum import Enum, auto

import canopen
import cv2
import traceback
from olaf import Resource, logger, new_oresat_file, scet_int_from_time

import unittest
import sys
import numpy as np
from os.path import abspath, dirname

import datetime
from  datetime import datetime

from .star_tracker_resource import State as StarTrackerState

DEFAULT_BUS_ID = 'vcan0'
STARTRACKER_NODE_ID = 0x2C

class CANopenTypes(Enum):
    '''All valid canopen types supported'''
    b = auto()
    i8 = auto()
    u8 = auto()
    i16 = auto()
    u16 = auto()
    i32 = auto()
    u32 = auto()
    i64 = auto()
    u64 = auto()
    f32 = auto()
    f64 = auto()
    s = auto()
    d = auto()  # DOMAIN type

DECODE_KEYS = {
    CANopenTypes.b: '?',
    CANopenTypes.i8: 'b',
    CANopenTypes.u8: 'B',
    CANopenTypes.i16: 'h',
    CANopenTypes.u16: 'H',
    CANopenTypes.i32: 'i',
    CANopenTypes.u32: 'I',
    CANopenTypes.i64: 'q',
    CANopenTypes.f32: 'f',
    CANopenTypes.f64: 'd',
}

def decode_value(raw_data, co_type):
    '''
    Decode can open value
    '''
    data = None
    if co_type == CANopenTypes.b:
        data = unpack('?', raw_data)
    elif co_type == CANopenTypes.i8:
        data = unpack('b', raw_data)
    elif co_type == CANopenTypes.u8:
        data = unpack('B', raw_data)
    elif co_type == CANopenTypes.i16:
        data = unpack('h', raw_data)
    elif co_type == CANopenTypes.u16:
        data = unpack('H', raw_data)
    elif co_type == CANopenTypes.i32:
        data = unpack('i', raw_data)
    elif co_type == CANopenTypes.u32:
        data = unpack('I', raw_data)
    elif co_type == CANopenTypes.i64:
        data = unpack('q', raw_data)
    elif co_type == CANopenTypes.u64:
        data = unpack('Q', raw_data)
    elif co_type == CANopenTypes.f32:
        data = unpack('f', raw_data)
    elif co_type == CANopenTypes.f64:
        data = unpack('d', raw_data)
    elif co_type == CANopenTypes.s:
        data = raw_data.decode('utf-8')
        logger.info(data)
        sys.exit(0)
    elif co_type == CANopenTypes.d:
        logger.info(raw_data)
        sys.exit(0)
    else:
        logger.info('invalid data type')
        sys.exit(0)
    return data;

def encode_value(value, co_type):
    '''
    Takes the value and a CAN open type end encodes
    it for writing.
    '''
    if co_type == CANopenTypes.b:
        raw_data = pack('?', int(value))
    elif co_type == CANopenTypes.i8:
        raw_data = pack('b', int(value))
    elif co_type == CANopenTypes.u8:
        raw_data = pack('B', int(value))
    elif co_type == CANopenTypes.i16:
        raw_data = pack('h', int(value))
    elif co_type == CANopenTypes.u16:
        raw_data = pack('H', int(value))
    elif co_type == CANopenTypes.i32:
        raw_data = pack('i', int(value))
    elif co_type == CANopenTypes.u32:
        raw_data = pack('I', int(value))
    elif co_type == CANopenTypes.i64:
        raw_data = pack('q', int(value))
    elif co_type == CANopenTypes.u64:
        raw_data = pack('Q', int(value))
    elif co_type == CANopenTypes.f32:
        raw_data = pack('f', float(value))
    elif co_type == CANopenTypes.f64:
        raw_data = pack('d', float(value))
    elif co_type == CANopenTypes.s:
        raw_data = value.encode('utf-8')
    elif co_type == CANopenTypes.d:
        raw_data = value
    else:
        raise RuntimeError('invalid data type')
    return raw_data

def connect(bus_id = DEFAULT_BUS_ID, node_id = STARTRACKER_NODE_ID):
    '''
    Connect to to the startracker node
    '''
    network = canopen.Network()
    node = canopen.RemoteNode(node_id, canopen.ObjectDictionary())
    network.add_node(node)
    network.connect(bustype='socketcan', channel=bus_id)
    return node, network

def trigger_capture_star_tracker(sdo):
    '''
    Send the capture command.
    '''
    try:
        payload = encode_value(1, CANopenTypes.i8)
        sdo.download(0x6002, 0, payload)
    except Exception as exc:
        print(exc)
        traceback.print_exc()
        raise exc

def get_star_tracker_state(sdo):
    '''
    Retreive tracker state.
    '''
    returned_value = sdo.upload(0x6000, 0)
    decoded_state  = decode_value(returned_value, CANopenTypes.i8)[0]
    return decoded_state

def set_star_tracker_state(sdo, state):
    '''
    Set the tracker state.
    '''
    payload = encode_value(state, CANopenTypes.i8)
    sdo.download(0x6000, 0, payload)
    return True

def is_valid_star_tracker_state(state):
    '''
    Check that tracker is in valid state.
    '''
    valid_states = np.array(sorted(StarTrackerState), dtype=np.int8)
    result = np.where(valid_states == state)
    return np.shape(result) ==  (1,1)

class TestStarTrackerCanInterface(unittest.TestCase):

    def setUp(self):
        '''Connect to remote can node  for Star Tracker'''
        logger.info("ENTRY::setUp")
        self.node, self.network = connect()
        self.sdo = self.node.sdo
        # long timeout, due to connection and startup issues.
        self.sdo.RESPONSE_TIMEOUT = 5.0
        logger.info("EXIT::setUp")

    def tearDown(self):
        '''
        Disconnect from rmeote can node.
        '''
        logger.info("ENTRY::tearDown")
        self.network.disconnect()
        logger.info("EXIT::tearDown")

    def test_get_state(self):
        '''
        Test that we can retreive the current tracker stat,  and that the tate is one of the
        valid star tracker states.
        '''
        logger.info("ENTRY:test_get_state")
        try:
            state = get_star_tracker_state(self.sdo)
            self.assertTrue(is_valid_star_tracker_state(state))
        except Exception as exc:
            print(exc)
            traceback.print_exc()
            raise exc
        logger.info("EXIT:test_get_state")


    def test_switch_states_standby_capture(self):
        '''
        Switch state Unknown -> Capture -> Standby -> Unknown
        '''
        logger.info("ENTRY:test_switch_states_standby_capture")
        try:
            # 1. Retreive the original state
            save_original_state = get_star_tracker_state(self.sdo)
            self.assertTrue(is_valid_star_tracker_state(save_original_state))

            # 2. Ensure can set to CAPTURE state
            set_star_tracker_state(self.sdo, StarTrackerState.CAPTURE)
            decoded_state = get_star_tracker_state(self.sdo)
            self.assertEqual(decoded_state, StarTrackerState.CAPTURE)

            # 3. Revert to original state.
            set_star_tracker_state(self.sdo, save_original_state)

        except Exception as exc:
            print(exc)
            traceback.print_exc()
            raise exc

        logger.info("EXIT:test_switch_states_standby_capture")

    def test_invoke_capture(self):
        '''
        Test invoke capture
        '''
        logger.info("ENTRY:test_invoke_capture")
        trigger_capture_star_tracker(self.sdo)
        logger.info("EXIT:test_invoke_capture")


    def test_fetch_from_fread_cache(self):
        '''
        Test listing fread cache
        '''
        pass

if __name__ == "__main__":
    unittest.main()
