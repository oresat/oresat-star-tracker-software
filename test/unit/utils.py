import unittest
import sys
import os
import io
import cv2
import numpy as np
from timeit import default_timer as timer

def read_file_to_buffer(file_path, buf_size):
    '''Read the file into a buffer of given size.
    '''
    buf = bytearray(buf_size)
    fd = os.open(file_path, os.O_RDWR)
    fio = io.FileIO(fd, closefd=False)
    fio.readinto(buf)
    fio.close()
    os.close(fd)
    return buf


def read_image_file_to_numpy_buffer(file_path, y_size, x_size):
    ''' Read image into numpy buffer.
    '''
    imgbuf = read_file_to_buffer(file_path, y_size * x_size)
    # Reshape into image.
    img = np.frombuffer(imgbuf, dtype=np.uint8).reshape(y_size, x_size)

    return img

def read_preprocess_image(image_path, y_size, x_size, color=True):
      ''' Read the image
      '''
      print("read_preprocess_image:y_size * x_size", y_size * x_size)
      img = read_image_file_to_numpy_buffer(image_path, y_size, x_size)

      # Convert to color
      if color is True:
          img = cv2.cvtColor(img, cv2.COLOR_BayerBG2BGR)

      return img


