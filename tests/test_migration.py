"""Tests for household-group config-entry migration helpers."""

from ._loader import load_integration_module

migration = load_integration_module("migration")


def test_strip_obsolete_group_config_preserves_contact_data() -> None:
    """Only the two legacy group fields are removed."""
    original = {
        "person_entity_id": "person.seba",
        "recipient": "393331234567",
        "contact_role": "family",
        "group_adults": True,
        "future_contact_metadata": {"language": "en"},
    }

    assert migration.without_obsolete_group_config(original) == {
        "person_entity_id": "person.seba",
        "recipient": "393331234567",
        "future_contact_metadata": {"language": "en"},
    }
    assert original["contact_role"] == "family"
    assert original["group_adults"] is True


def test_legacy_group_unique_ids_are_exact() -> None:
    """Migration targets only the three unique IDs emitted by version 1.0."""
    assert migration.legacy_group_unique_ids("account") == {
        "account_group_family",
        "account_group_adults",
        "account_group_guests",
    }
    assert "account_person:person.seba" not in (
        migration.legacy_group_unique_ids("account")
    )
