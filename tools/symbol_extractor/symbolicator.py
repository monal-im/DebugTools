import json
import sqlite3
import re
import argparse
from pathlib import Path

def replace_redacted_in_crash_log(text_log: str, resolved_json: dict) -> str:
    # Build symbol lookup table from resolved_json
    addr_to_symbol = {}

    threads = resolved_json.get("crash", {}).get("threads", [])
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
        symbol_name = addr_to_symbol.get(lib).get(absaddr)
        if symbol_name:
            return match.group(0).replace("<redacted>", symbol_name)
        return match.group(0)

    return frame_regex.sub(replacer, text_log)

def resolve_redacted_symbols(data, sqlite_db_path):
    # Connect to the SQLite database
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()

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
                    frame["symbol_name"] = result[0]
                else:
                    frame["symbol_name"] = "<unresolved>"

    conn.close()
    return data


parser = argparse.ArgumentParser(description="Replace '<redacted>' symbols in Apple crash logs using JSON crash data")
parser.add_argument("json_file", help="Path to JSON crash report (*.json)")
parser.add_argument("crash_log", help="Path to Apple crash log (*.crash)")
parser.add_argument("symbols_db", help="Path to symbols.db")
args = parser.parse_args()

json_path = Path(args.json_file)
crash_log_path = Path(args.crash_log)
symbols_db_path = Path(args.symbols_db)
if not json_path.exists():
    print(f"Error: JSON file not found: {json_path}", file=sys.stderr)
    sys.exit(1)
if not crash_log_path.exists():
    print(f"Error: Crash log file not found: {crash_log_path}", file=sys.stderr)
    sys.exit(1)
if not symbols_db_path.exists():
    print(f"Warning: symbols.db file not found: {symbols_db_path}", file=sys.stderr)

with open(json_path, 'r') as f:
    data =resolve_redacted_symbols(json.load(f), symbols_db_path)
    with open(crash_log_path, 'r') as t:
        print(replace_redacted_in_crash_log(t.read(), data))
