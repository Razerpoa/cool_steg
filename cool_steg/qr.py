import qrcode
import numpy as np
from PIL import Image
from pyzbar import pyzbar

def generate_qr_pixels(data: bytes, version: int = 1, box_size: int = 1) -> tuple[list[int], tuple[int, int]]:
    qr = qrcode.QRCode(
        version=version, 
        error_correction=qrcode.ERROR_CORRECT_L, 
        border=0, 
        box_size=box_size
    )
    qr.add_data(data)
    qr.make()
    img = qr.make_image().get_image().convert("L")
    pixels = list(img.get_flattened_data())
    # Normalize to 0 (black) and 255 (white)
    pixels = [255 if p > 128 else 0 for p in pixels]  # type: ignore
    return pixels, img.size

def save_qr_from_pixels(pixels: list[int], size: tuple[int, int], output_path: str):
    img_array = np.array(pixels, dtype=np.uint8).reshape((size[1], size[0]))
    img = Image.fromarray(img_array, mode='L')
    img.save(output_path)

def decode_qr_from_pixels(pixels: list[int], size: tuple[int, int], scale_factor: int = 10) -> str:
    img_array = np.array(pixels, dtype=np.uint8).reshape((size[1], size[0]))
    img = Image.fromarray(img_array, mode='L')

    new_size = (img.width * scale_factor, img.height * scale_factor)
    img_upscaled = img.resize(new_size, Image.Resampling.NEAREST)
    img_upscaled = img_upscaled.convert("RGB")

    data = pyzbar.decode(img_upscaled)[0]
    if data.type != "QRCODE":
        raise Exception("Not QR!")
    result = data.data.decode()

    return result