"""Windows PowerShell 5.1 reads a .ps1 file without a byte-order mark in the legacy code page, so
any non-ASCII character (e.g. an em dash, whose UTF-8 bytes include a 'smart quote') breaks parsing."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_powershell_scripts_are_ascii():
    scripts = [p for p in ROOT.rglob("*.ps1") if ".venv" not in p.parts]
    assert scripts
    for p in scripts:
        for n, line in enumerate(p.read_bytes().splitlines(), 1):
            assert line.isascii(), f"{p.name}:{n} has non-ASCII characters: {line!r}"
