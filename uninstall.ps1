$ErrorActionPreference = 'Stop'
$root = [IO.Path]::GetFullPath($PSScriptRoot)
$failed = $false

if ([IO.File]::GetAttributes($root) -band [IO.FileAttributes]::ReparsePoint) {
    Write-Host 'Open the original app folder before running the uninstaller.'
    exit 1
}

if (-not (Test-Path -LiteralPath (Join-Path $root 'Start_mimo-myanmar.bat') -PathType Leaf)) {
    Write-Host 'Run the uninstaller from the mimo-myanmar folder.'
    exit 1
}

Write-Host 'mimo-myanmar uninstaller'
Write-Host "App folder: $root"
Write-Host 'This permanently removes .venv, model, and __pycache__ from this folder.'
Write-Host 'The shared Python installation, exported audio, and project files are kept.'
Write-Host 'Close mimo-myanmar before continuing.'
if ((Read-Host 'Type REMOVE to continue') -cne 'REMOVE') {
    Write-Host 'Uninstall cancelled.'
    exit 0
}

function Assert-NoReparsePoints([IO.DirectoryInfo] $Directory) {
    if ($Directory.Attributes -band [IO.FileAttributes]::ReparsePoint) {
        throw "Linked directory found: $($Directory.FullName)"
    }
    foreach ($child in $Directory.EnumerateFileSystemInfos()) {
        if ($child.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Linked item found: $($child.FullName)"
        }
        if ($child -is [IO.DirectoryInfo]) {
            Assert-NoReparsePoints $child
        }
    }
}

foreach ($name in '.venv', 'model', '__pycache__') {
    $path = [IO.Path]::GetFullPath((Join-Path $root $name))
    try {
        if ([IO.Path]::GetDirectoryName($path) -ne $root.TrimEnd('\')) {
            throw 'The target is outside the app folder.'
        }
        try {
            $directory = Get-Item -LiteralPath $path -Force
        } catch [System.Management.Automation.ItemNotFoundException] {
            Write-Host "Already absent: $name"
            continue
        }
        if ($directory -isnot [IO.DirectoryInfo]) {
            throw 'The target is not a directory.'
        }
        Assert-NoReparsePoints $directory
        Remove-Item -LiteralPath $path -Recurse -Force
        Write-Host "Removed: $name"
    } catch {
        $failed = $true
        Write-Host "Could not remove ${name}: $($_.Exception.Message)"
    }
}

if ($failed) {
    Write-Host 'Close the app and any open setup windows, then run the uninstaller again.'
    exit 1
}
Write-Host 'Cleanup complete. You can delete the app folder if you no longer need it.'
