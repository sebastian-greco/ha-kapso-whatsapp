"""Tests for HACS and Home Assistant metadata files."""

import json
import tomllib
from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]
INTEGRATION = ROOT / "custom_components" / "kapso_whatsapp"


def test_json_metadata_is_valid() -> None:
    """All JSON metadata parses and English translations match strings."""
    manifest = json.loads((INTEGRATION / "manifest.json").read_text())
    hacs = json.loads((ROOT / "hacs.json").read_text())
    strings = json.loads((INTEGRATION / "strings.json").read_text())
    english = json.loads((INTEGRATION / "translations" / "en.json").read_text())

    assert manifest["domain"] == "kapso_whatsapp"
    assert manifest["config_flow"] is True
    assert (
        manifest["version"]
        == tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]["version"]
    )
    assert manifest["codeowners"] == ["@sebastian-greco"]
    assert manifest["issue_tracker"].endswith("/issues")
    assert hacs["name"] == "Kapso WhatsApp"
    assert english == strings


def test_service_metadata_matches_actions() -> None:
    """The three Phase 1 actions are described for the automation editor."""
    services = yaml.safe_load((INTEGRATION / "services.yaml").read_text())
    assert set(services) == {
        "send_authentication_code",
        "send_template",
        "send_text",
    }
