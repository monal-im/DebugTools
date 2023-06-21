import os
import pathlib
import json
import struct
import gzip
import io
import logging

from utils import randread

logger = logging.getLogger(__name__)
PREFIX_FORMAT = "!L"        # constant defining the struct.{pack,unpack} format of our length prefix

class Rawlog:
    def __init__(self, to_load=None, **kwargs):
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
        with gzip.GzipFile(fileobj=fp, mode="rb") if self._is_gzip_file(fp) else fp as fp:
            while True:
                # Unwraps the rawlog file and strips down the values
                json_read_len = fp.read(prefix_length)
                if len(json_read_len) != prefix_length:
                    break
                json_read_len = struct.unpack(PREFIX_FORMAT, json_read_len)[0]
                json_bytes = fp.read(json_read_len)
                if len(json_bytes) != json_read_len:
                    raise Exception("Rawlog file corrupt!")
                entry = json.loads(str(json_bytes, "UTF-8"))
                readsize += json_read_len + prefix_length
                
                if custom_load_callback != None:
                    entry = custom_load_callback(entry)
                if not entry:
                    continue
                self.data.append(entry)
                
                if progress_callback != None:
                    # the callback returns True if it wants to cancel the loading
                    if progress_callback(readsize, filesize) == True:
                        self.clear()
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
            entry_num += 1
            
            if not entry:
                continue
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
    
    def export_fp(self, fp, compressed, *, progress_callback=None, custom_store_callback=None):
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
            
            if not entry:
                continue
            fp.write(bytes("%s\n" % entry["formattedMessage"], "UTF-8"))
            
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
