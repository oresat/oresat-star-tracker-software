#!/usr/bin/env python3

"""
Hand written client to ease interaction with the startracker over can-0
"""
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

DEFAULT_BUS_ID='vcan0'
DEFAULT_NODE_ID='0x2C'
INDEX_MAP={ 'Capture' : 0x6002 } 

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

def can_decode_value(value, co_type):
    """
    Decode can open value
    """
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
        print(data)
        sys.exit(0)
    elif co_type == CANopenTypes.d:
        print(raw_data)
        sys.exit(0)
    else:
        print('invalid data type')
        sys.exit(0)
    return data;


def can_encode_value(value, co_type):
    """
    Takes the value and a can open type end encodes 
    it for writing.
    """
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

# def download_sdo(index, sub_index, 

def capture_image(node):
    """
    Send the capture Command 
    """
    try:
        node.sdo.download(INDEX_MAP['Capture'], 0, can_encode_value(1, CANopenTypes.i8))
    except Exception as exc: 
        print(exc) 
        traceback.print_exc()

def diagnostics(node):
    print("Running diagnostics")

def connect(bus_id = DEFAULT_BUS_ID, node_id = DEFAULT_NODE_ID):
    network = canopen.Network()
    node = canopen.RemoteNode(int(node_id, 16), canopen.ObjectDictionary())
    network.add_node(node)
    network.connect(bustype='socketcan', channel=bus_id)
    return node, network
 
if __name__ =="__main__":
    node, network = connect()
    diagnostics(node) 
    capture_image(node)
    network.disconnect()

