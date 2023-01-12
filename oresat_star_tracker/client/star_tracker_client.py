import traceback

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
        raise ValueError(data)
    elif co_type == CANopenTypes.d:
        raise ValueError(raw_data)
    else:
        raise ValueError(f'invalid data type:{co_type}')
    return data


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
    try:
        payload = encode_value(1, CANopenTypes.i8)
        sdo.download(0x6002, 0, payload)
    except Exception as exc:
        traceback.print_exc()
        raise exc


def get_star_tracker_state(sdo):
    ''' Retreive tracker state.  '''
    returned_value = sdo.upload(0x6000, 0)
    decoded_state = decode_value(returned_value, CANopenTypes.i8)[0]
    return decoded_state


def set_star_tracker_state(sdo, state_command):
    payload = encode_value(state_command.value, CANopenTypes.i8)
    sdo.download(0x6000, 0, payload)
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


'''
TOO SLOW UNUSABLE
'''


"""
def read_image_file(sdo, file_name: str):
    sdo[0x3003][1].raw = file_name.encode('utf-8')

    node, network = connect()
    sdo = node.sdo
    sdo.RESPONSE_TIMEOUT = 5.0

    infile = sdo[0x3003][2].open('rb', encoding='ascii', buffering=1024,
                                 size=3686454, block_transfer=True)


    file_bytes = np.asarray(bytearray(infile.read()), dtype=np.uint8)
    total_size = 3686454
    total_read = 0
    block_size = 1024
    num_blocks = total_size % block_size
    for  _ in range(num_blocks):
        contents = infile.read(block_size)
        if not contents:
            break;
        total_read+=block_size
        print('Read bytes ', total_read)
    print("after::reading.")

    # retval = cv2.imdecode(contents, cv2.IMREAD_GRAYSCALE)
    infile.close()
    # print("read-shape: ", np.shape(retval))
    network.disconnect()
    return retval
"""
