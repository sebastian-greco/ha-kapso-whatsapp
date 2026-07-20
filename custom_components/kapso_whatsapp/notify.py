"""Individual and group notify entities for Kapso WhatsApp.

The entity-per-recipient structure is adapted from Home Assistant Core's
Apache-2.0-licensed Telegram bot integration.
"""

from typing import override

from homeassistant.components.notify import (
    NotifyEntity,
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
    CONF_CONTACT_ROLE,
    CONF_GROUP_ADULTS,
    CONF_NOTIFICATION_MODE,
    CONF_RECIPIENT,
    CONF_TEMPLATE_LANGUAGE,
    CONF_TEMPLATE_NAME,
    CONF_TEMPLATE_PARAMETER_FORMAT,
    CONTACT_ROLE_FAMILY,
    CONTACT_ROLE_GUEST,
    DOMAIN,
    NOTIFICATION_MODE_TEMPLATE,
    RECIPIENT_GROUP_ADULTS,
    RECIPIENT_GROUP_FAMILY,
    RECIPIENT_GROUP_GUESTS,
    TEMPLATE_PARAMETER_FORMAT_NAMED,
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: KapsoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up individual recipients and logical household groups."""
    recipients = list(config_entry.subentries.items())
    for subentry_id, subentry in recipients:
        async_add_entities(
            [KapsoNotifyEntity(config_entry, subentry)],
            config_subentry_id=subentry_id,
        )

    group_members = {
        RECIPIENT_GROUP_FAMILY: [
            subentry
            for _, subentry in recipients
            if subentry.data.get(CONF_CONTACT_ROLE, CONTACT_ROLE_FAMILY)
            == CONTACT_ROLE_FAMILY
        ],
        RECIPIENT_GROUP_ADULTS: [
            subentry
            for _, subentry in recipients
            if subentry.data.get(CONF_GROUP_ADULTS, False)
        ],
        RECIPIENT_GROUP_GUESTS: [
            subentry
            for _, subentry in recipients
            if subentry.data.get(CONF_CONTACT_ROLE, CONTACT_ROLE_FAMILY)
            == CONTACT_ROLE_GUEST
        ],
    }
    async_add_entities(
        [
            KapsoGroupNotifyEntity(config_entry, group, members)
            for group, members in group_members.items()
        ]
    )


class KapsoNotifyEntity(NotifyEntity):
    """A WhatsApp notification destination backed by Kapso."""

    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(
        self, config_entry: KapsoConfigEntry, subentry: ConfigSubentry
    ) -> None:
        """Initialize the recipient notify entity."""
        phone_number = config_entry.runtime_data.phone_number
        recipient = subentry.data[CONF_RECIPIENT]

        self.config_entry = config_entry
        self._subentry = subentry
        self._attr_name = subentry.title
        self._attr_unique_id = f"{phone_number.id}_{subentry.unique_id or recipient}"
        self._attr_device_info = _device_info(config_entry)

    @property
    @override
    def suggested_object_id(self) -> str:
        """Use the contact name for the initial entity ID."""
        return self._subentry.title

    @override
    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a text or template-backed Home Assistant notification."""
        try:
            await _async_send_to_recipient(
                self.config_entry, self._subentry, message, title
            )
        except KapsoError as err:
            raise _home_assistant_error(err) from err


class KapsoGroupNotifyEntity(NotifyEntity):
    """A logical group that fans out to selected WhatsApp recipients."""

    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(
        self,
        config_entry: KapsoConfigEntry,
        group: str,
        members: list[ConfigSubentry],
    ) -> None:
        """Initialize a Family, Adults, or Guests notification group."""
        phone_number = config_entry.runtime_data.phone_number
        self.config_entry = config_entry
        self._group = group
        self._members = members
        self._attr_name = group.title()
        self._attr_unique_id = f"{phone_number.id}_group_{group}"
        self._attr_device_info = _device_info(config_entry)

    @property
    @override
    def suggested_object_id(self) -> str:
        """Use the logical group for the initial entity ID."""
        return self._group

    @override
    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send independently to every recipient selected for this group."""
        failures: list[KapsoError] = []
        for member in self._members:
            try:
                await _async_send_to_recipient(
                    self.config_entry, member, message, title
                )
            except KapsoError as err:
                failures.append(err)
        if failures:
            first_error = failures[0]
            error = KapsoError(
                f"{len(failures)} of {len(self._members)} group deliveries failed: "
                f"{first_error}"
            )
            raise _home_assistant_error(error) from first_error


async def _async_send_to_recipient(
    config_entry: KapsoConfigEntry,
    subentry: ConfigSubentry,
    message: str,
    title: str | None,
) -> None:
    """Render and send one configured recipient notification."""
    data = subentry.data
    client = config_entry.runtime_data.client
    if data[CONF_NOTIFICATION_MODE] != NOTIFICATION_MODE_TEMPLATE:
        text = f"{title}\n{message}" if title else message
        await client.async_send_text(data[CONF_RECIPIENT], text)
        return

    if data.get(CONF_TEMPLATE_PARAMETER_FORMAT) == TEMPLATE_PARAMETER_FORMAT_NAMED:
        await client.async_send_template(
            data[CONF_RECIPIENT],
            data[CONF_TEMPLATE_NAME],
            data[CONF_TEMPLATE_LANGUAGE],
            named_body_parameters={
                "subject": title or "Home Assistant",
                "notification_details": message,
            },
        )
        return

    text = f"{title}\n{message}" if title else message
    await client.async_send_template(
        data[CONF_RECIPIENT],
        data[CONF_TEMPLATE_NAME],
        data[CONF_TEMPLATE_LANGUAGE],
        body_parameters=[text],
    )


def _device_info(config_entry: KapsoConfigEntry) -> DeviceInfo:
    """Describe the shared Kapso WhatsApp sender service."""
    phone_number = config_entry.runtime_data.phone_number
    return DeviceInfo(
        identifiers={(DOMAIN, phone_number.id)},
        name=config_entry.title,
        manufacturer="Kapso",
        model="WhatsApp Business Cloud API",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url="https://app.kapso.ai",
    )


def _home_assistant_error(err: Exception) -> HomeAssistantError:
    """Translate a Kapso delivery failure for Home Assistant."""
    return HomeAssistantError(
        translation_domain=DOMAIN,
        translation_key="action_failed",
        translation_placeholders={"error": str(err)},
    )
