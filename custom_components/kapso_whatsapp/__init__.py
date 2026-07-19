"""Kapso WhatsApp integration for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
)
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    KapsoAuthenticationError,
    KapsoClient,
    KapsoError,
    KapsoMessage,
    KapsoPhoneNumber,
)
from .const import (
    ATTR_BODY_PARAMETERS,
    ATTR_CODE,
    ATTR_LANGUAGE,
    ATTR_PREVIEW_URL,
    ATTR_TEMPLATE_NAME,
    ATTR_TO,
    CONF_PHONE_NUMBER_ID,
    DEFAULT_TEMPLATE_LANGUAGE,
    DOMAIN,
    SERVICE_SEND_AUTHENTICATION_CODE,
    SERVICE_SEND_TEMPLATE,
    SERVICE_SEND_TEXT,
)
from .helpers import normalize_recipient

PLATFORMS: list[Platform] = [Platform.NOTIFY]
CONF_CONFIG_ENTRY_ID = "config_entry_id"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

BASE_SEND_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_CONFIG_ENTRY_ID): cv.string,
        vol.Required(ATTR_TO): cv.string,
    }
)
SEND_TEXT_SCHEMA = BASE_SEND_SCHEMA.extend(
    {
        vol.Required("message"): cv.string,
        vol.Optional(ATTR_PREVIEW_URL, default=False): cv.boolean,
    }
)
SEND_TEMPLATE_SCHEMA = BASE_SEND_SCHEMA.extend(
    {
        vol.Required(ATTR_TEMPLATE_NAME): cv.string,
        vol.Optional(ATTR_LANGUAGE, default=DEFAULT_TEMPLATE_LANGUAGE): cv.string,
        vol.Optional(ATTR_BODY_PARAMETERS, default=[]): vol.All(
            cv.ensure_list, [cv.string]
        ),
    }
)
SEND_AUTHENTICATION_CODE_SCHEMA = BASE_SEND_SCHEMA.extend(
    {
        vol.Required(ATTR_TEMPLATE_NAME): cv.string,
        vol.Optional(ATTR_LANGUAGE, default=DEFAULT_TEMPLATE_LANGUAGE): cv.string,
        vol.Required(ATTR_CODE): cv.string,
    }
)


@dataclass(slots=True)
class KapsoRuntimeData:
    """Runtime data for a configured Kapso sender."""

    client: KapsoClient
    phone_number: KapsoPhoneNumber


type KapsoConfigEntry = ConfigEntry[KapsoRuntimeData]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration-level Kapso actions."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TEXT,
        _async_handle_send_service,
        schema=SEND_TEXT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_TEMPLATE,
        _async_handle_send_service,
        schema=SEND_TEMPLATE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_AUTHENTICATION_CODE,
        _async_handle_send_service,
        schema=SEND_AUTHENTICATION_CODE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: KapsoConfigEntry) -> bool:
    """Set up a Kapso WhatsApp config entry."""
    client = KapsoClient(
        async_get_clientsession(hass),
        entry.data[CONF_API_KEY],
        entry.data[CONF_PHONE_NUMBER_ID],
    )

    try:
        phone_number = await client.async_get_phone_number()
    except KapsoAuthenticationError as err:
        raise ConfigEntryAuthFailed("Kapso rejected the configured API key") from err
    except KapsoError as err:
        raise ConfigEntryNotReady(f"Unable to connect to Kapso: {err}") from err

    entry.runtime_data = KapsoRuntimeData(client, phone_number)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KapsoConfigEntry) -> bool:
    """Unload a Kapso WhatsApp config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_handle_send_service(call: ServiceCall) -> ServiceResponse:
    """Handle one integration-specific outbound action."""
    entry = _loaded_entry(call.hass, call.data[CONF_CONFIG_ENTRY_ID])
    try:
        recipient = normalize_recipient(call.data[ATTR_TO])
        if call.service == SERVICE_SEND_TEXT:
            result = await entry.runtime_data.client.async_send_text(
                recipient,
                call.data["message"],
                preview_url=call.data[ATTR_PREVIEW_URL],
            )
        elif call.service == SERVICE_SEND_TEMPLATE:
            result = await entry.runtime_data.client.async_send_template(
                recipient,
                call.data[ATTR_TEMPLATE_NAME],
                call.data[ATTR_LANGUAGE],
                body_parameters=list(call.data[ATTR_BODY_PARAMETERS]),
            )
        else:
            result = await entry.runtime_data.client.async_send_authentication_code(
                recipient,
                call.data[ATTR_TEMPLATE_NAME],
                call.data[ATTR_LANGUAGE],
                call.data[ATTR_CODE],
            )
    except ValueError as err:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_recipient",
            translation_placeholders={"error": str(err)},
        ) from err
    except KapsoError as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="action_failed",
            translation_placeholders={"error": str(err)},
        ) from err

    if call.return_response:
        return _service_response(result)
    return None


def _loaded_entry(hass: HomeAssistant, entry_id: str) -> KapsoConfigEntry:
    """Resolve and validate the config entry selected by an action."""
    entry = hass.config_entries.async_get_entry(entry_id)
    if entry is None or entry.domain != DOMAIN:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_config_entry",
            translation_placeholders={"entry_id": entry_id},
        )
    if entry.state is not ConfigEntryState.LOADED:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="entry_not_loaded",
            translation_placeholders={"entry_title": entry.title},
        )
    return cast(KapsoConfigEntry, entry)


def _service_response(result: KapsoMessage) -> dict[str, str]:
    """Format an action response for Home Assistant."""
    return {"message_id": result.id, "recipient": result.recipient}
