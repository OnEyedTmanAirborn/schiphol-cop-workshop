<#
.SYNOPSIS
Create the workshop tickets in YOUR OWN Jira project via acli.

.DESCRIPTION
Reads every docs/workshop/exercises/{exercise,stretch}-*.md, creates one work
item per file, and writes my-tickets.md mapping exercises to your ticket keys.

.PARAMETER Project
The Jira project key (e.g., OPS)

.EXAMPLE
.\scripts\seed-jira.ps1 -Project OPS
#>

param(
    [Parameter(Mandatory=$true)]
    [string]$Project
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$ExercisesDir = Join-Path $RepoRoot "docs\workshop\exercises"
$MappingFile = Join-Path $RepoRoot "my-tickets.md"

# Check if acli is available
try {
    $null = Get-Command acli -ErrorAction Stop
} catch {
    Write-Error "acli not found - see docs/workshop/00-setup.md"
    exit 1
}

# Check if acli is authenticated
try {
    $null = acli jira auth status 2>&1
    if ($LASTEXITCODE -ne 0) { throw }
} catch {
    Write-Error "acli not authenticated - run: acli jira auth login"
    exit 1
}

# Find all exercise and stretch files
$files = @()
$files += Get-ChildItem -Path $ExercisesDir -Filter "exercise-*.md" -ErrorAction SilentlyContinue
$files += Get-ChildItem -Path $ExercisesDir -Filter "stretch-*.md" -ErrorAction SilentlyContinue

if ($files.Count -eq 0) {
    Write-Error "no exercise files found in $ExercisesDir"
    exit 1
}

# Show preview and ask for confirmation
Write-Host "About to create $($files.Count) work items in Jira project '$Project':"
foreach ($f in $files) {
    $firstLine = Get-Content $f.FullName -First 1
    $title = $firstLine -replace '^# ', ''
    Write-Host "  - $title"
}

$answer = Read-Host 'Continue? [y/N]'
if ($answer -notmatch '^(y|Y|yes|YES)$') {
    Write-Host "aborted."
    exit 0
}

# Initialize mapping file
$mappingContent = @"
# My workshop tickets

Created $(Get-Date -Format 'yyyy-MM-dd') in Jira project ``$Project``.

| Exercise | Ticket | Summary |
|----------|--------|---------|
"@
Set-Content -Path $MappingFile -Value $mappingContent

# Process each file
foreach ($f in $files) {
    $content = Get-Content $f.FullName -Raw
    $lines = Get-Content $f.FullName
    
    $firstLine = $lines[0]
    $title = $firstLine -replace '^# ', ''
    $summary = ($title -split ' - ', 2)[1]
    $exercise = ($title -split ' - ', 2)[0]
    
    # Extract type
    $typeLine = $lines | Where-Object { $_ -match '^\*\*Type:\*\*' } | Select-Object -First 1
    $type = "Task"
    if ($typeLine) {
        $type = ($typeLine -replace '^\*\*Type:\*\* *', '').Trim()
    }
    
    # Extract description (everything after first line)
    $description = ($lines | Select-Object -Skip 1) -join "`n"
    
    Write-Host "Creating [$type] $summary ..."
    
    # Try to create with specified type
    $output = acli jira workitem create --project $Project --type $type --summary $summary --description $description 2>&1
    
    if ($LASTEXITCODE -ne 0) {
        # Try again with Task type
        Write-Host "  (work item type '$type' not available - trying as Task)"
        $output = acli jira workitem create --project $Project --type "Task" --summary $summary --description $description 2>&1
        
        if ($LASTEXITCODE -ne 0) {
            Write-Host "  FAILED: $output" -ForegroundColor Red
            Add-Content -Path $MappingFile -Value "| $exercise | (failed) | $summary |"
            continue
        }
    }
    
    # Extract ticket key from output
    $key = "(created - key not parsed)"
    if ($output -match "($Project-\d+)") {
        $key = $matches[1]
    }
    
    Write-Host "  -> $key"
    Add-Content -Path $MappingFile -Value "| $exercise | $key | $summary |"
}

Write-Host ""
Write-Host "Done. Your exercise → ticket mapping is in my-tickets.md (gitignored)."
Write-Host "Check them with: acli jira workitem search --jql `"project = $Project ORDER BY created ASC`""
