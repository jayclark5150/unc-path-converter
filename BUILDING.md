# Building UNC Path Converter as a desktop app

UNC Path Converter is packaged with [PyInstaller](https://pyinstaller.org), which bundles
Python, Tkinter and the app into a single file. People running the result do not need Python
installed.

**Build on each operating system you want to support.** PyInstaller does not cross-compile:
a Windows `.exe` must be built on Windows, a macOS `.app` on macOS, and so on. Since mapped
drive letters are a Windows feature, the Windows build is the one most people will want.

## 1. Install Python with Tkinter

Python 3.10 or newer is required.

- **Windows / macOS**: install from [python.org](https://www.python.org/downloads/) (Tkinter is included).
- **Linux (Debian/Ubuntu)**: `sudo apt install python3-tk python3-venv`
- **Linux (Fedora)**: `sudo dnf install python3-tkinter`

## 2. Build

From the project folder.

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install pyinstaller
pyinstaller --onefile --windowed --name UNCPathConverter uncpath.py
```

**Windows (Command Prompt):**

```bat
python -m venv .venv
.venv\Scripts\activate
pip install pyinstaller
pyinstaller --onefile --windowed --name UNCPathConverter uncpath.py
```

| Option | Purpose |
|---|---|
| `--onefile` | Produce a single file |
| `--windowed` | Don't open a terminal window alongside the app |
| `--name UNCPathConverter` | Name of the output file |

## 3. Find the result

The app is written to `dist/`.

| OS | Output | Double-click notes |
|---|---|---|
| Windows | `dist\UNCPathConverter.exe` | SmartScreen may warn about an unknown publisher. Click **More info → Run anyway**. |
| macOS | `dist/UNCPathConverter.app` | The app is unsigned, so the first time right-click it and choose **Open**. Drag it to Applications. |
| Linux | `dist/UNCPathConverter` | Many file managers won't launch a program on double-click. Add a launcher (below). |

## Linux launcher

Install the binary and create a menu entry. Paste the whole block at once; don't type the
lines between `cat` and `EOF` on their own.

```bash
mkdir -p ~/.local/bin ~/.local/share/applications
cp dist/UNCPathConverter ~/.local/bin/
cat > ~/.local/share/applications/uncpathconverter.desktop <<EOF
[Desktop Entry]
Type=Application
Name=UNC Path Converter
Comment=Convert mapped drive paths to UNC paths
Exec=$HOME/.local/bin/UNCPathConverter
Terminal=false
Categories=Utility;
StartupWMClass=UNCPathConverter
EOF
```

UNC Path Converter then appears in your app menu and can be pinned to the dock.

## Command-line use

A `--windowed` build has no console, so its command-line output isn't visible on Windows.
For scripts, either run the source directly:

```
python uncpath.py "Z:\Reports\plan.docx"
```

or build a separate console version by replacing `--windowed` with `--console` and using a
different `--name` (for example `uncpath`).

## Optional

- **Custom icon**: add `--icon icon.ico` (Windows) or `--icon icon.icns` (macOS).
- **No security warnings**: requires code signing, with a code-signing certificate on Windows
  and an Apple Developer ID on macOS.
