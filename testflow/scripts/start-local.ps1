$ErrorActionPreference='Stop'
$env:PYTHONIOENCODING='utf-8'
$projectRoot=Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $projectRoot
$python=Join-Path $projectRoot '.venv\Scripts\python.exe'
$runtime=Join-Path $projectRoot '.local'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null
& $python scripts/bootstrap.py
if($LASTEXITCODE){throw 'Не вдалося підготувати середовище.'}
& $python manage.py migrate --noinput
if($LASTEXITCODE){throw 'Не вдалося застосувати міграції. Перевірте PostgreSQL і DATABASE_URL.'}
$seedConfig=Join-Path $projectRoot '.env'
if((Test-Path -LiteralPath $seedConfig) -and ((Get-Content -LiteralPath $seedConfig -Raw) -match '(?m)^DEMO_SEED_ON_START\s*=\s*true\s*$')){
    & $python manage.py seed_demo
    & $python manage.py seed_quality_demo
    if($LASTEXITCODE){throw 'Не вдалося підготувати демонстраційні дані.'}
}
$mailpit=Join-Path $runtime 'mailpit\mailpit.exe'
if(!(Test-Path -LiteralPath $mailpit)){
    Invoke-WebRequest 'https://github.com/axllent/mailpit/releases/download/v1.27.0/mailpit-windows-amd64.zip' -OutFile (Join-Path $runtime 'mailpit.zip')
    Expand-Archive -LiteralPath (Join-Path $runtime 'mailpit.zip') -DestinationPath (Join-Path $runtime 'mailpit') -Force
}
function Start-ServiceProcess($Name,$Executable,$Arguments,$Directory,$Port){
    $listener=Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if($listener){
        $owner=Get-CimInstance Win32_Process -Filter "ProcessId=$($listener.OwningProcess)"
        $pidFile=Join-Path $runtime "$Name.pid"
        $knownProcess=$false
        if(Test-Path -LiteralPath $pidFile){$knownProcess=([int](Get-Content -LiteralPath $pidFile -Raw).Trim() -eq $listener.OwningProcess)}
        $projectProcess=($owner.CommandLine -and $owner.CommandLine.Contains($projectRoot)) -or ($owner.ExecutablePath -and $owner.ExecutablePath.StartsWith($projectRoot))
        # Django and Vite can be started from the project directory while using a global runtime,
        # so their command line may not contain the absolute project path.
        $matchingService=($Name -eq 'backend' -and $owner.CommandLine -match "manage\.py\s+runserver\s+127\.0\.0\.1:$Port") -or ($Name -eq 'frontend' -and $owner.CommandLine -match 'vite')
        if(!$knownProcess -and !$projectProcess -and !$matchingService){throw "Порт $Port зайнятий іншим застосунком. Його не зупинено."}
        Set-Content -LiteralPath $pidFile -Value $listener.OwningProcess
        Write-Host "$Name уже працює.";return
    }
    $process=Start-Process -FilePath $Executable -ArgumentList $Arguments -WorkingDirectory $Directory -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtime "$Name.out.log") -RedirectStandardError (Join-Path $runtime "$Name.err.log")
    Set-Content -LiteralPath (Join-Path $runtime "$Name.pid") -Value $process.Id
}
if(!(Get-NetTCPConnection -LocalPort 11025 -State Listen -ErrorAction SilentlyContinue)){
    Start-ServiceProcess 'mailpit' $mailpit @('--listen','127.0.0.1:18025','--smtp','127.0.0.1:11025','--database',('"'+(Join-Path $runtime 'mailpit.db')+'"')) $projectRoot 18025
}else{Write-Host 'Використовується вже запущений локальний SMTP на 11025.'}
Start-ServiceProcess 'backend' $python @(('"'+(Join-Path $projectRoot 'manage.py')+'"'),'runserver','127.0.0.1:8000','--noreload') $projectRoot 8000
Start-ServiceProcess 'frontend' (Get-Command node.exe).Source @(('"'+(Join-Path $projectRoot 'frontend\node_modules\vite\bin\vite.js')+'"'),'--host','127.0.0.1') (Join-Path $projectRoot 'frontend') 5173
Write-Host 'WebTestCase: http://localhost:5173 | Mailpit: http://localhost:18025'
