#!/usr/bin/env python3

import sqlite3
import re
import argparse
from pathlib import Path

def extract_crash_metadata(crash: str) -> dict:
    os_type, os_version, build_number, cpu_arch = None, None, None, None

    for line in crash.splitlines():
        line = line.strip()

        # Example: "Version:             1046 (6.4.13)"
        if line.startswith("Version:"):
            match = re.match(r"Version:\s+(\d+)\s+\(([\d\.]+)\)", line)
            if match:
                app_build_number, app_version = match.groups()
        # Example: "OS Version:          iOS 18.6.2 (22G100)"
        elif line.startswith("OS Version:"):
            match = re.match(r"OS Version:\s+(\w+)\s+([\d\.]+)\s+\(([^)]+)\)", line)
            if match:
                os_type, os_version, build_number = match.groups()
        # Example: "Code Type:           ARM-64 (Native)"
        elif line.startswith("Code Type:"):
            match = re.search(r"Code Type:\s+([A-Za-z0-9\-]+)", line)
            if match:
                arch = match.group(1).lower()
                # Map Apple-style arch names to canonical strings
                cpu_arch_map = {
                    "arm-64": "arm64e",
                    "arm64": "arm64",
                    "x86-64": "x86_64"
                }
                cpu_arch = cpu_arch_map.get(arch, arch)

    return {
        "osType": os_type,
        "osVersion": os_version,
        "buildNumber": build_number,
        "cpuArch": cpu_arch,
        "appBuildNumber": app_build_number,
        "appVersion": app_version,
    }

def replace_redacted_in_crash_log(crash: str, sqlite_db_path: str) -> str:
    metadata = extract_crash_metadata(crash)
    conn = sqlite3.connect(sqlite_db_path)
    cursor = conn.cursor()
    
    # Match stack frame lines, matches:
    # 7   Foundation                    	0x0000000199bc8500 0x199b11000 + 750848 (<redacted> + 212)
    frame_regex = re.compile(
        r"""^(?P<index>\s*\d+\s+)                                   # thread frame index
            (?P<lib>\S+)\s+                                         # library name
            0x(?P<absaddr>[0-9a-fA-F]+)\s+                          # absolute address
            0x(?P<baseaddr>[0-9a-fA-F]+)\s+\+\s+(?P<offset>\d+)\s+  # base + offset
            \((?P<symbol>.+)\s+\+\s+(?P<delta>\d+)\)$               # (symbol + N)
        """,
        re.VERBOSE | re.MULTILINE
    )

    def replacer(match):
        offset = int(match.group("offset")) - int(match.group("delta"))
        lib = match.group("lib")
        query = """
            SELECT symbols.name
            FROM symbols
            JOIN files ON symbols.file_id = files.id
            JOIN builds ON files.build_id = builds.id
            WHERE symbols.address = ?
                AND files.name = ?
                AND builds.build = ?
                AND builds.arch = ?
            LIMIT 1;
        """
        # print("Searching for %s, %s, %s, %s" % (offset, lib, metadata["buildNumber"], metadata["cpuArch"]))
        cursor.execute(query, (offset, lib, metadata["appBuildNumber"], metadata["cpuArch"]))
        result = cursor.fetchone()
        if result:
            return match.group(0).replace(match.group("symbol"), result[0])
        else:
            cursor.execute(query, (offset, lib, metadata["buildNumber"], metadata["cpuArch"]))
            result = cursor.fetchone()
            if result:
                return match.group(0).replace(match.group("symbol"), result[0])
        return match.group(0)

    retval = frame_regex.sub(replacer, crash)
    conn.close()
    return retval


parser = argparse.ArgumentParser(description="Replace '<redacted>' symbols in Apple crash logs using symbols.db")
parser.add_argument("crash_log", help="Path to Apple crash log (*.crash)")
parser.add_argument("symbols_db", help="Path to symbols.db")
args = parser.parse_args()

crash_log_path = Path(args.crash_log)
symbols_db_path = Path(args.symbols_db)
if not crash_log_path.exists():
    print(f"Error: Crash log file not found: {crash_log_path}", file=sys.stderr)
    sys.exit(1)
if not symbols_db_path.exists():
    print(f"Warning: symbols.db file not found: {symbols_db_path}", file=sys.stderr)

with open(crash_log_path, 'r') as t:
    symbolicated_crash = replace_redacted_in_crash_log(t.read(), symbols_db_path)
    print(symbolicated_crash)
