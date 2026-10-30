# printlab setup and check for Windows 11. Run in PowerShell (no admin needed):
#   powershell -ExecutionPolicy Bypass -File <printlab>\setup\win_setup.ps1
# Safe to re-run any time ("check setup"): reuses the Python and OrcaSlicer already installed,
# installs only what is missing, then builds, checks, renders and slices the fit coupon and
# compares the slice with the cloud reference.
#   -PinnedOrca  also install the tested OrcaSlicer 2.4.2 (portable, in the user folder) and use it
#                instead of an installed OrcaSlicer of another version.
param([switch]$PinnedOrca)
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$Repo  = Split-Path -Parent $PSScriptRoot
$Local = Join-Path $env:LOCALAPPDATA 'printlab'
$Venv  = Join-Path $Repo '.venv'
$Py    = Join-Path $Venv 'Scripts\python.exe'

# Same pins as setup/cloud_setup.sh; every dependency is held to the tested version by constraints.txt.
# All resolve to Windows wheels for Python 3.12-3.14 (numpy 2.5 / scipy 1.18 need 3.12+).
$Packages = @('cadquery==2.8.0', 'trimesh==5.2.0', 'pyvista==0.49.2', 'vtk==9.6.2',
              'shapely==2.2.0', 'networkx==3.7', 'scipy==1.18.1', 'rtree==1.4.1',
              'matplotlib==3.11.2', 'numpy==2.5.4')
$PyVersions = @('3.13', '3.12', '3.14')

# OrcaSlicer 2.4.2 ships Creality profile bundle 02.03.02.75: same K2 profiles as the cloud AppImage.
$OrcaZip      = 'OrcaSlicer_Windows_V2.4.2_x64_portable.zip'
$OrcaSha256   = 'FEBA3009DFB9D268779CCA5758A1A5BC3B7D0722BF8FA48D5C57340DE975D6BE'
$OrcaUrls     = @("https://github.com/SoftFever/OrcaSlicer/releases/download/v2.4.2/$OrcaZip",
                  "https://sourceforge.net/projects/orcaslicer.mirror/files/v2.4.2/$OrcaZip/download")
$OrcaProfiles = '02.03.02.75'
$PinnedDir    = Join-Path $Local 'OrcaSlicer'

# Cloud reference slice of the fit coupon plate (CLAUDE.md print log)
$RefTime  = '15m 16s'
$RefGrams = '8.19'

function Say([string]$tag, [string]$msg) { Write-Host ('printlab {0,-8} {1}' -f $tag, $msg) }

function Invoke-Checked([string]$exe, [string[]]$argv) {
    & $exe @argv
    if ($LASTEXITCODE -ne 0) { throw "$exe failed (exit $LASTEXITCODE)" }
}

function Find-Python {
    foreach ($v in $PyVersions) {
        try {
            $exe = & py "-$v" -c 'import sys; print(sys.executable)' 2>$null
            if ($LASTEXITCODE -eq 0 -and $exe) { return "$exe".Trim() }
        } catch { }
    }
    foreach ($v in $PyVersions) {
        $name = 'Python' + $v.Replace('.', '')
        foreach ($root in @((Join-Path $env:LOCALAPPDATA 'Programs\Python'), $env:ProgramFiles)) {
            $exe = Join-Path $root "$name\python.exe"
            if (Test-Path $exe) { return $exe }
        }
    }
    return $null
}

# Same search order as tools/slice_orca.py
function Find-Orca {
    foreach ($d in @($env:PRINTLAB_ORCA, $PinnedDir, (Join-Path $env:ProgramFiles 'OrcaSlicer'))) {
        if ($d -and (Test-Path (Join-Path $d 'orca-slicer.exe'))) { return $d }
    }
    return $null
}

function Get-OrcaProfiles([string]$dir) {
    $text = Get-Content -Raw -Encoding UTF8 (Join-Path $dir 'resources\profiles\Creality.json')
    if ($text -match '"version"\s*:\s*"([^"]+)"') { return $Matches[1] }
    return 'unknown'
}

function Install-PinnedOrca {
    if (Test-Path (Join-Path $PinnedDir 'orca-slicer.exe')) { return }
    New-Item -ItemType Directory -Force -Path $Local | Out-Null
    $zip = Join-Path $Local $OrcaZip
    foreach ($u in $OrcaUrls) {
        if ((Test-Path $zip) -and (Get-FileHash $zip -Algorithm SHA256).Hash -eq $OrcaSha256) { break }
        Say 'orca' "downloading $u"
        & curl.exe -fsSL --retry 3 -o $zip $u
    }
    if (-not (Test-Path $zip) -or (Get-FileHash $zip -Algorithm SHA256).Hash -ne $OrcaSha256) {
        throw "OrcaSlicer download failed or checksum mismatch ($zip)"
    }
    New-Item -ItemType Directory -Force -Path $PinnedDir | Out-Null
    Invoke-Checked 'tar.exe' @('-xf', $zip, '-C', $PinnedDir)
    Remove-Item $zip
}

function Get-Field($lines, [string]$key) {
    foreach ($l in $lines) { if ($l -match "^$key\s*:\s*(.*)$") { return $Matches[1].Trim() } }
    return ''
}

Say 'repo' $Repo
if ($Repo -match 'OneDrive') {
    Say 'WARNING' 'repo is inside OneDrive: move it (e.g. to %USERPROFILE%\printlab) so .venv and outputs do not sync'
}
if (Get-Command git -ErrorAction SilentlyContinue) { Say 'git' 'OK' } else { Say 'WARNING' 'git not found (winget install Git.Git)' }

# 1. Python 3.12-3.14 and the project venv (.venv in the repo, ignored by git)
$sysPy = Find-Python
if (-not $sysPy) {
    Say 'python' 'no Python 3.12-3.14 found: installing Python 3.13 with winget (per-user)'
    Invoke-Checked 'winget' @('install', '--id', 'Python.Python.3.13', '-e', '--scope', 'user', '--silent',
                              '--accept-package-agreements', '--accept-source-agreements')
    $sysPy = Find-Python
    if (-not $sysPy) { throw 'Python 3.13 was installed but not found: open a new PowerShell window and re-run' }
}
if (-not (Test-Path $Py)) {
    Say 'venv' "creating $Venv with $sysPy"
    Invoke-Checked $sysPy @('-m', 'venv', $Venv)
}
$pipArgs = @('-m', 'pip', 'install', '-q', '--disable-pip-version-check',
             '-c', (Join-Path $PSScriptRoot 'constraints.txt')) + $Packages
Invoke-Checked $Py $pipArgs
$pyInfo = & $Py -I -c 'import sys, cadquery, trimesh, pyvista, shapely; print(sys.version.split()[0], cadquery.__version__)'
if ($LASTEXITCODE -ne 0) { throw 'Python packages failed to import' }
Say 'python' "OK Python/CadQuery $pyInfo ($Py)"

# 2. OrcaSlicer: the installed one, or the pinned portable 2.4.2
if ($PinnedOrca) { Install-PinnedOrca }
$orca = Find-Orca
if (-not $orca) {
    Say 'orca' "no OrcaSlicer found: installing the tested 2.4.2 (portable) to $PinnedDir"
    Install-PinnedOrca
    $orca = Find-Orca
}
$orcaExe = Join-Path $orca 'orca-slicer.exe'
$orcaVer = (Get-Item $orcaExe).VersionInfo.ProductVersion
$orcaProf = Get-OrcaProfiles $orca
Say 'orca' "OK $orcaExe (version $orcaVer, Creality profiles $orcaProf)"
if ($orcaProf -ne $OrcaProfiles) {
    Say 'WARNING' "Creality profiles $orcaProf, tested set is $OrcaProfiles (OrcaSlicer 2.4.2): slices can differ."
    Say 'WARNING' 'Re-run with -PinnedOrca to use 2.4.2 alongside the installed OrcaSlicer.'
}

# 3. PrusaSlicer: fallback only, not installed here
$prusa = Join-Path $env:ProgramFiles 'Prusa3D\PrusaSlicer\prusa-slicer-console.exe'
if (Test-Path $prusa) { Say 'prusa' "OK $prusa (fallback)" } else { Say 'prusa' 'not installed (fallback only, not needed)' }

# 4. Self-test: build, check, render and slice the fit coupon in a temp folder
$t = Join-Path $env:TEMP 'printlab_selftest'
if (Test-Path $t) { Remove-Item -Recurse -Force $t }
New-Item -ItemType Directory -Path $t | Out-Null
Push-Location $Repo
try {
    $out = & $Py -I 'parts\fit_coupon\build_fit_coupon_v1.py' $t
    if ($LASTEXITCODE -ne 0 -or -not ($out -match 'OK all features built \(2 bodies')) { $out | Write-Host; throw 'self-test build failed' }
    Say 'build' 'OK fit coupon v1 (2 bodies: Rail, Slider)'

    foreach ($b in 'Rail', 'Slider') {
        $stl = Join-Path $t "FitCoupon_v1_$b.stl"
        $out = & $Py -I 'tools\check.py' $stl
        if ($LASTEXITCODE -ne 0 -or -not ($out -match 'CHECK OK')) { $out | Write-Host; throw "self-test check failed ($b)" }
        Copy-Item $stl (Join-Path $t "FitCoupon_v1_${b}_print.stl")
    }
    Say 'check' 'OK Rail, Slider'

    $rail = Join-Path $t 'FitCoupon_v1_Rail_print.stl'
    $slider = Join-Path $t 'FitCoupon_v1_Slider_print.stl'
    $null = & $Py -I 'tools\render.py' (Join-Path $t 'FitCoupon_v1') $rail $slider
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path (Join-Path $t 'FitCoupon_v1_sheet.png'))) { throw 'self-test render failed' }
    Say 'render' 'OK'

    $out = & $Py -I 'tools\slice_orca.py' PLA (Join-Path $t 'orca') $rail $slider
    if ($LASTEXITCODE -ne 0) { $out | Write-Host; throw 'self-test slice failed' }
    $time = Get-Field $out 'time'
    $grams = Get-Field $out 'grams'
    $found = Get-Field $out 'objects_found'
    $expected = Get-Field $out 'objects_expected'
    if ($found -ne $expected) { throw "self-test slice: $found of $expected objects in the G-code" }
    $gcode = (Get-ChildItem (Join-Path $t 'orca') -Filter '*.gcode' | Select-Object -First 1).FullName
    if (Select-String -Path $gcode -Pattern '^M191' -Quiet) { throw 'self-test slice: G-code waits for chamber temperature (M191)' }
    if (-not (Select-String -Path $gcode -Pattern '^START_PRINT EXTRUDER_TEMP=220 BED_TEMP=50' -Quiet)) { throw 'self-test slice: START_PRINT line missing' }
    if ($time -eq $RefTime -and $grams -eq $RefGrams) {
        Say 'slice' "OK $time / $grams g, $found of $expected objects (matches cloud reference)"
    } else {
        Say 'WARNING' "slice gives $time / $grams g; cloud reference is $RefTime / $RefGrams g (different OrcaSlicer profiles?)"
    }
    if (Get-Command git -ErrorAction SilentlyContinue) {
        & git -C $Repo diff --quiet -- profiles/creality_k2/orca
        if ($LASTEXITCODE -eq 1) { Say 'WARNING' 'K2 profiles from this OrcaSlicer differ from the repo copy (git diff profiles/creality_k2/orca)' }
    }
} finally {
    Pop-Location
}

Say 'setup' 'OK all checks passed'
Say 'python' "run tools with: $Py -I tools\<tool>.py"
