"""Notify entities for Kapso WhatsApp.

The entity-per-recipient structure is adapted from Home Assistant Core's
Apache-2.0-licensed Telegram bot integration.
"""

from typing import override

from homeassistant.components.notify import (
    NotifyEntity,
    NotifyEntityDescription,
    NotifyEntityFeature,
)
from homeassistant.config_entries import ConfigSubentry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import KapsoConfigEntry
from .api import KapsoError
from .const import (
    CONF_NOTIFICATION_MODE,
    CONF_RECIPIENT,
    CONF_TEMPLATE_LANGUAGE,
    CONF_TEMPLATE_NAME,
    DOMAIN,
    NOTIFICATION_MODE_TEMPLATE,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: KapsoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up one notify entity per configured recipient."""
    for subentry_id, subentry in config_entry.subentries.items():
        async_add_entities(
            [KapsoNotifyEntity(config_entry, subentry)],
            config_subentry_id=subentry_id,
        )


class KapsoNotifyEntity(NotifyEntity):
    """A WhatsApp notification destination backed by Kapso."""

    _attr_has_entity_name = True
    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(
        self, config_entry: KapsoConfigEntry, subentry: ConfigSubentry
    ) -> None:
        """Initialize the recipient notify entity."""
        phone_number = config_entry.runtime_data.phone_number
        recipient = subentry.data[CONF_RECIPIENT]

        self.config_entry = config_entry
        self.entity_description = NotifyEntityDescription(key=recipient)
        self._subentry = subentry
        self._attr_name = subentry.title
        self._attr_unique_id = f"{phone_number.id}_{subentry.unique_id or recipient}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, phone_number.id)},
            name=config_entry.title,
            manufacturer="Kapso",
            model="WhatsApp Business Cloud API",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://app.kapso.ai",
        )

    @override
    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a text or template-backed Home Assistant notification."""
        text = f"{title}\n{message}" if title else message
        data = self._subentry.data

        try:
            if data[CONF_NOTIFICATION_MODE] == NOTIFICATION_MODE_TEMPLATE:
                await self.config_entry.runtime_data.client.async_send_template(
                    data[CONF_RECIPIENT],
                    data[CONF_TEMPLATE_NAME],
                    data[CONF_TEMPLATE_LANGUAGE],
                    body_parameters=[text],
                )
            else:
                await self.config_entry.runtime_data.client.async_send_text(
                    data[CONF_RECIPIENT],
                    text,
                )
        except KapsoError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="action_failed",
                translation_placeholders={"error": str(err)},
            ) from err
