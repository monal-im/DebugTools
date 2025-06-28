import io
import struct

from .randread_context import randread

# see https://stackoverflow.com/a/47080739
def is_gzip_file(fp):
    with randread(fp, 2, offset=0, whence=io.SEEK_SET) as data:
        return data == b'\x1f\x8b'

# see https://code.activestate.com/lists/python-list/245777
def gzip_file_size(fp):
    with randread(fp, offset=-4, whence=io.SEEK_END) as data:
        return struct.unpack('<I', data)[0]

def is_lzma_file(fp):
    with randread(fp, 6, offset=0, whence=io.SEEK_SET) as data:
        return data == b'\xFD\x37\x7A\x58\x5A\x00'