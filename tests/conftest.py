"""Fixtures shared across test files. pytest loads this file automatically."""

from pathlib import Path

import pytest


@pytest.fixture
def record(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Where the stand-in claude.exe writes down what it was given (see fake_claude.py)."""
    path = tmp_path / "record.json"
    monkeypatch.setenv("FAKE_CLAUDE_RECORD", str(path))
    return path
