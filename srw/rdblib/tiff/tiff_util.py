

__all__ = ['pad_bytes']

def pad_bytes(value, length):
    data = b''
    if isinstance(value, str):
        # TIFF specification (page 15): "8-bit byte that contains a 7-bit ASCII code"
        data = value.encode('ASCII')
    else:
        data += value
    # TIFF specification (page 15): "the last byte must be NUL (binary zero)"
    if not data.endswith(b'\x00'):
        data += b'\x00'
    if len(data) < length:
        nr_fill_bytes = length - len(data)
        data += (b'\x00' * nr_fill_bytes)
    return data

