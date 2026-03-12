$ErrorActionPreference = "Stop"
$UserDir = $env:USERPROFILE
$FreeliDir = "$UserDir\.freeli"
$BinDir = "$FreeliDir\bin"

Write-Host "Installing Freeli..." -ForegroundColor Cyan

# Create Dirs
New-Item -ItemType Directory -Force -Path $FreeliDir | Out-Null
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null

$Repo = "https://raw.githubusercontent.com/Kelushael/free-li/master"

# Download Source
Write-Host "Downloading core files..."
try {
    Invoke-WebRequest -Uri "$Repo/freeli.py" -OutFile "$FreeliDir\freeli.py"
} catch {
    Write-Error "Failed to download freeli.py. Check internet connection."
    exit 1
}

# Create Wrapper
$BatContent = "@echo off`npython ""$FreeliDir\freeli.py"" %*"
Set-Content -Path "$BinDir\freeli.cmd" -Value $BatContent

# Add to Path
$UserPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($UserPath -notlike "*$BinDir*") {
    Write-Host "Adding $BinDir to PATH..."
    [Environment]::SetEnvironmentVariable("Path", "$UserPath;$BinDir", "User")
    Write-Host "NOTE: You may need to restart your terminal for PATH changes to take effect." -ForegroundColor Yellow
}

Write-Host "`n[SUCCESS] Freeli installed!" -ForegroundColor Green
Write-Host "Type 'freeli' to start."
