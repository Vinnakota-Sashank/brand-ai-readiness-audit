"""Make each self-contained skill script importable during the test run."""
from pathlib import Path
import sys
import os
import subprocess

ROOT = Path(__file__).resolve().parents[1]
for scripts_dir in sorted((ROOT / "skills").glob("*/scripts")):
    sys.path.insert(0, str(scripts_dir))

# The source tests use the Unix executable name; keep them portable on Windows.
os.environ["PATH"] = str(Path(__file__).resolve().parent) + os.pathsep + os.environ.get("PATH", "")

_run = subprocess.run


def _portable_run(args, *run_args, **run_kwargs):
    if isinstance(args, (list, tuple)):
        args = list(args)
        if args and args[0] == "python3":
            args[0] = sys.executable
        args = [str(ROOT / value.replace("skills/", "skills/")) if isinstance(value, str) and value.startswith("skills/") else value for value in args]
    return _run(args, *run_args, **run_kwargs)


subprocess.run = _portable_run
