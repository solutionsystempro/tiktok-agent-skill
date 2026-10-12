# Copyright (c) 2026 Ian Ryan Kirk. MIT License.
"""Shared helpers. Each tool lives in its own skill folder and is not a
package, so tests load it by path, the same way a copied skill folder runs."""

import importlib.util
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")


def load(skill, module):
    path = os.path.join(SKILLS, skill, module + ".py")
    spec = importlib.util.spec_from_file_location(f"{skill}_{module}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_cli(skill, script, *args, stdin=None, cwd=None):
    """Run a tool the way a user does, through pipes. -I ignores
    PYTHONIOENCODING and PYTHONUTF8, so a Windows cp1252 default would show
    up here as a crash."""
    return subprocess.run(
        [sys.executable, "-I", os.path.join(SKILLS, skill, script), *args],
        input=stdin.encode("utf-8") if stdin is not None else None,
        capture_output=True, timeout=60, cwd=cwd)


def temp_file(content, suffix=".txt", raw=None):
    """Write content (str, utf-8) or raw bytes to a temp file and return its path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as fh:
        fh.write(raw if raw is not None else content.encode("utf-8"))
    return path
