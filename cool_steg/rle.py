def encode_rle(data: list[int]) -> str:
    if not data:
        return ""
    
    result = []
    current_val = data[0]
    count = 0
    for val in data:
        if val == current_val:
            count += 1
        else:
            result.append(count)
            current_val = val
            count = 1
    result.append(count)

    # Encode: 1-9 as digit, 10+ as letter (a=10, b=11, ...)
    return "".join(str(x) if x < 10 else chr(ord('a') + x - 10) for x in result)

def decode_rle(encoded_data: str) -> list[int]:
    runs = [int(c) if c.isdigit() else ord(c) - ord('a') + 10 for c in encoded_data]
    
    result = []
    for idx, count in enumerate(runs):
        color = 0 if idx % 2 == 0 else 1
        result.extend([color] * count)
    return result

def step_2_compression(rle_string: str) -> str:
    """
    Compresses an RLE string by grouping repeating characters.
    Uses Uppercase suffixes for counts to avoid collision with Step 1 letters.
    Example: '11111' -> '1E', '22' -> '2B', '7' -> '7'
    """
    if not rle_string:
        return ""
    
    result = []
    current_char = rle_string[0]
    count = 0
    
    for char in rle_string:
        if char == current_char:
            count += 1
        else:
            result.append(_encode_char_run(current_char, count))
            current_char = char
            count = 1
    result.append(_encode_char_run(current_char, count))
    return "".join(result)

def _encode_char_run(char: str, count: int) -> str:
    if count < 2:
        return char
    
    s = [char]
    temp_count = count
    while temp_count > 26:
        s.append('Z')
        temp_count -= 26
    if temp_count > 0:
        s.append(chr(ord('A') + temp_count - 1))
    return "".join(s)

def step_2_decompression(encoded_data: str) -> str:
    """
    Decompresses the Step 2 string back into the Step 1 RLE string.
    """
    if not encoded_data:
        return ""
    
    result = []
    i = 0
    while i < len(encoded_data):
        char = encoded_data[i]
        i += 1
        
        count = 0
        has_suffix = False
        while i < len(encoded_data) and encoded_data[i].isupper():
            count += ord(encoded_data[i]) - ord('A') + 1
            i += 1
            has_suffix = True
        
        if not has_suffix:
            count = 1
            
        result.append(char * count)
    return "".join(result)

def convert_bytes_to_rle_suitable(data: bytes) -> list[int]:
    bits = [int(bit) for byte in data for bit in f'{byte:08b}']
    return bits

def convert_rle_suitable_to_bytes(data: list[int]) -> bytes:
    return bytes([int("".join(map(str, data[i:i+8])), 2) 
                  for i in range(0, len(data), 8)])