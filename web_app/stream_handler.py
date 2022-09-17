import os
import json
import base64
from pathlib import Path
from datetime import datetime

import numpy as np
import cv2
from loguru import logger
from tornado.websocket import WebSocketHandler
from tornado.ioloop import PeriodicCallback
from tornado.options import options, define
from oresat_star_tracker.solver import Solver
from oresat_star_tracker.camera import Camera


MOCK = os.getenv('MOCK', 'false')

define('mock', default=MOCK.lower() == 'true', help='run in a mocked mode')


class StreamHandler(WebSocketHandler):

    DATA_DIR = 'data'
    SYSFS_PATH = '/sys/class/pru/prucam'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.stream = PeriodicCallback(self.new_frame, 1000)
        self.solver = Solver()
        self.solver.startup()
        self.img_num = 1

        Path(self.DATA_DIR).mkdir(parents=True, exist_ok=True)

        self._mock = options.mock
        if not self._mock:
            self.camera = Camera()
            self.camera.power_on()

    def open(self, *args, **kwargs):
        '''New connection'''

        self.new_frame()
        self.stream.start()

    def on_message(self, message: str):
        '''New message received'''

        logger.debug(f'new message: {message}')

        # Receive data from WebSocket
        json_dict = json.loads(message)
        json_dict_keys = json_dict.keys()

        try:
            if 'coarse_time' in json_dict_keys:
                coarse_time = json_dict['coarse_time']
                logger.info(f'setting coarse time to {coarse_time}')
                with open(self.SYSFS_PATH + '/coarse_time', 'w') as f:
                    f.write(coarse_time)

            if 'coarse_time' in json_dict_keys:
                fine_time = json_dict['fine_time']
                logger.info(f'setting fine time to {fine_time}')
                with open(self.SYSFS_PATH + '/fine_time', 'w') as f:
                    f.write(fine_time)

            if 'auto_exposure' in json_dict_keys:
                auto_exposure = json_dict['auto_exposure']
                logger.info(f'setting auto exposure to {auto_exposure}')
                with open(self.SYSFS_PATH + '/fine_time', 'w') as f:
                    f.write(int(auto_exposure))
        except Exception as exc:
            logger.error(str(exc))
            self.write_message(json.dumps({'error': str(exc)}))

    def on_close(self):
        '''Connection closed'''

        if self.stream.is_running:
            self.stream.stop()

        logger.debug('connection closed')

    def new_frame(self):
        '''Send new frame to client'''

        dec = 0.0
        ra = 0.0
        ori = 0.0
        error = ''

        if self._mock:
            data = cv2.imread(f'misc/test-data/downsample/samples/{self.img_num}.bmp')

            self.img_num += 1
            self.img_num %= 7
            if self.img_num == 0:
                self.img_num += 1
        else:
            data = self.camera.capture()

        try:
            dec, ra, ori = self.solver.solve(data)
        except Exception as exc:
            error = str(exc)
            logger.error(exc)

        file_name = datetime.now().strftime('capture-%Y-%m-%d-%H-%M-%S.bmp')
        file_path = f'{self.DATA_DIR}/{file_name}'
        cv2.imwrite(file_path, data)
        logger.info(f'wrote new capture to: {file_path}')

        _, img = cv2.imencode('.jpg', data)
        frame = base64.b64encode(img).decode('ascii')
        frame_message = 'data:image/jpg;base64, ' + frame

        message = {
            'frame': frame_message,
            'dec': dec,
            'ra': ra,
            'ori': ori,
            'error': error,
        }

        self.write_message(json.dumps(message))
        logger.debug('new frame was sent')
