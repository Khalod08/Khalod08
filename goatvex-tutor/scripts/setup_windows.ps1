# GoatVex setup for Windows 10/11.
#
# Run from the goatvex-tutor folder in PowerShell:
#     powershell -ExecutionPolicy Bypass -File scripts\setup_windows.ps1
#
# It checks each piece, explains what it is, and asks before installing anything.
# Safe to run again: anything already installed is skipped.

# "Continue": native tools (py, winget) write normal messages to stderr; we check exit codes instead.
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

function Say($msg)  { Write-Host "`n== $msg" -ForegroundColor Cyan }
function Ok($msg)   { Write-Host "   OK  $msg" -ForegroundColor Green }
function Info($msg) { Write-Host "   $msg" }
function Ask($q)    { (Read-Host "   $q [y/n]") -match '^[Yy]' }
function Refresh-Path {
    # winget installs update PATH for NEW terminals; pull the new PATH into this one too.
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}
function Have($cmd) { [bool](Get-Command $cmd -ErrorAction SilentlyContinue) }

if (-not (Have "winget")) {
    Write-Host "winget (the Windows package manager) was not found. Install 'App Installer' from the Microsoft Store, then re-run." -ForegroundColor Red
    exit 1
}

# ---------------------------------------------------------------- Python
Say "Python 3.12 or 3.11 (runs the math engine and Manim)"
$py = $null
foreach ($v in @("3.12", "3.11")) {  # not 3.13+: manim-voiceover needs audioop, removed in 3.13
    if ((Have "py") -and (& py "-$v" -c "print('ok')" 2>$null) -eq "ok") { $py = @("py", "-$v"); break }
}
if ($py) { Ok "found Python $($py[1].TrimStart('-'))" }
elseif (Ask "Python 3.12 not found. Install it with winget? (Other versions can stay installed.)") {
    winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
    Refresh-Path
    $py = @("py", "-3.12")
} else { Write-Host "Python is required. Stopping." -ForegroundColor Red; exit 1 }

# ---------------------------------------------------------------- FFmpeg
Say "FFmpeg (Manim uses it to encode video and mix in the voiceover)"
if (Have "ffmpeg") { Ok "ffmpeg is on PATH" }
elseif (Ask "FFmpeg not found. Install it with winget (Gyan.FFmpeg)?") {
    winget install -e --id Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
    Refresh-Path
}

# ---------------------------------------------------------------- MiKTeX
Say "MiKTeX (a LaTeX distribution: Manim's MathTex uses it to typeset equations)"
if (Have "latex") { Ok "latex is on PATH" }
elseif (Ask "LaTeX not found. Install MiKTeX with winget? (about 1 GB with packages)") {
    winget install -e --id MiKTeX.MiKTeX --accept-source-agreements --accept-package-agreements
    Refresh-Path
}
if (Have "initexmf") {
    # Let MiKTeX fetch missing LaTeX packages automatically instead of popping up dialogs mid-render.
    & initexmf --set-config-value "[MPM]AutoInstall=1" 2>$null
    Ok "MiKTeX set to install missing packages automatically"
}

# ---------------------------------------------------------------- venv + packages
Say "Virtual environment (.venv) — keeps GoatVex's Python packages separate from everything else"
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    & $py[0] $py[1] -m venv .venv
    Ok "created .venv"
} else { Ok ".venv already exists" }

Say "Python packages: manim, manim-voiceover, edge-tts, sympy, numpy, mpmath, pymupdf, pytest"
& .venv\Scripts\python.exe -m pip install --upgrade pip
& .venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { Write-Host "pip install failed - see the messages above." -ForegroundColor Red; exit 1 }
Ok "packages installed"

# ---------------------------------------------------------------- checks
Say "Checking everything (including the Edge TTS voice, which needs internet)"
& .venv\Scripts\python.exe scripts\check_env.py --voice

Say "Running the math verification tests"
& .venv\Scripts\python.exe -m pytest -q

Say "Rendering the 5-second test video (LaTeX equation + voice line)"
& .venv\Scripts\manim.exe -ql setup_check\hello_goatvex.py HelloGoatVex
$video = Get-ChildItem -Recurse media\videos\hello_goatvex -Filter HelloGoatVex.mp4 | Select-Object -First 1
if ($video) {
    Ok "rendered $($video.FullName)"
    if (Ask "Play it now?") { Start-Process $video.FullName }
}

Write-Host "`nDone. Each time you open a new terminal, activate the environment with:" -ForegroundColor Cyan
Write-Host "    .venv\Scripts\Activate.ps1"
