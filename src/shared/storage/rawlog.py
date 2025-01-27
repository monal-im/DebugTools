import math
import pathlib
import json
import struct
import gzip
import io
from queue import Queue
from PyQt5 import QtCore

from shared.utils import randread
try:
    from .udp_server import UdpServer
    hasLogserver = True
except ImportError:
    hasLogserver = False

import logging
logger = logging.getLogger(__name__)

PREFIX_FORMAT = "!L"        # constant defining the struct.{pack,unpack} format of our length prefix
LENGTH_BITS_NEEDED = 20

# own exception to allow the loader callback to communicate an abort condition
class AbortRawlogLoading(RuntimeError):
    pass

class Rawlog(QtCore.QObject):
    finishInsertRows = QtCore.pyqtSignal()

    def __init__(self, to_load=None, **kwargs):
        super(Rawlog, self).__init__()
        self.clear()
        if to_load == None:
            return
        elif isinstance(to_load, str):
            self.load_file(to_load, **kwargs)
        elif isinstance(to_load, bytes):
            self.load_bytes(to_load, **kwargs)
        else:
            raise Exception("Unsupported data type to load from: %s" % str(type(to_load)))
    
    # allow array access
    def __getitem__(self, key):
        return self.data[key]
    def __setitem__(self, key, value):
        self.data[key] = value
    def __delitem__(self, key):
        del self.data[key]
    def __len__(self):
        return len(self.data)
    
    def clear(self):
        self.data = []
        self.needs_custom_callbacks = False
        self.server = None
    
    def stream_rawlog(self, key, /, host="::", port=5555, custom_load_callback=None):
        if not hasLogserver:
            raise Exception("UDP logserver not importable!")
        
        logger.debug("Listening for streamed rawlog data on %s: %s" % (str(host), str(port)))
        self.clear()
        
        # force custom save/export callbacks later on if data is now loaded with a custom load callback
        if custom_load_callback != None:
            self.needs_custom_callbacks = True
        
        queue = Queue(128)
        self.server = UdpServer(queue, key, host=host, port=port)
        
        def poll(stop=False):
            if stop:
                self.server.stop()
                return False
            retval = not queue.empty()
            while not queue.empty():
                self._append_entry(queue.get(), custom_load_callback)
            return retval
        return poll
    
    def load_bytes(self, data, /, **kwargs):
        logger.debug("Loading rawlog data from bytearray...")
        with io.BytesIO(data) as fp:
            return self.load_fp(fp, **kwargs)       # returns True on success and None on abort
    
    def load_file(self, filename, /, **kwargs):
        logger.debug("Loading rawlog data from '%s'..." % filename)
        with open(filename, "rb") as fp:
            return self.load_fp(fp, **kwargs)       # returns True on success and None on abort
    
    def load_fp(self, fp, /, progress_callback=None, custom_load_callback=None):
        logger.debug("Loading rawlog data from fp: %s" % str(fp))
        self.clear()
        prefix_length = len(struct.pack(PREFIX_FORMAT, 0))
        
        # force custom save/export callbacks later on if data is now loaded with a custom load callback
        if custom_load_callback != None:
            self.needs_custom_callbacks = True
        
        # readsize and filesize are needed for progress calculation
        readsize = 0
        if self._is_gzip_file(fp):
            logger.debug("Data is gzip compressed...")
            filesize = self._gzip_file_size(fp)
        else:
            logger.debug("Data is uncompressed...")
            # calculate file size by seeking to the end
            fp.seek(0, io.SEEK_END)
            filesize = fp.tell()
            fp.seek(0, io.SEEK_SET)
        
        # now process our data
        entry = None
        old_processid = None
        with gzip.GzipFile(fileobj=fp, mode="rb") if self._is_gzip_file(fp) else fp as fp:
            try:
                while True:
                    # Unwraps the rawlog file and strips down the values
                    json_raw_read_len = fp.read(prefix_length)
                    if len(json_raw_read_len) != prefix_length:
                        break
                    json_read_len = struct.unpack(PREFIX_FORMAT, json_raw_read_len)[0]
                    if json_read_len == 0:
                        logger.debug("Length prefix at %d is zero (possibly old format), ignoring this chunk...", readsize)
                        continue
                    
                    skip_corrupted_part = False
                    # only 20 bits of our length prefix should ever be needed
                    if json_read_len > (1<<LENGTH_BITS_NEEDED):
                        logger.error("Potential corruption at %d [%d], trying to skip to next full entry..." % (readsize, fp.tell()))
                        logger.debug("Last complete entry: %s" % entry)
                        fp.seek(-prefix_length, io.SEEK_CUR)
                        skip_corrupted_part = True
                    else:
                        #logger.debug("Loading %d json bytes at %d..." % (json_read_len, fp.tell()))
                        json_bytes = fp.read(json_read_len)
                        if len(json_bytes) != json_read_len:
                            raise Exception("Rawlog file corrupt!")
                        try:
                            entry = json.loads(str(json_bytes, "UTF-8"))
                        except:
                            logger.debug("Corruption detected: failed to load json...", exc_info=True)
                        readsize += json_read_len + prefix_length
                    
                    if skip_corrupted_part:
                        # seek through the file byte by byte and search for a (prefix_length*8)-LENGTH_BITS_NEEDED bit zero sequence beginning on a byte boundary
                        search_length = math.ceil(((prefix_length*8)-LENGTH_BITS_NEEDED)/8)
                        while True:
                            potential_high_bytes = fp.read(search_length)
                            logger.debug("Searching for next length prefix at %d: %s" % (fp.tell(), potential_high_bytes))
                            if len(potential_high_bytes) != search_length:
                                logger.error("Could not find next undamaged block, EOF reached!")
                                break
                            fp.seek(-(search_length-1), io.SEEK_CUR)        # move cursor by one byte relative to our old search position
                            # only allow for the [LENGTH_BITS_NEEDED % 8] low bits to be used
                            # (these are the [LENGTH_BITS_NEEDED % 8] high bits of our [LENGTH_BITS_NEEDED] bit number mentioned above)
                            if struct.unpack("!H", potential_high_bytes)[0] <= (1<<(LENGTH_BITS_NEEDED % 8)):
                                fp.seek(-1, io.SEEK_CUR)        # move cursor back to original search position (compensate the off by one of our seek above)
                                logger.error("Found next undamaged block at %d, skipping %d bytes!" % (fp.tell(), fp.tell()-readsize))
                                message = "Corruption at %d, skipping %d bytes!" % (readsize, fp.tell()-readsize)
                                self._append_entry({
                                    "__warning": True,
                                    "__virtual": True,
                                    "__message": message,
                                }, custom_load_callback)
                                readsize = fp.tell()        # fix readsize value
                                break
                        continue        # continue reading (eof will be automatically handled by our normal code, too)
                    
                    # if the udpServer is configured -> get data from udpServer
                    if self.server != None:
                        self._append_entry(self.server.correctProcessId(old_processid, entry["_processID"]))
                    else:
                        self._append_entry(entry, custom_load_callback)
                        if "_processID" in entry:
                            old_processid = entry["_processID"]
                    
                    if progress_callback != None:
                        # the callback returns True if it wants to cancel the loading
                        if progress_callback(readsize, filesize) == True:
                            self.clear()
                            return None     # always return None on abort
            except AbortRawlogLoading:
                return None     # always return None on abort
        return True     # return True on success
    
    def store_file(self, filename, **kwargs):
        compressed = pathlib.Path(filename).suffix == ".gz"
        logger.debug("Storing %s rawlog data to '%s'..." % ("compressed " if compressed else "uncompressed", filename))
        with open(filename, "wb") as fp:
            fp.truncate()       # make sure the file is empty now
            return self.store_fp(fp, compressed, **kwargs)      # returns True on success and None on abort
    
    def store_bytes(self, data, compressed, **kwargs):
        logger.debug("Storing %s rawlog data to bytearray..." % ("compressed " if compressed else "uncompressed"))
        with io.BytesIO() as fp:
            if self.store_fp(fp, compressed, **kwargs) == True:
                return fp.getvalue()    # return bytearray on success
            return None                 # return None on abort
    
    def store_fp(self, fp, compressed, *, progress_callback=None, custom_store_callback=None):
        if self.needs_custom_callbacks and custom_store_callback == None:
            raise Exception("You need to specify a custom_store_callback because you loaded this file/data using a custom_load_callback!")
        logger.debug("Storing %s rawlog data to fp: %s" % ("compressed " if compressed else "uncompressed", str(fp)))
        entry_num = 0
        # don't use a context manager here, to not close this file pointer after writing!
        if compressed:
            fp = gzip.GzipFile(fileobj=fp, mode="wb")
        for entry in self.data:
            if custom_store_callback != None:
                entry = custom_store_callback(entry)
            entry_num += 1      # increment before checking for None
            if not entry or ("__virtual" in entry and entry["__virtual"]):
                continue
            
            # don't store this, too
            entry = entry.copy()
            del entry["__logline_index"]
            
            json_bytes = bytearray(json.dumps(entry), "UTF-8")
            size = struct.pack(PREFIX_FORMAT, len(json_bytes))
            fp.write(size + json_bytes)
            
            if progress_callback != None:
                if progress_callback(entry_num, len(self.data)) == True:
                    logger.debug("Store was aborted...")
                    return None     # always return None on abort
        logger.debug("Store completed...")
        return True     # return True on success
    
    def export_file(self, filename, **kwargs):
        compressed = pathlib.Path(filename).suffix == ".gz"
        logger.debug("Exporting %s textlog data to '%s'..." % ("compressed " if compressed else "uncompressed", filename))
        with open(filename, "wb") as fp:    # always open in binary mode, export_fp() will take care of text encoding
            fp.truncate()                   # make sure the file is empty now
            return self.export_fp(fp, compressed, **kwargs)      # returns True on success and None on abort
    
    def export_bytes(self, compressed, **kwargs):
        logger.debug("Exporting %s textlog data to bytearray..." % ("compressed " if compressed else "uncompressed"))
        fp = io.BytesIO()
        if self.export_fp(fp, compressed, **kwargs) == True:
            return fp.getvalue()    # return bytearray on success
        return None                 # return None on abort
    
    def export_fp(self, fp, compressed, *, formatter, progress_callback=None, custom_store_callback=None):
        if self.needs_custom_callbacks and custom_store_callback == None:
            raise Exception("You need to specify a custom_store_callback because you loaded this file/data using a custom_load_callback!")
        logger.debug("Exporting %s textlog data to fp: %s" % ("compressed " if compressed else "uncompressed", str(fp)))
        entry_num = 0
        # don't use a context manager here, to not close this file pointer after writing!
        if compressed:
            fp = gzip.GzipFile(fileobj=fp, mode="wb")
        for entry in self.data:
            if custom_store_callback != None:
                entry = custom_store_callback(entry)
            entry_num += 1
            if not entry or ("__virtual" in entry and entry["__virtual"]):
                continue
            fp.write(bytes("%s\n" % formatter(entry), "UTF-8"))
            
            if progress_callback != None:
                if progress_callback(entry_num, len(self.data)) == True:
                    logger.debug("Export was aborted...")
                    return None     # always return None on abort
        logger.debug("Export completed...")
        return True     # return wrapped fp on success
    
    def getCompleterList(self, custom_extract_callback=None):
        if self.needs_custom_callbacks and custom_extract_callback == None:
            raise Exception("You need to specify a custom_extract_callback because you loaded this file using a custom_load_callback!")
        if len(self.data) == 0:
            return []
        entry = self.data[0]
        if custom_extract_callback != None:
            entry = custom_extract_callback(entry)
        
        completer_list = []
        for key in entry:
            completer_list.append(str(key))
            if isinstance(entry[key], dict):
                completer_list += self._completerList_recursor([str(key)], entry[key])
        logger.debug("Extracted completer list: %s" % str(completer_list))
        return completer_list
    
    
    def _append_entry(self, entry, custom_load_callback=None):
        entry["__logline_index"] = len(self.data)
        if "__virtual" not in entry:
            entry["__virtual"] = False
        custom_entry = entry        # needed if no load_callback is used
        if custom_load_callback != None:
            custom_entry = custom_load_callback(entry)
        if not custom_entry:
            return
        self.data.append(custom_entry)
            
    def appendUdpEntries(self, entries, custom_load_callback=None):
        for entry in entries:
            self._append_entry(entry, custom_load_callback)

        self.finishInsertRows.emit()
    
    # see https://stackoverflow.com/a/47080739
    def _is_gzip_file(self, fp):
        with randread(fp, 2, offset=0, whence=io.SEEK_SET) as data:
            return data == b'\x1f\x8b'
    
    # see https://code.activestate.com/lists/python-list/245777
    def _gzip_file_size(self, fp):
        with randread(fp, offset=-4, whence=io.SEEK_END) as data:
            return struct.unpack('<I', data)[0]
    
    def _completerList_recursor(self, initial_parts, entry):
        retval = []
        for key in entry:
            parts = initial_parts.copy()
            if isinstance(key, str):
                parts.append("[\"%s\"]" % str(key))
            else:
                parts.append("[%s]" % str(key))
            if isinstance(entry[key], dict):
                retval += self._completerList_recursor(parts, entry[key])
            retval.append("".join(parts))
        return retval
