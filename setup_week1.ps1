# Week-1 finisher: verify env, run the extractor, init git, commit, and push (if gh authed).
# Run: powershell -ExecutionPolicy Bypass -File setup_week1.ps1
$ErrorActionPreference = "Continue"
$envRoot = "$env:USERPROFILE\miniconda3\envs\budget"
$env:Path = "$envRoot;$envRoot\Scripts;$envRoot\Library\bin;$env:Path"
$repo = Join-Path $env:USERPROFILE "Downloads\budget-guard"
Set-Location $repo

Write-Host "=== 1) verify env ===" -ForegroundColor Cyan
python -c "import pandas,numpy,sklearn,lightgbm,scipy,matplotlib,huggingface_hub; print('ENV_OK pandas',pandas.__version__,'sklearn',sklearn.__version__)"

Write-Host "=== 2) run extractor on smoke sample ===" -ForegroundColor Cyan
python budget_guard\extract.py

Write-Host "=== 3) git init + commit ===" -ForegroundColor Cyan
git --version
if (-not (Test-Path ".git")) { git init -b main }
git add -A
if (-not (git config user.name)) { git config user.name "budget-guard"; git config user.email "budget-guard@local" }
git commit -m "Week 1: offline extractor, data dictionary, plans, env setup"
git log --oneline -1

Write-Host "=== 4) push to GitHub (only if gh is authenticated) ===" -ForegroundColor Cyan
if (Get-Command gh -ErrorAction SilentlyContinue) {
    $auth = (gh auth status 2>&1 | Out-String)
    Write-Host $auth
    if ($auth -match "Logged in") {
        gh repo create budget-guard --private --source=. --remote=origin --push
    } else {
        Write-Host "GH_NOT_AUTHED -- run 'gh auth login', then:"
        Write-Host "  gh repo create budget-guard --private --source=. --remote=origin --push"
    }
} else {
    Write-Host "GH_CLI_NOT_FOUND -- create an empty private repo 'budget-guard' on github.com, then:"
    Write-Host "  git remote add origin https://github.com/<you>/budget-guard.git"
    Write-Host "  git push -u origin main"
}
