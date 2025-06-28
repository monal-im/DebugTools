import io
import re
import gzip
import json
import sqlite3
import base64
import pathlib
import logging

from shared.storage.rawlog import Rawlog
from shared.utils import Paths, randread, is_gzip_file

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
        self.resymbolicated = False
    
    def load(self, filename):
        logger.debug("Loading crash report from '%s'..." % filename)
        self.clear()
        # catch exceptions to clear half read data and then rethrow them to be handled by the caller
        try:
            with open(filename, "rb") as fp:
                if is_gzip_file(fp):
                    logger.debug("Crash report is gzip compressed")
                else:
                    logger.debug("Crash report is uncompressed")
                with gzip.GzipFile(fileobj=fp, mode="rb") if is_gzip_file(fp) else fp as fp:
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
                                    "data": self._convert_raw_data(entry, parttype),
                                })
                            name = None
                        first = not first
            
            #resymbolicate apple crashlog (must be done *after* self._convert_raw_data(), which resymbolicates the json report)
            json_data = None
            for entry in self.parts:
                if entry["type"] == "*.json":
                    json_data = entry["data"]
            if json_data is not None:
                for entry in self.parts:
                    if entry["type"] == "*.crash":
                        entry["data"] = self._replace_redacted_in_crash_log(entry["data"], json_data)
        except:
            logger.exception("Exception while loading report!")
            self.clear()
            raise       # rethrow to handle this in upper layers
        logger.debug("Parts loaded: %s" % str([entry["name"] for entry in self.parts]))
    
    def export_part(self, index, filename):
        if index not in range(len(self.parts)):
            raise Exception("Invalid part index: %d" % index)
        data = self.parts[index]["data"]
        if self.parts[index]["type"] == "*.json":
            data = json.dumps(data, indent=4)
        open_mode = "w"+("t" if isinstance(data, str) else "b")
        logger.debug("Exporting %s %s data to '%s'..." % ("compressed " if pathlib.Path(filename).suffix == ".gz" else "uncompressed", self.parts[index]["name"], filename))
        with gzip.open(filename, open_mode) if pathlib.Path(filename).suffix == ".gz" else open(filename, open_mode) as fp:
            fp.write(data)
        logger.debug("Export succeeded...")
    
    def export_all(self, dirname):
        for index in range(len(self.parts)):
            self.export_part(index, pathlib.Path(dirname) / ("report%s" % self.parts[index]["type"][1:]))
    
    def display_format(self, index, tail=None):
        if index not in range(len(self.parts)):
            raise Exception("Invalid part index: %d" % index)
        data = self.parts[index]["data"]
        if self.parts[index]["type"] == "*.json":
            data = json.dumps(self.parts[index]["data"], indent=4)
        if isinstance(data, str):
            if tail == None:
                return data
            return data[-tail:]
        elif self.parts[index]["type"] in ("*.rawlog", "*.rawlog.gz"):
            rawlog = Rawlog(self.parts[index]["data"])
            if tail == None:
                return str(rawlog.export_bytes(False, formatter=lambda entry: "%s %s" % (entry["timestamp"], entry["message"])), encoding="UTF-8")
            return str(rawlog.export_bytes(
                False, 
                formatter=lambda entry: "%s %s" % (entry["timestamp"], entry["message"]), 
                custom_store_callback = lambda entry: None if entry["__logline_index"] < len(rawlog) - tail else entry
            ), encoding="UTF-8")
        else:
            return "This part contains raw bytes (%s) and cannot be displayed!" % self.parts[index]["type"]
    
    def _convert_raw_data(self, data, parttype="*.txt"):
        if parttype in ("*.json"):
            symbols_db = pathlib.Path(Paths.get_default_data_filepath("symbols.db"))
            if symbols_db.is_file():
                return self._resolve_redacted_symbols(json.loads(data), symbols_db)
            else:
                return json.loads(data)
        if parttype in ("*.txt", "*.crash", "*.json"):
            return data
        if parttype in ("*.rawlog", "*.rawlog.gz"):
            try:
                retval = bytes.fromhex(data)
            except Exception as exb64:
                try:
                    retval = base64.b64decode(data)
                except Exception as exhex:
                    raise TypeError("Neither hex nor base64 encoding found for embedded rawlog data!\n\n%s: %s\n\n%s: %s" % (
                        str(type(exhex).__name__), str(exhex),
                        str(type(exb64).__name__), str(exb64)
                    ))
            return retval
        raise Exception("Unknown parttype: '%s'!" % str(parttype))
    
    def _replace_redacted_in_crash_log(self, apple_report, crash_json) -> str:
        addr_to_symbol = {}

        threads = crash_json.get("crash", {}).get("threads", [])
        for thread in threads:
            for frame in thread.get("backtrace", {}).get("contents", []):
                addr = frame.get("instruction_addr")
                symbol = frame.get("symbol_name")
                lib = frame.get("object_name")
                if addr is not None and symbol and symbol != "<redacted>" and lib is not None:
                    # print(f"{addr=}, {symbol=}, {lib=}")
                    addr_to_symbol[lib] = addr_to_symbol.get(lib, {})
                    addr_to_symbol[lib][addr] = symbol
        
        # Match stack frame lines, matches:
        # 7   Foundation                    	0x0000000199bc8500 0x199b11000 + 750848 (<redacted> + 212)
        frame_regex = re.compile(
            r"""^(?P<index>\s*\d+\s+)                                   # thread frame index
                (?P<lib>\S+)\s+                                         # library name
                0x(?P<absaddr>[0-9a-fA-F]+)\s+                          # absolute address
                0x(?P<baseaddr>[0-9a-fA-F]+)\s+\+\s+(?P<offset>\d+)\s+  # base + offset
                \(<redacted>\s+\+\s+(?P<delta>\d+)\)                    # (<redacted> + N)
            """,
            re.VERBOSE | re.MULTILINE
        )

        def replacer(match):
            lib = match.group("lib")
            absaddr = int(match.group("absaddr"), 16)
            symbol_name = addr_to_symbol.get(lib, {}).get(absaddr)
            if symbol_name:
                return match.group(0).replace("<redacted>", symbol_name)
            return match.group(0)

        return frame_regex.sub(replacer, apple_report)

    def _resolve_redacted_symbols(self, data, sqlite_db_path):
        # Connect to the SQLite database
        try:
            conn = sqlite3.connect(sqlite_db_path)
            cursor = conn.cursor()
        except:
            logger.warn("Could not open symbols database at '%s', not resymbolicating!" % sqlite_db_path)
            return data

        os_version = data["system"]["os_version"]

        for thread in data["crash"]["threads"]:
            if "backtrace" not in thread:
                continue
            for frame in thread["backtrace"]["contents"]:
                if frame.get("symbol_name") == "<redacted>":
                    symbol_addr = frame["symbol_addr"]
                    object_addr = frame["object_addr"]
                    object_name = frame["object_name"]

                    offset = symbol_addr - object_addr

                    query = """
                        SELECT symbols.name
                        FROM symbols
                        JOIN files ON symbols.file_id = files.id
                        JOIN builds ON files.build_id = builds.id
                        WHERE symbols.address = ?
                        AND files.name = ?
                        AND builds.build = ?
                        LIMIT 1;
                    """

                    cursor.execute(query, (offset, object_name, os_version))
                    result = cursor.fetchone()

                    if result:
                        self.resymbolicated = True
                        frame["symbol_name"] = result[0]
                    else:
                        frame["symbol_name"] = "<redacted>"

        conn.close()
        return data
