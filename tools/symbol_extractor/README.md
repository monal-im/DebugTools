# Symbol Extractor

This small C++ helper tool can be used to extract symbols from all libraries under `$HOME/Library/Developer/Xcode/iOS DeviceSupport/`.

## Preparation
The symbol_extractor will automatically demangle C++ symbols, for demangling of Swift symbols, the `swift-demangle` binary
from [www.swift.org] is needed. It can be downloaded as tarball (the Debian tarball can be found over here, for example:
[https://www.swift.org/install/linux/debian/12/]). Just extract it to some directory.

Note: Since only two files of the DSK are needed, you can copy `/usr/bin/swift-demangle` and `/usr/lib/swift/linux/libswiftCore.so`
into the directory, your `symbol_extractor` binary resides in and delete the rest of the SDK to save disk space.

## Compilation
Just compile it with g++ using the `Makefile`in this directory or any other C++20 compiler at your hand.
You'll need an install of libsqlite3 to link against.

## Usage
Usage: `symbol_extractor <directory-with-symbols> [path-to-swift-demangle-binary]`.
The `directory-with-symbols` is usually `$HOME/Library/Developer/Xcode/iOS DeviceSupport/`.
The optional `path-to-swift-demangle-binary` is probably something like `sdk/usr/bin/swift-demangle` or just `./swift-demangle`.

The symbol extractor will extract all symbols of all builds into a neat sqlite3 database where they can be
picked up later on by the CrashAnalyzer.

If you don't have the right files/versions in `iOS DeviceSupport` (or if you are on Linux without Xcode), you can download
these files from [https://github.com/CXTretar/iOS-System-Symbols-Supplement?tab=readme-ov-file]
and extract them into your `directory-with-symbols`.

### Crash Analyzer
For the Crash Analyzer being able to find the symbols.db, you'll have to import it using the corresponding menu entry.
Either as `symbols.db` or as `symbols.db.xz` (the Crash Analyzer will automatically extract it, if needed).

If the symbols database is present and symbols for the iOS version of the crash report can be found,
the Crash Analyzer will automatically resymbolicate all `<redacted>` symbols.
It will inform you with a dialog box, if resymbolication wasn't possible for all `<redacted>` symbols.

## Symbolicator
The `symbolicator.py` is a small script essentially doing the same as the Crash Analyzer.
It can be used to do a stand-alone resymbolication of a `*.crash` file, if it is also presented with a `*.json` and `symbols.db` file.
