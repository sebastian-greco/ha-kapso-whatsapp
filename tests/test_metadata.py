"""Tests for HACS and Home Assistant metadata files."""

import json
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "waha_whatsapp"


def test_json_metadata_is_valid() -> None:
    """All JSON metadata parses and English translations match strings."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    strings = json.loads((INTEGRATION / "strings.json").read_text())
    english = json.loads((INTEGRATION / "translations" / "en.json").read_text())

    assert manifest["domain"] == "waha_whatsapp"
    assert manifest["config_flow"] is True
    assert (
        manifest["version"]
        == tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    )
    assert manifest["codeowners"] == ["@sebastian-greco"]
    assert manifest["issue_tracker"].endswith("/issues")
    assert hacs["name"] == "WAHA WhatsApp"
    assert english == strings


def test_service_metadata_matches_actions() -> None:
    """The direct free-form action is described for the automation editor."""
    services = yaml.safe_load((INTEGRATION / "services.yaml").read_text())
    assert set(services) == {"send_message"}


def test_recipient_flow_uses_home_assistant_people() -> None:
    """Recipient setup can link optional Person metadata to a contact."""
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'domain="person"' in source
    assert "vol.Optional(CONF_PERSON_ENTITY_ID)" in source
    assert "vol.Optional(CONF_NAME)" in source
    assert "CONF_CONTACT_ROLE" not in source
    assert "CONF_GROUP_ADULTS" not in source


def test_recipient_changes_use_one_reload_listener() -> None:
    """All entry and subentry changes reload individual recipient entities."""
    integration = (INTEGRATION / "__init__.py").read_text()
    config_flow = (INTEGRATION / "config_flow.py").read_text()

    assert "entry.add_update_listener(_async_reload_entry)" in integration
    assert "await hass.config_entries.async_reload(entry.entry_id)" in integration
    assert "async_update_reload_and_abort" not in config_flow
    assert "reload_on_update=False" in config_flow


def test_notify_entities_share_stable_waha_device_name() -> None:
    """Account identity and server version do not leak into entity IDs."""
    source = (INTEGRATION / "notify.py").read_text()

    assert 'name="WAHA"' in source
    assert "name=config_entry.title" not in source


def test_notify_platform_has_only_individual_contacts() -> None:
    """The notify platform does not create household-group entities."""
    source = (INTEGRATION / "notify.py").read_text()

    assert "WahaGroupNotifyEntity" not in source
    assert "RECIPIENT_GROUP_" not in source
    assert "config_entry.subentries.items()" in source


def test_notify_entities_expose_safe_person_metadata() -> None:
    """Individual entities publish only the template-safe Person association."""
    source = (INTEGRATION / "notify.py").read_text()

    assert "_attr_extra_state_attributes = contact_state_attributes(" in source


def test_config_entry_migration_is_registered() -> None:
    """Version 1.2 migration removes only legacy integration-owned groups."""
    integration = (INTEGRATION / "__init__.py").read_text()
    config_flow = (INTEGRATION / "config_flow.py").read_text()

    assert "MINOR_VERSION = 2" in config_flow
    assert "async def async_migrate_entry(" in integration
    assert "async_update_subentry(" in integration
    assert "async_entries_for_config_entry(" in integration
    assert "entity.platform == DOMAIN" in integration
    assert "entity.unique_id in obsolete_unique_ids" in integration
