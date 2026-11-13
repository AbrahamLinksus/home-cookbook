"""Smoke test: every layer package of the skeleton imports cleanly."""

import importlib

import pytest

LAYER_PACKAGES = [
    "cookbook",
    "cookbook.domain",
    "cookbook.adapters",
    "cookbook.services",
    "cookbook.web",
    "cookbook.app",
]


@pytest.mark.parametrize("name", LAYER_PACKAGES)
def test_package_import_layer_succeeds(name: str) -> None:
    # Arrange / Act
    module = importlib.import_module(name)

    # Assert
    assert module.__name__ == name
