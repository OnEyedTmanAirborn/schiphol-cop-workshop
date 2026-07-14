# Verify the workshop prerequisites. Run from the repo root: .\scripts\check-setup.ps1

$REPO_ROOT = Split-Path -Parent $PSScriptRoot
Set-Location $REPO_ROOT

$PASS = 0
$FAIL = 0

function Ok($message) {
    Write-Host "  ✓ $message" -ForegroundColor Green
    $script:PASS++
}

function Bad($message) {
    Write-Host "  ✗ $message" -ForegroundColor Red
    $script:FAIL++
}

function Note($message) {
    Write-Host "  · $message" -ForegroundColor Yellow
}

Write-Host "schiphol-cop-workshop - setup check"
Write-Host ""

Write-Host "Python"
$python3 = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $python3) {
    $python3 = Get-Command python -ErrorAction SilentlyContinue
}

if ($python3) {
    $version = & $python3.Source -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    $versionCheck = & $python3.Source -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
    if ($LASTEXITCODE -eq 0) {
        Ok "python3 $version (>= 3.11)"
    } else {
        Bad "python3 $version found, but 3.11+ is required"
    }
} else {
    Bad "python3 not found"
}

$venvPython = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } 
              elseif (Test-Path ".venv/bin/python") { ".venv/bin/python" }
              else { $null }

if ($venvPython) {
    Ok ".venv exists"
    
    $importCheck = & $venvPython -c "import schiphol_ops" 2>&1
    if ($LASTEXITCODE -eq 0) {
        Ok "schiphol-ops installed in .venv"
    } else {
        Bad "schiphol-ops not importable - run: .venv\Scripts\activate && pip install -e `".[dev]`""
    }
    
    $pytestCheck = & $venvPython -m pytest -q 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Ok "pytest green"
    } else {
        Bad "pytest failing - that's not how this repo ships; check your install"
    }
} else {
    Bad ".venv missing - run: python3 -m venv .venv && .venv\Scripts\activate && pip install -e `".[dev]`""
}

Write-Host ""
Write-Host "Git & GitHub"
$git = Get-Command git -ErrorAction SilentlyContinue
if ($git) {
    $gitVersion = (git --version) -replace 'git version ', ''
    Ok "git $gitVersion"
} else {
    Bad "git not found"
}

$gh = Get-Command gh -ErrorAction SilentlyContinue
if ($gh) {
    $ghVersion = (gh --version | Select-Object -First 1) -replace 'gh version ', ''
    Ok "gh $ghVersion"
    
    $ghAuthCheck = gh auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Ok "gh authenticated"
    } else {
        Bad "gh not authenticated - run: gh auth login"
    }
    
    $origin = git remote get-url origin 2>$null
    if ($origin -and $origin -notmatch "scholtenmartijn/schiphol-cop-workshop") {
        Ok "working on a fork ($origin)"
    } else {
        Note "origin looks like the upstream repo - did you fork? (gh repo fork --clone)"
    }
} else {
    Bad "gh not found - install from https://cli.github.com"
}

Write-Host ""
Write-Host "Jira"
$acli = Get-Command acli -ErrorAction SilentlyContinue
if ($acli) {
    Ok "acli found"
    $acliAuthCheck = acli jira auth status 2>&1
    if ($LASTEXITCODE -eq 0) {
        Ok "acli authenticated"
    } else {
        Bad "acli not authenticated - run: acli jira auth login"
    }
} else {
    Bad "acli not found - see docs/workshop/00-setup.md (GitHub Issues fallback exists)"
}

Write-Host ""
Write-Host "Copilot"
Note "can't be checked from a script - confirm the Copilot extension is installed,"
Note "you're signed in, agent mode opens, and the extension is up to date (agent skills need a recent version)."

Write-Host ""
if ($FAIL -eq 0) {
    Write-Host "All $PASS checks passed - see you at the workshop." -ForegroundColor Green
} else {
    Write-Host "$FAIL check(s) failed ($PASS passed) - fix the ✗ lines above, docs/workshop/00-setup.md has the details." -ForegroundColor Red
    exit 1
}
