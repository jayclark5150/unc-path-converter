"""Translate paths on mapped drives / mounted SMB shares into UNC paths. No GUI code here."""

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote, unquote

APP_NAME = "UNC Path Converter"

DRIVE_RE = re.compile(r"^([A-Za-z]):(?:[\\/]+(.*))?$", re.S)
# GNOME/GVFS mounts, e.g. /run/user/1000/gvfs/smb-share:server=nas,share=data/docs
GVFS_RE = re.compile(r"^/run/user/\d+/gvfs/smb-share:([^/]*)(?:/(.*))?$")
SMB_FSTYPES = {"cifs", "smb3", "smbfs"}

FORMATS = {
    "UNC  (\\\\server\\share\\path)": "unc",
    "smb:// URL": "smb",
    "file:// URL": "file",
}


# ---------- Normalisation ----------

def clean_input(path: str) -> str:
    path = path.strip()
    if len(path) >= 2 and path[0] == path[-1] and path[0] in "\"'":
        path = path[1:-1].strip()
    return path


def normalize_unc(target: str) -> str:
    """Accept \\\\server\\share, //server/share or smb://[user@]server/share; return \\\\server\\share."""
    target = clean_input(target)
    if target.lower().startswith("smb://"):
        target = unquote(target[6:])
    target = target.replace("/", "\\").strip("\\")
    host, _, rest = target.partition("\\")
    host = host.rpartition("@")[2]  # drop any user@ prefix
    if not host or not rest:
        raise ValueError(f"Not a valid network path (need server and share): {target!r}")
    return "\\\\" + host + "\\" + rest.strip("\\")


def normalize_local(local: str) -> str:
    """'z', 'Z:', 'z:\\' -> 'Z:'; mount points lose trailing slashes."""
    local = clean_input(local)
    m = re.fullmatch(r"([A-Za-z]):?[\\/]*", local)
    if m:
        return m.group(1).upper() + ":"
    if not local.startswith("/"):
        raise ValueError(f"Local side must be a drive letter or an absolute mount path: {local!r}")
    return local.rstrip("/") or "/"


def _join(unc: str, rest: str | None) -> str:
    rest = (rest or "").replace("/", "\\").strip("\\")
    return f"{unc}\\{rest}" if rest else unc


# ---------- Conversion ----------

def to_unc(path: str, mappings: dict[str, str]) -> str:
    """Convert one path. `mappings` maps 'Z:' or '/mnt/share' -> '\\\\server\\share'. Raises ValueError."""
    path = clean_input(path)
    if not path:
        raise ValueError("Empty path")

    if path.startswith(("\\\\", "//")) or path.lower().startswith("smb://"):
        return normalize_unc(path)

    m = DRIVE_RE.match(path)
    if m:
        drive = m.group(1).upper() + ":"
        if drive not in mappings:
            raise ValueError(f"{drive} is not a mapped network drive")
        return _join(mappings[drive], m.group(2))

    m = GVFS_RE.match(path)
    if m:
        params = dict(p.split("=", 1) for p in m.group(1).split(",") if "=" in p)
        if "server" in params and "share" in params:
            return _join(f"\\\\{unquote(params['server'])}\\{unquote(params['share'])}", m.group(2))

    # Longest matching mount point wins.
    mounts = sorted((k for k in mappings if k.startswith("/")), key=len, reverse=True)
    for mount in mounts:
        if path == mount or path.startswith(mount.rstrip("/") + "/"):
            return _join(mappings[mount], path[len(mount):])

    raise ValueError("Not on a mapped drive or network share")


def format_unc(unc: str, fmt: str) -> str:
    if fmt == "unc":
        return unc
    url_path = quote(unc[2:].replace("\\", "/"), safe="/")
    return f"{fmt}://{url_path}"


# ---------- Detecting mappings ----------

def detect_windows_drives() -> dict[str, str]:
    import ctypes
    from ctypes import wintypes

    mpr = ctypes.WinDLL("mpr")
    get_conn = mpr.WNetGetConnectionW
    get_conn.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    get_conn.restype = wintypes.DWORD
    ERROR_CONNECTION_UNAVAIL = 1201  # remembered mapping, currently disconnected

    found = {}
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        drive = letter + ":"
        buf = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(len(buf))
        if get_conn(drive, buf, ctypes.byref(size)) in (0, ERROR_CONNECTION_UNAVAIL) and buf.value:
            try:
                found[drive] = normalize_unc(buf.value)
            except ValueError:
                pass
    return found


def parse_proc_mounts(text: str) -> dict[str, str]:
    found = {}
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 3 or parts[2] not in SMB_FSTYPES:
            continue
        # /proc/mounts escapes spaces etc. as octal, e.g. \040
        device, mount = (re.sub(r"\\(\d{3})", lambda m: chr(int(m.group(1), 8)), p) for p in parts[:2])
        try:
            found[normalize_local(mount)] = normalize_unc(device)
        except ValueError:
            pass
    return found


def parse_mac_mount(text: str) -> dict[str, str]:
    found = {}
    for line in text.splitlines():
        m = re.match(r"^(//\S+) on (.+) \((smbfs|cifs)\b", line)
        if m:
            try:
                found[normalize_local(m.group(2))] = normalize_unc(unquote(m.group(1)))
            except ValueError:
                pass
    return found


def detect_mappings() -> dict[str, str]:
    """Best-effort auto-detection for the current OS. Never raises."""
    try:
        if sys.platform == "win32":
            return detect_windows_drives()
        if sys.platform == "darwin":
            out = subprocess.run(["mount"], capture_output=True, text=True, timeout=5).stdout
            return parse_mac_mount(out)
        return parse_proc_mounts(Path("/proc/mounts").read_text())
    except Exception:
        return {}


# ---------- Saved manual mappings ----------

def config_path() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / APP_NAME / "mappings.json"


def load_manual() -> dict[str, str]:
    try:
        data = json.loads(config_path().read_text(encoding="utf-8"))
        return {normalize_local(k): normalize_unc(v) for k, v in data.items()}
    except (OSError, ValueError, AttributeError):
        return {}


def save_manual(mappings: dict[str, str]) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mappings, indent=2, sort_keys=True), encoding="utf-8")
