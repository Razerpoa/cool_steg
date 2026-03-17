from PIL import Image
import random
import struct
from typing import cast

target_start_index = 0

def chop_to_pieces(binary_string: str, piece_size: int):
    return [binary_string[i:i+piece_size] for i in range(0, len(binary_string), piece_size)]

def get_img_from_path(image_path: str):
    img = Image.open(image_path)
    return img

def embed_data(img: Image.Image, data_bytes: bytes, seed: int, target_start_index: int = 0, piece_size: int = 2) -> Image.Image:
    pixels = list(img.get_flattened_data())
    
    # 1. Prepare Data
    # data_len in bits for the header
    data_bits_total = len(data_bytes) * 8
    header = struct.pack(">I", data_bits_total)
    
    full_data = header + data_bytes
    data_in_binary = "".join(format(byte, '08b') for byte in full_data)
    pieces = [data_in_binary[i:i+piece_size] for i in range(0, len(data_in_binary), piece_size)]
    
    # 2. Identify available pixels based on mode
    if img.mode == "RGBA":
        # Only use pixels that are mostly opaque (Alpha > 127)
        available_indices = [
            i for i in range(target_start_index, len(pixels))
            if pixels[i][3] >= 128
        ]
    else:
        available_indices = list(range(target_start_index, len(pixels)))

    rng = random.Random(seed)
    rng.shuffle(available_indices)
    
    # 3. Calculate capacity correctly
    # Determine how many channels per pixel we actually have
    sample_pixel = pixels[0]
    channels_per_pixel = len(sample_pixel) if isinstance(sample_pixel, (tuple, list)) else 1
    
    needed_pixels = (len(pieces) + channels_per_pixel - 1) // channels_per_pixel
    
    if needed_pixels > len(available_indices):
        raise ValueError(f"Data too large. Need {needed_pixels} pixels, but only {len(available_indices)} available.")
        
    # 4. Embed
    piece_idx = 0
    for idx in available_indices:
        if piece_idx >= len(pieces):
            break
            
        pixel = pixels[idx]
        # Convert to list so we can mutate
        new_channels = list(pixel) if isinstance(pixel, (tuple, list)) else [pixel]

        for c_idx in range(len(new_channels)):
            if piece_idx < len(pieces):
                # Bit manipulation: Clear LSBs and OR the piece
                # Faster than string formatting:
                val = new_channels[c_idx]
                mask = (1 << piece_size) - 1
                val = (val >> piece_size << piece_size) | int(pieces[piece_idx], 2)
                
                new_channels[c_idx] = val
                piece_idx += 1

        # Put back in the original list (save memory/time)
        pixels[idx] = tuple(new_channels) if isinstance(pixel, (tuple, list)) else new_channels[0]
        
    # 5. Create new image
    new_img = Image.new(img.mode, img.size)
    new_img.putdata(pixels)
    return new_img

def extract_data(img: Image.Image, seed: int, target_start_index: int = target_start_index, piece_size: int = 2) -> bytes:
    pixels = list(img.get_flattened_data())
    pixels = cast(list[tuple[int, ...]], pixels)
    
    # Header is 32 bits for data_len
    header_bits_count = 32
    header_piece_count = header_bits_count // piece_size
    
    available_indices = list(range(target_start_index, len(pixels)))
    rng = random.Random(seed)
    rng.shuffle(available_indices)
    
    # 1. Extract Header
    header_pieces = []
    idx_iter = iter(available_indices)
    while len(header_pieces) < header_piece_count:
        idx = next(idx_iter)
        pixel = pixels[idx]
        pixel = pixel if not isinstance(pixel, int) else [pixel]

        for channel in pixel:
            if len(header_pieces) < header_piece_count:
                binary_channel = format(channel, '08b')
                header_pieces.append(binary_channel[-piece_size:])
    
    header_binary = "".join(header_pieces)
    header_bytes = bytes(int(header_binary[i:i+8], 2) for i in range(0, header_bits_count, 8))
    data_len = struct.unpack(">I", header_bytes)[0]
    
    # 2. Extract Data
    data_piece_count = data_len // piece_size
    # data_pieces = []
    # Continue from where header left off if needed, but header might end mid-pixel
    # Let's restart extraction but with the knowledge of how many total pieces we need
    total_piece_count = header_piece_count + data_piece_count
    
    # Restart to be safe and simple
    pieces = []
    for idx in available_indices:
        if len(pieces) >= total_piece_count:
            break
        pixel = pixels[idx]
        pixel = pixel if not isinstance(pixel, int) else [pixel]

        for channel in pixel:
            if len(pieces) < total_piece_count:
                binary_channel = format(channel, '08b')
                pieces.append(binary_channel[-piece_size:])
    
    # Data is after header
    data_binary = "".join(pieces[header_piece_count:])
    # Convert binary string to bytes
    data_bytes = bytes(int(data_binary[i:i+8], 2) for i in range(0, len(data_binary), 8))
    return data_bytes
