param(
    [Parameter(Mandatory = $true)]
    [string]$AppDir
)

$appDirPath = (Resolve-Path -LiteralPath $AppDir).Path
$targetPath = Join-Path $appDirPath "Start Cost Markup Tool (FOR DAD).bat"
$iconPath = Join-Path $appDirPath "assets\statement-mark.ico"
$shortcutPath = Join-Path $appDirPath "Statement Markup Tool (FOR DAD).lnk"

if (-not (Test-Path -LiteralPath $targetPath)) {
    throw "Launcher was not found: $targetPath"
}

if (-not (Test-Path -LiteralPath $iconPath)) {
    throw "Icon was not found: $iconPath"
}

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $targetPath
$shortcut.WorkingDirectory = $appDirPath
$shortcut.IconLocation = "$iconPath,0"
$shortcut.Description = "Launch the Statement Markup Tool (FOR DAD)"
$shortcut.Save()
