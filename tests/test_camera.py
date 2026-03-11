from PIL import Image
import numpy as np
from pathlib import Path

capture_path = Path('/dev/prucam')

print(capture_path.stat())

try:
    print('capturing')
    raw = np.fromfile(capture_path, dtype=(np.uint8, 1280 * 960), count=1)[0]
except Exception as e:
    print(f'Error reading from file {e}')

with open(capture_path, 'rb') as f:
    raw = np.frombuffer(f.read(960 * 1280), np.uint8).reshape(960, 1280)

    img = Image.fromarray(raw)
    img.save('test.png')
