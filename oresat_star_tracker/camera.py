import os
import io
from os.path import abspath, dirname

import numpy as np
import cv2
from datetime import datetime

from olaf import PRU, PRUError


class CameraError(Exception):
    '''An error has occured with camera'''


class Camera:
    '''Star tracker AR013x camera'''

    # these files are provide by the prucam-dkms debian package
    PRU0_FW = '/lib/firmware/prucam_pru0_fw.out'
    PRU1_FW = '/lib/firmware/prucam_pru1_fw.out'

    def __init__(self, mock: bool = False):

        self._mock = mock

        if self._mock:
            self._capture_path = f'{dirname(abspath(__file__))}/data/mock.bmp'
        else:
            self._capture_path = '/dev/prucam'
            self._prus = [PRU(0, self.PRU0_FW), PRU(1, self.PRU1_FW)]

    def power_on(self) -> None:
        '''Turn on the camera'''

        if self._mock:
            return

        try:
            self._prus[0].start()
            self._prus[1].start()
        except PRUError as exc:
            raise CameraError(exc)

        try:
            with open('/sys/class/pru/prucam/context_settings/x_size', 'r') as f:
                x_size = int(f.read())
            with open('/sys/class/pru/prucam/context_settings/y_size', 'r') as f:
                y_size = int(f.read())
        except FileNotFoundError:
            raise CameraError('no sysfs attributes for camera')

        self.image_size = (y_size, x_size)

        try:
            with open('/sys/class/pru/prucam/auto_exposure_settings/ae_enable', 'w') as f:
                f.write('1')
        except FileNotFoundError:
            raise CameraError('no sysfs attribute for camera auto-exposure')


    def power_off(self) -> None:
        '''Turn off the camera'''

        if not self._mock:
            try:
                self._prus[0].stop()
                self._prus[1].stop()
            except PRUError as exc:
                raise CameraError(exc)

    def capture(self, color=True) -> np.ndarray:
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
        numpy.ndarray
            image data in numpy array
        '''

        if self._mock:
            img = cv2.imread(self._capture_path, cv2.IMREAD_COLOR)
        else:
            # Read raw data
            fd = os.open(self._capture_path, os.O_RDWR)
            fio = io.FileIO(fd, closefd=False)
            imgbuf = bytearray(self.image_size[0] * self.image_size[1])
            fio.readinto(imgbuf)
            fio.close()
            os.close(fd)

            # Convert to image
            img = np.frombuffer(imgbuf, dtype=np.uint8).reshape(
                self.image_size[0],
                self.image_size[1]
            )

            # Convert to color
            if color is True:
                img = cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)

        return img

    def capture_and_save(self, file_path: str, color=True, ext='.bmp') -> None:
        '''Capture an image and save it to disk

        Parameters
        ----------
        file_path: str
            set the new file path
        color: bool
            enable color
        ext: str
            file extision including the '.'

        Raises
        ------
        CameraError
            failed to capture image
        '''

        img = self.capture(color)

        ok, data = cv2.imencode(ext, img)
        if not ok:
            raise CameraError('encode error')

        try:
            # Save image
            with open(file_path, 'wb') as f:
                f.write(data)
        except Exception as exc:
            raise CameraError(exc)
