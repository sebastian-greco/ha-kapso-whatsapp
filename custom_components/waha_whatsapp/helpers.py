"""Validation and formatting helpers for WAHA WhatsApp."""

import re
from collections.abc import Mapping
from typing import Any

from .const import ATTR_PERSON_ENTITY_ID, CONF_PERSON_ENTITY_ID

_PHONE_RE = re.compile(r"^[0-9]{7,15}$")
_CHAT_ID_RE = re.compile(r"^[0-9]{7,15}@c\.us$")


def normalize_recipient(recipient: str) -> str:
    """Normalize and validate a WhatsApp destination phone number."""
    value = re.sub(r"[\s()+.\-]", "", recipient.strip())
    if not _PHONE_RE.fullmatch(value):
        raise ValueError(
            "Phone recipients must contain 7 to 15 digits including country code"
        )
    return value


def recipient_chat_id(recipient: str) -> str:
    """Convert a normalized phone number to a WAHA direct-message chat ID."""
    return f"{normalize_recipient(recipient)}@c.us"


def normalize_chat_id(value: str) -> str:
    """Accept a phone number or WAHA direct-message chat ID."""
    candidate = value.strip()
    if _CHAT_ID_RE.fullmatch(candidate):
        return candidate
    return recipient_chat_id(candidate)


def render_notification(message: str, title: str | None = None) -> str:
    """Render a Home Assistant title and message as readable WhatsApp text."""
    clean_message = message.strip()
    clean_title = title.strip() if title else ""
    if not clean_title:
        return clean_message
    return f"*{clean_title}*\n\n{clean_message}"


def contact_state_attributes(data: Mapping[str, Any]) -> dict[str, str]:
    """Expose non-sensitive contact identity metadata as state attributes."""
    person_entity_id = data.get(CONF_PERSON_ENTITY_ID)
    if not isinstance(person_entity_id, str) or not person_entity_id:
        return {}
    return {ATTR_PERSON_ENTITY_ID: person_entity_id}
