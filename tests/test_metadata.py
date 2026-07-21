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
    """Recipient setup links a Person entity to a WhatsApp number."""
    source = (INTEGRATION / "config_flow.py").read_text()
    assert 'domain="person"' in source
    assert "CONF_PERSON_ENTITY_ID" in source


def test_recipient_changes_use_one_reload_listener() -> None:
    """All entry and subentry changes reload recipient and group entities."""
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
