import numpy as np
from PIL import Image

if __name__ == "__main__":
    color_img = Image.open("mock_img.png")
    color_img = color_img.convert("RGB")
    print(color_img.size)

    values = np.array(color_img)

    print(values.shape)

    with open("mock_img.bin", "wb") as fd:
        fd.write(values)
