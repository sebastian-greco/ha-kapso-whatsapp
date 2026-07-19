"""Validation helpers for the Kapso WhatsApp integration."""

import re

_PHONE_RE = re.compile(r"^[0-9]{7,15}$")


def normalize_recipient(recipient: str) -> str:
    """Normalize and validate a WhatsApp destination phone number."""
    value = re.sub(r"[\s()+.-]", "", recipient.strip())
    if not _PHONE_RE.fullmatch(value):
        raise ValueError(
            "Phone recipients must contain 7 to 15 digits including country code"
        )
    return value
