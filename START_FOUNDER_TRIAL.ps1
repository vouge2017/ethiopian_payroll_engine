param([string]$PythonPath = 'D:\payroll-work-2026-09-30\ci-lock-env\Scripts\python.exe')

$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw 'Provide -PythonPath pointing to a Python environment with requirements-lock.txt installed.'
}
$trialScript = Join-Path $PSScriptRoot 'scripts\founder_trial.py'
& $PythonPath -X utf8 $trialScript init
if ($LASTEXITCODE -ne 0) { throw 'Trial setup failed. Existing data has been preserved.' }
& $PythonPath -X utf8 $trialScript serve
if ($LASTEXITCODE -ne 0) { throw 'Trial server stopped with an error. Existing data has been preserved.' }
