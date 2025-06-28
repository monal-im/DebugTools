# DebugTools
Some tools for reading [Monal IM](https://github.com/monal-im/Monal/) crash reports, logfiles etc.

1. Monal Crash Analyzer
2. Monal Log Viewer
3. Monal Mobile Crash Analyzer (Android)
4. Monal Mobile Log Viewer (Android)

## Usage
The Crash Analyzer and Log Viewer are published on the releaes page as binaries for Windows, Linux and macOS.
You can clone/download the repository and run the main scripts of each of these two tools under `src/LogViewer.py`
and `src/CrashAnalyzer.py`. See the requirements.txt for needed libraries (mainly qt).

To use the mobile tools, just download the `*.apk` files of the Mobile Crash Analyzer or Mobile Log Viewer from the releases page
and just install them on your Android-based phone.

# Aux Tools
The Crash Analyzer is capable of resymbolicating all `<redacted>` symbols in stacktraces contained within crash reports.
To do so, it needs a sqlite database containing symbols for the system libs of the iOS/macOS version the crash report comes from.

The `tools/symbol_extractor` directory contains a C++ tool capable of generating such a sqlite database.
See [the readme](tools/symbol_extractor/README.md) in [that directory](tools/symbol_extractor/) for all the details.

I tried to add a sample database to this repository, but unfortunately the compressed sqlite database containing symbols
for 2 iOS versions is about 300MiB in size and github only allows 100MiB of git LFS files.

**So: Just contact me, if you need such a "precompiled" sqlite database.**