$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $projectRoot '.env'
$template = Join-Path $projectRoot '.env.example'

if (!(Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath $template -Destination $envFile
}

Write-Host 'Configure Gmail SMTP for WebTestCase.'
Write-Host 'Use a 16-character Gmail App Password, not your regular Google password.' -ForegroundColor Yellow
$email = (Read-Host 'Gmail address').Trim().ToLowerInvariant()
if ($email -notmatch '^[^\s@]+@gmail\.com$') {
    throw 'Enter a valid Gmail address.'
}

$securePassword = Read-Host 'Gmail App Password' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $appPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer) -replace '\s', ''
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
if ([string]::IsNullOrWhiteSpace($appPassword)) {
    throw 'App Password cannot be empty.'
}

$lines = @(Get-Content -LiteralPath $envFile)
function Set-EnvValue([string]$Name, [string]$Value) {
    $script:lines = @($script:lines | Where-Object { $_ -notmatch ('^' + [regex]::Escape($Name) + '=') })
    $script:lines += "$Name=$Value"
}

Set-EnvValue 'EMAIL_HOST' 'smtp.gmail.com'
Set-EnvValue 'EMAIL_PORT' '587'
Set-EnvValue 'EMAIL_USE_TLS' 'true'
Set-EnvValue 'EMAIL_HOST_USER' $email
Set-EnvValue 'EMAIL_HOST_PASSWORD' $appPassword
Set-EnvValue 'DEFAULT_FROM_EMAIL' "WebTestCase <$email>"
Set-EnvValue 'EMAIL_VERIFICATION_REQUIRED' 'true'

Set-Content -LiteralPath $envFile -Value $lines -Encoding utf8
Remove-Variable appPassword -ErrorAction SilentlyContinue
Write-Host 'Gmail SMTP saved locally in .env. The secret was not printed.' -ForegroundColor Green
Write-Host 'Restart backend with: .\scripts\restart-backend.ps1'
