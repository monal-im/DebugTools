import re
import gzip
import base64
import pathlib
import logging

logger = logging.getLogger(__name__)
PART_SEPARATOR_REGEX = "-------- d049d576-9bf0-47dd-839f-dee6b07c1df9 -------- (.*) -------- d049d576-9bf0-47dd-839f-dee6b07c1df9 --------"
PART_FILETYPE_REGEX = "^.*\((.*)\)$"

class CrashReport:
    def __init__(self, filename=None):
        super().__init__()
        self.clear()
        if filename != None:
            self.load(filename)
    
    def __getitem__(self, key):
        return self.parts[key]
    
    def __setitem__(self, key, value):
        self.parts[key] = value
    
    def __delitem__(self, key):
        del self.parts[key]
    
    def __len__(self):
        return len(self.parts)
    
    def clear(self):
        self.parts = []
    
    def load(self, filename):
        logger.debug("Loading crash report from '%s'..." % filename)
        self.clear()
        # catch exceptions to clear half read data and then rethrow them to be handled by the caller
        try:
            if self._is_gzip_file(filename):
                logger.debug("'%s' is gzip compressed" % filename)
            else:
                logger.debug("'%s' is uncompressed" % filename)
            with gzip.open(filename, "rb") if self._is_gzip_file(filename) else open(filename, "rb") as fp:
                parts = re.split(PART_SEPARATOR_REGEX, fp.read().decode("utf-8"))
                first = True
                for entry in parts:
                    entry = entry.strip()
                    # skip empty lines at the beginning of our file
                    if first and entry == "":
                        continue
                    if first:
                        name = entry
                    else:
                        parttype = re.search(PART_FILETYPE_REGEX, name)
                        if parttype != None:
                            parttype = parttype.group(1)
                        if len(entry) > 0:
                            self.parts.append({
                                "name": name,
                                "type": parttype,
                                "data": self._convertRawData(entry, parttype),
                            })
                        name = None
                    first = not first
        except:
            logger.exception("Exception while loading report!")
            self.clear()
            raise       # rethrow to handle this in upper layers
        logger.debug("Parts loaded: %s" % str([entry["name"] for entry in self.parts]))
    
    def export_part(self, index, filename):
        if index not in range(len(self.parts)):
            raise Exception("Invalid part index: %d" % index)
        open_mode = "w"+("t" if isinstance(self.parts[index]["data"], str) else "b")
        logger.debug("Exporting %s %s data to '%s'..." % ("compressed " if pathlib.Path(filename).suffix == ".gz" else "uncompressed", self.parts[index]["name"], filename))
        with gzip.open(filename, open_mode) if pathlib.Path(filename).suffix == ".gz" else open(filename, open_mode) as fp:
            fp.write(self.parts[index]["data"])
        logger.debug("Export succeeded...")
    
    def export_all(self, dirname):
        for index in range(len(self.parts)):
            self.export_part(index, pathlib.Path(dirname) / ("report%s" % self.parts[index]["type"]))
    
    def _convertRawData(self, data, parttype="*.txt"):
        if parttype in ("*.txt", "*.crash", "*.json"):
            return data
        if parttype in ("*.rawlog", "*.rawlog.gz"):
            return base64.b64decode(data)
        raise Exception("Unknown parttype: '%s'!" % str(parttype))
    
    # see https://stackoverflow.com/a/47080739
    def _is_gzip_file(self, filename):
        with open(filename, 'rb') as test_f:
            return test_f.read(2) == b'\x1f\x8b'
