"""Tests for recipient validation."""

import pytest

from ._loader import load_integration_module

helpers = load_integration_module("helpers")


def test_normalize_phone() -> None:
    """Common phone formatting is removed before sending."""
    assert helpers.normalize_recipient("+39 333-123-4567") == "393331234567"


@pytest.mark.parametrize("recipient", ["+39", "abc123", "1" * 16])
def test_invalid_phone(recipient: str) -> None:
    """Malformed phone recipients fail locally."""
    with pytest.raises(ValueError, match="7 to 15 digits"):
        helpers.normalize_recipient(recipient)
