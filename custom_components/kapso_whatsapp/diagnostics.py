"""Diagnostics for the Kapso WhatsApp integration."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant

from . import KapsoConfigEntry
from .const import CONF_PHONE_NUMBER_ID, CONF_RECIPIENT

TO_REDACT = {CONF_API_KEY, CONF_PHONE_NUMBER_ID, CONF_RECIPIENT}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KapsoConfigEntry
) -> dict[str, Any]:
    """Return redacted account, recipient, and sender diagnostics."""
    phone_number = entry.runtime_data.phone_number
    return {
        "config_entry": async_redact_data(dict(entry.data), TO_REDACT),
        "phone_number": async_redact_data(
            {
                "phone_number_id": phone_number.id,
                "verified_name": phone_number.verified_name,
                "recipient": phone_number.display_phone_number,
                "quality_rating": phone_number.quality_rating,
                "account_mode": phone_number.account_mode,
                "messaging_limit_tier": phone_number.messaging_limit_tier,
            },
            TO_REDACT,
        ),
        "recipients": [
            {
                "title": subentry.title,
                "data": async_redact_data(dict(subentry.data), TO_REDACT),
            }
            for subentry in entry.subentries.values()
        ],
    }
