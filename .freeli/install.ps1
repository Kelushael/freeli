$ErrorActionPreference = "Stop"

$RepoBase = "https://raw.githubusercontent.com/Kelushael/freeli/master"
$InstallDir = "$env:USERPROFILE\.freeli"
$BinDir = "$InstallDir\bin"

Write-Host "--- Installing Freeli (Windows) ---" -ForegroundColor Cyan

# 1. Check Python
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    Write-Host "Python not found! Please install Python 3.10+ from python.org" -ForegroundColor Red
    exit 1
}

# 2. Setup Dirs
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

# 3. Download Source
Write-Host "Downloading core files..."
try {
    Invoke-WebRequest -Uri "$RepoBase/.freeli/freeli.py" -OutFile "$InstallDir\freeli.py"
    Invoke-WebRequest -Uri "$RepoBase/gguf_wrapper.py" -OutFile "$InstallDir\gguf_wrapper.py"
} catch {
    Write-Error "Download failed. Check internet connection."
    exit 1
}

# 4. Install Libs
Write-Host "Installing Python libraries..."
pip install requests prompt_toolkit colorama rich httpx

# 5. Create Wrapper (freeli.cmd)
$CmdContent = "@echo off`npython ""$InstallDir\freeli.py"" %*"
Set-Content -Path "$BinDir\freeli.cmd" -Value $CmdContent

# 6. Create Wrapper (freeli.ps1 for PowerShell native execution)
$PsContent = "python `"$InstallDir\freeli.py`" `$args"
Set-Content -Path "$BinDir\freeli.ps1" -Value $PsContent

# 7. Add to Path
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    Write-Host "Adding $BinDir to PATH..."
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    Write-Host "NOTE: Please restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
}

Write-Host "`n------------------------------------------------"
Write-Host "[SUCCESS] Freeli installed!" -ForegroundColor Green
Write-Host "Type 'freeli' to start."
Write-Host "------------------------------------------------"
