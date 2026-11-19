$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$runtime = Join-Path $projectRoot '.local'
$pidFile = Join-Path $runtime 'backend.pid'

if (Test-Path -LiteralPath $pidFile) {
    $processId = (Get-Content -LiteralPath $pidFile -Raw).Trim()
    if ($processId -match '^\d+$' -and (Get-Process -Id $processId -ErrorAction SilentlyContinue)) {
        Stop-Process -Id $processId -Force
    }
    Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue
}

$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
$process = Start-Process -FilePath $python -ArgumentList @('manage.py', 'runserver', '127.0.0.1:8000', '--noreload') -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime 'backend.out.log') -RedirectStandardError (Join-Path $runtime 'backend.err.log')
Set-Content -LiteralPath $pidFile -Value $process.Id
Write-Host 'Backend restarted. Check: http://127.0.0.1:8000/api/health/' -ForegroundColor Green
