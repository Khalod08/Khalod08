"""Tests run with GoatVex's default notation, whatever the student's course materials say."""

import pytest


@pytest.fixture(autouse=True)
def default_notation(monkeypatch):
    from tutor.materials import notation

    monkeypatch.setattr(notation, "settings_for", lambda course: dict(notation.DEFAULTS))
