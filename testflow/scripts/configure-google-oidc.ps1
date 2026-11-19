$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $projectRoot '.env'
$template = Join-Path $projectRoot '.env.example'

if (!(Test-Path -LiteralPath $envFile)) {
    Copy-Item -LiteralPath $template -Destination $envFile
}

Write-Host 'Configure Google OpenID Connect for WebTestCase.'
Write-Host 'Create a Web application OAuth client in Google Cloud first.' -ForegroundColor Yellow
Write-Host 'Authorized redirect URIs:'
Write-Host '  http://localhost:5173/api/auth/oidc/callback/'
Write-Host '  http://127.0.0.1:5173/api/auth/oidc/callback/'
$clientId = (Read-Host 'Google OAuth Client ID').Trim()
if ([string]::IsNullOrWhiteSpace($clientId)) {
    throw 'Client ID cannot be empty.'
}

$secureSecret = Read-Host 'Google OAuth Client Secret' -AsSecureString
$pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret)
try {
    $clientSecret = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
}
finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
}
if ([string]::IsNullOrWhiteSpace($clientSecret)) {
    throw 'Client Secret cannot be empty.'
}

$lines = @(Get-Content -LiteralPath $envFile)
function Set-EnvValue([string]$Name, [string]$Value) {
    $script:lines = @($script:lines | Where-Object { $_ -notmatch ('^' + [regex]::Escape($Name) + '=') })
    $script:lines += "$Name=$Value"
}

Set-EnvValue 'GOOGLE_CLIENT_ID' $clientId
Set-EnvValue 'GOOGLE_CLIENT_SECRET' $clientSecret
Set-Content -LiteralPath $envFile -Value $lines -Encoding utf8
Remove-Variable clientSecret -ErrorAction SilentlyContinue
Write-Host 'Google OAuth settings saved locally in .env. The secret was not printed.' -ForegroundColor Green
Write-Host 'Restart backend with: .\scripts\restart-backend.ps1'
