# UNC Path Converter
# Version 1.2.0 (2026-10-24)
#   1.2.0  New: a path that is already UNC (\\server\share\...) is passed through unchanged
#               and copied to the clipboard instead of showing "Invalid path format."
#          New: when run as administrator and a drive is not found, the status message
#               explains that elevated sessions cannot see drives mapped in a normal session.
#          New: the window is DPI aware and scales correctly at 125%, 150% and higher.
#   1.1.0  Fix: "Open UNC" now quotes the path, so folders with spaces open correctly.
#          Fix: drive letter is swapped for the UNC root with plain string handling,
#               so a "$" in a share name (for example an admin share) is never misread.
#          Version number now shown in the window title.
#   1.0.0  Initial release (2026-07-07).

$Version = '1.2.0'

cls

# Opt in to DPI awareness before any window is created. Without this, Windows
# bitmap-scales the window and it looks blurry or oversized on scaled displays.
if (-not ([System.Management.Automation.PSTypeName]'UncDpiHelper').Type) {
    Add-Type -TypeDefinition @"
using System.Runtime.InteropServices;
public static class UncDpiHelper {
    [DllImport("user32.dll")]
    public static extern bool SetProcessDPIAware();
}
"@
}
try { [void][UncDpiHelper]::SetProcessDPIAware() } catch { }

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

[System.Windows.Forms.Application]::EnableVisualStyles()

# Elevated sessions cannot see network drives mapped in the normal session
$IsElevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

$form = New-Object System.Windows.Forms.Form
$form.AutoScaleDimensions = New-Object System.Drawing.SizeF(96, 96)
$form.AutoScaleMode = [System.Windows.Forms.AutoScaleMode]::Dpi
$form.Text = "UNC Path Converter v$Version"
$form.Size = New-Object System.Drawing.Size(900,260)
$form.StartPosition = 'CenterScreen'
$form.MaximizeBox = $false

# Input Label
$lblInput = New-Object System.Windows.Forms.Label
$lblInput.Location = New-Object System.Drawing.Point(10,15)
$lblInput.Size = New-Object System.Drawing.Size(200,20)
$lblInput.Text = 'Mapped Path'
$form.Controls.Add($lblInput)

# Input TextBox
$txtInput = New-Object System.Windows.Forms.TextBox
$txtInput.Location = New-Object System.Drawing.Point(10,35)
$txtInput.Size = New-Object System.Drawing.Size(860,25)
$form.Controls.Add($txtInput)

# Convert Button
$btnConvert = New-Object System.Windows.Forms.Button
$btnConvert.Location = New-Object System.Drawing.Point(10,70)
$btnConvert.Size = New-Object System.Drawing.Size(100,30)
$btnConvert.Text = 'Convert'
$form.Controls.Add($btnConvert)

# Clear Button
$btnClear = New-Object System.Windows.Forms.Button
$btnClear.Location = New-Object System.Drawing.Point(120,70)
$btnClear.Size = New-Object System.Drawing.Size(100,30)
$btnClear.Text = 'Clear'
$form.Controls.Add($btnClear)

# Open Button
$btnOpen = New-Object System.Windows.Forms.Button
$btnOpen.Location = New-Object System.Drawing.Point(230,70)
$btnOpen.Size = New-Object System.Drawing.Size(100,30)
$btnOpen.Text = 'Open UNC'
$form.Controls.Add($btnOpen)

# Exit Button
$btnExit = New-Object System.Windows.Forms.Button
$btnExit.Location = New-Object System.Drawing.Point(340,70)
$btnExit.Size = New-Object System.Drawing.Size(100,30)
$btnExit.Text = 'Exit'
$form.Controls.Add($btnExit)

# Output Label
$lblOutput = New-Object System.Windows.Forms.Label
$lblOutput.Location = New-Object System.Drawing.Point(10,115)
$lblOutput.Size = New-Object System.Drawing.Size(200,20)
$lblOutput.Text = 'UNC Path'
$form.Controls.Add($lblOutput)

# Output TextBox
$txtOutput = New-Object System.Windows.Forms.TextBox
$txtOutput.Location = New-Object System.Drawing.Point(10,135)
$txtOutput.Size = New-Object System.Drawing.Size(860,25)
$txtOutput.ReadOnly = $true
$form.Controls.Add($txtOutput)

# Status Label
$lblStatus = New-Object System.Windows.Forms.Label
$lblStatus.Location = New-Object System.Drawing.Point(10,175)
$lblStatus.Size = New-Object System.Drawing.Size(860,20)
$lblStatus.Text = 'Ready.'
$form.Controls.Add($lblStatus)

# Convert Action
$ConvertAction = {

    try {

        $Path = $txtInput.Text

        if (-not $Path -or -not $Path.Trim()) {
            $lblStatus.Text = 'Please enter a path.'
            return
        }

        # Strip Explorer Copy-As-Path quotes and whitespace
        $Path = $Path.Trim().Trim('"')

        # Already a UNC path: pass it through unchanged
        if ($Path.StartsWith('\\')) {
            $txtOutput.Text = $Path
            $Path | Set-Clipboard
            $lblStatus.Text = 'Already a UNC path. Copied to clipboard.'
            return
        }

        if ($Path.Length -lt 2 -or $Path.Substring(1,1) -ne ':') {
            $lblStatus.Text = 'Invalid path format.'
            return
        }

        $DriveLetter = $Path.Substring(0,1).ToUpper()

        $ProviderName = (
            Get-CimInstance Win32_LogicalDisk |
            Where-Object {
                $_.DeviceID -eq "${DriveLetter}:"
            }
        ).ProviderName

        if (-not $ProviderName) {
            $Message = "Drive $DriveLetter is not a mapped network drive."
            if ($IsElevated) {
                $Message += ' (Elevated sessions cannot see drives mapped in a normal session.)'
            }
            $lblStatus.Text = $Message
            return
        }

        # Plain string handling (no regex replacement), so characters such as "$"
        # in a share name are kept exactly as they are.
        $UNC = $ProviderName.TrimEnd('\') + $Path.Substring(2)

        $txtOutput.Text = $UNC

        $UNC | Set-Clipboard

        $lblStatus.Text = 'UNC path copied to clipboard.'

    }
    catch {
        $lblStatus.Text = $_.Exception.Message
    }
}

$btnConvert.Add_Click($ConvertAction)

$txtInput.Add_KeyDown({
    if ($_.KeyCode -eq 'Enter') {
        & $ConvertAction
    }
})

$btnClear.Add_Click({

    $txtInput.Clear()
    $txtOutput.Clear()
    $lblStatus.Text = 'Ready.'

})

$btnOpen.Add_Click({

    if ($txtOutput.Text) {
        # Quote the path so folders with spaces open in the right place.
        Start-Process explorer.exe -ArgumentList ('"{0}"' -f $txtOutput.Text)
    }

})

$btnExit.Add_Click({

    $form.Close()

})

$form.Add_Shown({

    $txtInput.Focus()

})

[void]$form.ShowDialog()
