# UNC Path Converter

**Version 1.1.0**

A small PowerShell WinForms utility that converts mapped drive paths (e.g. `Z:\Folder`) into their underlying UNC paths (e.g. `\\Server\Share\Folder`).

## Features

- Accepts paths pasted from Explorer's Copy as path (quotes handled automatically)
- Converts mapped network drives to UNC using Win32_LogicalDisk
- Copies the result to clipboard automatically
- Open UNC location directly in Explorer (paths with spaces are supported)

## Run

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\20261024-UNCPathConverter.ps1
```

## Compile to EXE

```powershell
Install-Module PS2EXE -Scope CurrentUser
Invoke-PS2EXE -InputFile .\20261024-UNCPathConverter.ps1 -OutputFile .\20261024-UNCPathConverter.exe -NoConsole
```

## Changelog

### 1.1.0 (2026-10-24)

- Fixed: "Open UNC" now quotes the path, so folders with spaces open in the correct location.
- Fixed: the drive letter is replaced with plain string handling instead of a regex replace, so a `$` in a share name (such as an admin share) is never misread.
- Fixed: Run and Compile commands in this README now use the actual script file name.
- Added: the version number is shown in the window title.

### 1.0.0 (2026-07-07)

- Initial release.

## Author

Jay
