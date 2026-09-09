#!/usr/bin/env bash
set -euo pipefail
root="$(cd "$(dirname "$0")/.." && pwd)"
cd "$root"
python tests/validate_package.py
rm -f brand-ai-readiness-audit.zip
zip -r brand-ai-readiness-audit.zip . -x '.git/*' '__pycache__/*' '*.pyc' '.pytest_cache/*' '.mypy_cache/*' '.ruff_cache/*' 'src/*' 'brand-ai-readiness-audit.zip'
