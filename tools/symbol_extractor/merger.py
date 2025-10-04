#!/usr/bin/env python3

import sqlite3
import argparse
import os
import sys

def merge_databases(main_db_path, source_db_path):
    if not os.path.exists(main_db_path):
        print(f"Error: Main database '{main_db_path}' does not exist.")
        sys.exit(1)
    if not os.path.exists(source_db_path):
        print(f"Error: Source database '{source_db_path}' does not exist.")
        sys.exit(1)

    main_conn = sqlite3.connect(main_db_path)
    main_cursor = main_conn.cursor()
    main_cursor.execute(f"ATTACH DATABASE ? AS other;", (source_db_path,))

    main_cursor.execute("PRAGMA foreign_keys = ON;")
    main_cursor.execute("PRAGMA other.foreign_keys = ON;")

    build_id_map = {}
    file_id_map = {}

    print("Merging builds...")
    rows = [row for row in main_cursor.execute("SELECT id, build, arch, version FROM other.builds")]
    for row in rows:
        other_id, build, arch, version = row
        
        main_cursor.execute("""
            SELECT id FROM builds WHERE build = ? AND arch = ?
        """, (build, arch))
        pre_existing = main_cursor.fetchone()
        if not pre_existing:
            print(f"Adding new: {build=}, {arch=}")
        
        main_cursor.execute("""
            INSERT OR IGNORE INTO builds (build, arch, version)
            VALUES (?, ?, ?)
        """, (build, arch, version))
        main_cursor.execute("""
            SELECT id FROM builds WHERE build = ? AND arch = ?
        """, (build, arch))
        new_id = main_cursor.fetchone()[0]
        build_id_map[other_id] = new_id

    print("Merging files...")
    rows = [row for row in main_cursor.execute("SELECT id, build_id, name, path FROM other.files")]
    for row in rows:
        other_id, old_build_id, name, path = row
        new_build_id = build_id_map[old_build_id]
        main_cursor.execute("""
            INSERT OR IGNORE INTO files (build_id, name, path)
            VALUES (?, ?, ?)
        """, (new_build_id, name, path))
        main_cursor.execute("""
            SELECT id FROM files WHERE build_id = ? AND name = ?
        """, (new_build_id, name))
        new_id = main_cursor.fetchone()[0]
        file_id_map[other_id] = new_id

    print("Merging symbols...")
    rows = [row for row in main_cursor.execute("SELECT file_id, address, name FROM other.symbols")]
    for row in rows:
        old_file_id, address, name = row
        new_file_id = file_id_map.get(old_file_id)
        if new_file_id:
            main_cursor.execute("""
                INSERT OR IGNORE INTO symbols (file_id, address, name)
                VALUES (?, ?, ?)
            """, (new_file_id, address, name))

    main_conn.commit()
    main_cursor.execute("DETACH DATABASE other")
    main_conn.close()

parser = argparse.ArgumentParser(description="Merge one SQLite symbols database into another.")
parser.add_argument("main_db", help="Path to the main (destination) database.")
parser.add_argument("source_db", help="Path to the source database to be merged in.")

args = parser.parse_args()
merge_databases(args.main_db, args.source_db)
