import io
import contextlib

# context manager for random reads without moving the current file position
@contextlib.contextmanager
def randread(fp, size=-1, *, offset=0, whence=io.SEEK_SET):
    old_pos = fp.tell()
    try:
        fp.seek(offset, whence)
        yield fp.read(size)
    finally:
        fp.seek(old_pos, io.SEEK_SET)
