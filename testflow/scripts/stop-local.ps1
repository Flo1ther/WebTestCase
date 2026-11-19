$ErrorActionPreference='Stop'
$projectRoot=Split-Path $PSScriptRoot -Parent
foreach($name in @('frontend','backend','mailpit')){
    $file=Join-Path $projectRoot ".local\$name.pid"
    if(Test-Path -LiteralPath $file){
        $serviceId=[int](Get-Content -LiteralPath $file)
        $process=Get-CimInstance Win32_Process -Filter "ProcessId=$serviceId"
        if($process -and $process.CommandLine.Contains($projectRoot)){Stop-Process -Id $serviceId}
        Remove-Item -LiteralPath $file
    }
}
Write-Host 'Процеси цього проєкту зупинено. PostgreSQL і дані збережено.'
