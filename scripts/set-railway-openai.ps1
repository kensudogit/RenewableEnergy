# Requires: railway login && railway link
# Usage: .\scripts\set-railway-openai.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$envFile = Join-Path $root ".env"

if (-not (Test-Path $envFile)) {
  Write-Error ".env が見つかりません。先に .env.example をコピーして OPENAI_API_KEY を設定してください。"
}

$keyLine = Get-Content $envFile | Where-Object { $_ -match '^OPENAI_API_KEY=' } | Select-Object -First 1
if (-not $keyLine) {
  Write-Error ".env に OPENAI_API_KEY がありません。"
}
$key = $keyLine.Substring("OPENAI_API_KEY=".Length).Trim()
if ([string]::IsNullOrWhiteSpace($key)) {
  Write-Error "OPENAI_API_KEY が空です。"
}

Write-Host "Setting Railway variable OPENAI_API_KEY ..."
railway variables set "OPENAI_API_KEY=$key"
railway variables set "OPENAI_MODEL=gpt-4o-mini"
Write-Host "Done. Confirm with: railway variables"
