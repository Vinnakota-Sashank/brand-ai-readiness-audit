$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$archive = Join-Path $root 'brand-ai-readiness-audit.zip'
if (Test-Path $archive) { Remove-Item $archive -Force }
$items = Get-ChildItem $root -Force | Where-Object { $_.Name -notin @('.git', '__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', 'brand-ai-readiness-audit.zip', 'src') }
Compress-Archive -Path $items.FullName -DestinationPath $archive -CompressionLevel Optimal
Write-Host "Created $archive"
Write-Host ((Get-Item $archive).Length.ToString() + ' bytes')
