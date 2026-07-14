# Fallback for participants without a Jira site: create the workshop tickets as
# GitHub issues on YOUR FORK.
#
#   .\scripts\seed-github-issues.ps1
#
# Reads every docs/workshop/exercises/{exercise,stretch}-*.md, creates one issue
# per file, and writes my-tickets.md mapping exercises to your issue numbers.

$ErrorActionPreference = "Stop"

$REPO_ROOT = Split-Path -Parent $PSScriptRoot
$EXERCISES_DIR = Join-Path $REPO_ROOT "docs\workshop\exercises"
$MAPPING_FILE = Join-Path $REPO_ROOT "my-tickets.md"

# Check for gh command
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Error "gh not found - install from https://cli.github.com"
    exit 1
}

# Check gh authentication
try {
    gh auth status 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Error "gh not authenticated - run: gh auth login"
        exit 1
    }
} catch {
    Write-Error "gh not authenticated - run: gh auth login"
    exit 1
}

# Get current repo from origin remote
Push-Location $REPO_ROOT
try {
    $originUrl = (git remote get-url origin) | Out-String
    $originUrl = $originUrl.Trim()
    # Extract owner/repo from URL (handles both https and git formats)
    if ($originUrl -match 'github\.com[:/](.+?)(?:\.git)?$') {
        $repo = $matches[1]
    } else {
        Write-Error "Could not parse GitHub repo from origin URL: $originUrl"
        exit 1
    }
} finally {
    Pop-Location
}

if ($repo -eq "scholtenmartijn/schiphol-cop-workshop") {
    Write-Error "origin is the upstream workshop repo - fork it first: gh repo fork --clone"
    exit 1
}

# Find exercise files
$files = @()
$files += Get-ChildItem -Path $EXERCISES_DIR -Filter "exercise-*.md" -ErrorAction SilentlyContinue
$files += Get-ChildItem -Path $EXERCISES_DIR -Filter "stretch-*.md" -ErrorAction SilentlyContinue

if ($files.Count -eq 0) {
    Write-Error "no exercise files found in $EXERCISES_DIR"
    exit 1
}

# Display files and prompt
Write-Host "About to create $($files.Count) issues on ${repo}:"
foreach ($f in $files) {
    $firstLine = Get-Content $f.FullName -First 1
    $title = $firstLine -replace '^# ', ''
    Write-Host "  - $title"
}

$answer = Read-Host 'Continue? [y/N]'
if ($answer -notmatch '^[yY](es)?$') {
    Write-Host "aborted."
    exit 0
}

# Enable issues and create labels
gh repo edit $repo --enable-issues 2>&1 | Out-Null
gh label create bug --repo $repo --color d73a4a 2>&1 | Out-Null
gh label create feature --repo $repo --color a2eeef 2>&1 | Out-Null

# Create mapping file header
$mappingContent = @"
# My workshop tickets

Created $(Get-Date -Format yyyy-MM-dd) as GitHub issues on ``${repo}``.

| Exercise | Issue | Summary |
|----------|-------|---------
"@

# Process each file
$issueLines = @()
foreach ($f in $files) {
    $content = Get-Content $f.FullName
    $firstLine = $content[0]
    $title = $firstLine -replace '^# ', ''
    $summary = ($title -split ' - ', 2)[1]
    $exercise = ($title -split ' - ', 2)[0]
    
    # Find type line
    $typeLine = $content | Where-Object { $_ -match '^\*\*Type:\*\*' } | Select-Object -First 1
    $type = if ($typeLine) {
        ($typeLine -replace '^\*\*Type:\*\* *', '').Trim()
    } else {
        ""
    }
    
    $label = if ($type -eq "Bug") { "bug" } else { "feature" }
    
    Write-Host "Creating [$label] $summary ..."
    
    # Get body (everything except first line)
    $body = ($content | Select-Object -Skip 1) -join "`n"
    $tempFile = [System.IO.Path]::GetTempFileName()
    Set-Content -Path $tempFile -Value $body -NoNewline
    
    try {
        $url = (gh issue create --repo $repo --title $summary --label $label --body-file $tempFile) | Out-String
        $url = $url.Trim()
        $number = "#" + ($url -split '/')[-1]
        Write-Host "  -> $number"
        $issueLines += "| $exercise | $number | $summary |"
    } finally {
        Remove-Item $tempFile -ErrorAction SilentlyContinue
    }
}

# Write mapping file
$mappingContent + "`n" + ($issueLines -join "`n") | Set-Content -Path $MAPPING_FILE

Write-Host ""
Write-Host "Done. Your exercise → issue mapping is in my-tickets.md (gitignored)."
Write-Host "Where a ticket says 'acli …', use the gh equivalent (gh issue view/comment)."
