# Pipeline completo: PyInstaller -> Inno Setup
# Uso: .\scripts\build_installer.ps1

$ErrorActionPreference = "Stop"

Write-Host "[1/2] Compilando o executavel com PyInstaller..."
& .venv\Scripts\python.exe -m PyInstaller rift_pilot.spec --noconfirm
if ($LASTEXITCODE -ne 0) {
    Write-Host "PyInstaller falhou."
    exit 1
}

Write-Host ""
Write-Host "[2/2] Gerando o instalador com Inno Setup..."

$candidateInnoPaths = @(
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    "C:\Program Files\Inno Setup 6\ISCC.exe",
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
)

$inno = $candidateInnoPaths | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $inno) {
    Write-Host "Inno Setup 6 nao encontrado nos caminhos:"
    $candidateInnoPaths | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
    Write-Host "Instale com: winget install JRSoftware.InnoSetup"
    Write-Host "Ou baixe de https://jrsoftware.org/isdl.php"
    exit 1
}

& $inno setup.iss
if ($LASTEXITCODE -ne 0) {
    Write-Host "Inno Setup falhou."
    exit 1
}

Write-Host ""
Write-Host "OK - executavel:  dist\rift-pilot.exe"
Write-Host "OK - instalador: dist\installer\RiftPilot-Setup-0.1.0-beta.exe"
