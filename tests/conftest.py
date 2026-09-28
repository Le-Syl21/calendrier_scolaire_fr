"""Shared fixtures."""

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    yield


def records(name: str) -> list[dict]:
    """A real answer of the Éducation nationale API, saved on 2026-09-28."""
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))["results"]
