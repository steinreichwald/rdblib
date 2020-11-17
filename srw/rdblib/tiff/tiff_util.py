

from srw.rdblib.utils import pad_bytes


__all__ = ['pad_tiff_bytes']

def pad_tiff_bytes(value, length):
    data = b''
    if isinstance(value, str):
        # TIFF specification (page 15): "8-bit byte that contains a 7-bit ASCII code"
        data = value.encode('ASCII')
    else:
        data += value
    padded_data = pad_bytes(data, length=length, pad_right=True, pad_byte=b'\x00')
    # TIFF specification (page 15): "the last byte must be NUL (binary zero)"
    assert (padded_data[-1:] == b'\x00')
    return padded_data

