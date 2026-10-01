# UNC Path Converter

Version 1.0.0

A small cross-platform desktop app that turns paths on mapped network drives into their full
UNC paths, so you can share a link that works on anyone's machine.

```
Z:\Reports\Q3 summary.xlsx   ->   \\fileserver\projects\Reports\Q3 summary.xlsx
```

## Features
- **Auto-detects mappings**
  - Windows: every mapped drive letter, including remembered-but-disconnected ones
  - Linux: CIFS/SMB mounts from `/proc/mounts`, plus GNOME Files (GVFS) `smb-share` paths
  - macOS: SMB shares mounted under `/Volumes`
- **Manual mappings** for anything not detected (e.g. converting a colleague's `Z:` path on a
  machine where `Z:` isn't mapped). Manual entries override detected ones and are saved.
- Converts many paths at once (one per line); results update as you type
- Accepts paths with forward or back slashes and surrounding quotes
- Output as UNC (`\\server\share\path`), `smb://` URL, or `file://` URL
- Copy all results with one click
- Command-line mode for scripts

## Run
Requires Python 3.10+ with Tkinter. No other dependencies.

```
python3 uncpath.py
```

- **Windows / macOS**: the python.org installer includes Tkinter.
- **Linux (Debian/Ubuntu)**: `sudo apt install python3-tk`

### Command line
Pass one or more paths to print their UNC paths instead of opening the window:

```
python3 uncpath.py "Z:\Reports\Q3 summary.xlsx" "P:\docs"
```

Paths that can't be converted are reported on stderr, and the exit code is 1.

## Where manual mappings are saved
| OS | File |
|---|---|
| Windows | `%APPDATA%\UNC Path Converter\mappings.json` |
| macOS | `~/Library/Application Support/UNC Path Converter/mappings.json` |
| Linux | `~/.config/UNC Path Converter/mappings.json` |

## Build a double-click desktop app
See [BUILDING.md](BUILDING.md) for step-by-step instructions for Windows, macOS and Linux,
including a Linux app-menu launcher. Quick version (run on each target OS):

```
pip install pyinstaller
pyinstaller --onefile --windowed --name UNCPathConverter uncpath.py
```

## Changelog

### 1.0.0
- Initial release
