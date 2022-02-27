import os
import io

import numpy as np
import cv2


class CameraError(Exception):
    '''An error has occured with camera'''


class Camera:
    '''Star tracker AR013x camera'''

    def __init__(self):

        self._capture_path = '/dev/prucam'

        try:
            with open('/sys/class/pru/prucam/context_settings/x_size', 'r') as f:
                x_size = int(f.read())
            with open('/sys/class/pru/prucam/context_settings/y_size', 'r') as f:
                y_size = int(f.read())
        except FileNotFoundError:
            raise CameraError('no sysfs attributes for camera')

        self.image_size = (y_size, x_size)

    def capture_bytes(self, color=True) -> bytes:
        '''Capture an image

        Parameters
        ----------
        color: bool
            enable color

        Raises
        ------
        CameraError
            failed to capture image

        Returns
        -------
        bytes
            image data
        '''

        # Read raw data
        fd = os.open(self._capture_path, os.O_RDWR)
        fio = io.FileIO(fd, closefd=False)
        imgbuf = bytearray(self.image_size[0] * self.image_size[1])
        fio.readinto(imgbuf)
        fio.close()
        os.close(fd)

        # Convert to image
        img = np.frombuffer(imgbuf, dtype=np.uint8).reshape(self.image_size[0], self.image_size[1])

        # Convert to color
        if color is True:
            img = cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)

        return img

    def capture(self, file_path: str, color=True):
        '''Capture an image and save it to disk

        Parameters
        ----------
        file_path: str
            set the new file path
        color: bool
            enable color

        Raises
        ------
        CameraError
            failed to capture image
        '''

        img = self.capture(color)

        ok, data = cv2.imencode('.bmp', img)
        if not ok:
            raise CameraError('encode error')

        try:
            # Save image
            with open(file_path, 'wb') as f:
                f.write(data)
        except Exception as exc:
            raise CameraError(exc)
