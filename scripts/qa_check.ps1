$ErrorActionPreference = 'Stop'
Write-Host '=== Package validation ==='
python tests/validate_package.py
Write-Host '=== Test suite ==='
python -m pytest -q
Write-Host '=== Syntax compilation ==='
python -m compileall -q skills tests
Write-Host '=== ALL CHECKS PASSED ==='
