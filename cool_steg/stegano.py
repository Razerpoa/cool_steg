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

def embed_data(img: Image.Image, data_bytes: bytes, seed: int, target_start_index: int = target_start_index, piece_size: int = 2) -> Image.Image:
    pixels = list(img.get_flattened_data())
    pixels = cast(list[tuple[int, ...]], pixels)
    # mode = img.mode
    # print(pixels)

    # Header: data_len (32 bits)
    data_len = len(data_bytes) * 8
    header = struct.pack(">I", data_len)
    
    full_data = header + data_bytes
    data_in_binary = "".join(format(byte, '08b') for byte in full_data)
    pieces = chop_to_pieces(data_in_binary, piece_size)
    
    # Generate and shuffle indices
    available_indices = [
        i for i in range(target_start_index, len(pixels))
        if pixels[i][3] >= 255 // 2
    ]
    
    rng = random.Random(seed)
    rng.shuffle(available_indices)
    
    pixels_needed = (len(pieces) + 2) // 3
    if pixels_needed > len(available_indices):
        raise ValueError("Data too large for the image.")
        
    selected_indices = available_indices[:pixels_needed]
    
    modified_pixels_map = {}
    piece_idx = 0
    
    for idx in selected_indices:
        if piece_idx >= len(pieces):
            break
            
        pixel = pixels[idx]
        new_channels = list(pixel)
        for channel_idx in range(3):
            if piece_idx < len(pieces):
                binary_channel = format(new_channels[channel_idx], '08b')
                modified = binary_channel[:-piece_size] + pieces[piece_idx]
                new_channels[channel_idx] = int(modified, 2)
                piece_idx += 1
        
        modified_pixels_map[idx] = tuple(new_channels)
        
    # Reconstruct all pixels
    new_pixels = [modified_pixels_map.get(i, pixels[i]) for i in range(len(pixels))]
            
    new_img = Image.new(img.mode, img.size)
    new_img.putdata(new_pixels)
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
        for channel in pixel:
            if len(pieces) < total_piece_count:
                binary_channel = format(channel, '08b')
                pieces.append(binary_channel[-piece_size:])
    
    # Data is after header
    data_binary = "".join(pieces[header_piece_count:])
    # Convert binary string to bytes
    data_bytes = bytes(int(data_binary[i:i+8], 2) for i in range(0, len(data_binary), 8))
    return data_bytes
