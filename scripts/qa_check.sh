#!/usr/bin/env bash
set -euo pipefail
python tests/validate_package.py
python -m pytest -q
python -m compileall -q skills tests
echo "ALL CHECKS PASSED"
