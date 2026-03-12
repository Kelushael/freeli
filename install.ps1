# Freeli Installer (Windows)
# Usage: Invoke-WebRequest -Uri https://raw.githubusercontent.com/Kelushael/freeli/master/install.ps1 -OutFile install.ps1; .\install.ps1

Write-Host "Installing Freeli Sovereign Client..." -ForegroundColor Cyan

# 1. Check Python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is required. Please install it from python.org or Microsoft Store." -ForegroundColor Red
    exit
}

# 2. Setup Directories
$FreeliHome = "$env:USERPROFILE\.freeli"
New-Item -ItemType Directory -Force -Path "$FreeliHome\bin" | Out-Null
New-Item -ItemType Directory -Force -Path "$FreeliHome\config" | Out-Null
New-Item -ItemType Directory -Force -Path "$FreeliHome\workspace" | Out-Null

# 3. Download Freeli CLI
$RepoUrl = "https://raw.githubusercontent.com/Kelushael/freeli/master/.freeli/freeli.py"
Write-Host "Downloading Freeli from $RepoUrl..."
Invoke-WebRequest -Uri $RepoUrl -OutFile "$FreeliHome\bin\freeli.py"

# 4. Create Wrapper (freeli.bat)
$Wrapper = "$FreeliHome\bin\freeli.bat"
$WrapperContent = "@echo off`r`npython `"$FreeliHome\bin\freeli.py`" %*"
Set-Content -Path $Wrapper -Value $WrapperContent
Write-Host "Wrapper created at $Wrapper"

# 5. Add to PATH (User Environment Variable)
$CurrentPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($CurrentPath -notlike "*$FreeliHome\bin*") {
    $NewPath = "$CurrentPath;$FreeliHome\bin"
    [Environment]::SetEnvironmentVariable("Path", $NewPath, "User")
    Write-Host "Added $FreeliHome\bin to User Path." -ForegroundColor Green
} else {
    Write-Host "Freeli bin is already in Path."
}

# 6. Pre-configure Remote (Auto-Connect to Axis Mundi)
$ConfigFile = "$FreeliHome\config\config.json"
if (-not (Test-Path $ConfigFile)) {
    $ConfigContent = '{
    "remote": {
        "url": "http://187.77.208.28:8000",
        "ssh_host": "root@187.77.208.28"
    }
}'
    Set-Content -Path $ConfigFile -Value $ConfigContent
    Write-Host "Configured default remote: http://187.77.208.28:8000" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "===========================================" -ForegroundColor Green
Write-Host "  Freeli Installed Successfully!" -ForegroundColor Green
Write-Host "  Restart your terminal and type: freeli" -ForegroundColor Yellow
Write-Host "===========================================" -ForegroundColor Green
