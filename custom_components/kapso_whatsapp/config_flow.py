"""Config flow for Kapso WhatsApp.

The recipient-subentry structure is adapted from Home Assistant Core's
Apache-2.0-licensed Telegram bot integration.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, override

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import CONF_API_KEY, CONF_NAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import KapsoConfigEntry
from .api import (
    KapsoAuthenticationError,
    KapsoClient,
    KapsoConnectionError,
    KapsoError,
    KapsoPhoneNumber,
    KapsoRequestError,
)
from .const import (
    CONF_NOTIFICATION_MODE,
    CONF_PHONE_NUMBER_ID,
    CONF_RECIPIENT,
    CONF_TEMPLATE_LANGUAGE,
    CONF_TEMPLATE_NAME,
    DEFAULT_TEMPLATE_LANGUAGE,
    DOMAIN,
    NOTIFICATION_MODE_TEMPLATE,
    NOTIFICATION_MODES,
    SUBENTRY_TYPE_RECIPIENT,
)
from .helpers import normalize_recipient

ACCOUNT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        ),
        vol.Required(CONF_PHONE_NUMBER_ID): TextSelector(TextSelectorConfig()),
    }
)
REAUTH_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_API_KEY): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        )
    }
)
RECIPIENT_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): TextSelector(TextSelectorConfig()),
        vol.Required(CONF_RECIPIENT): TextSelector(TextSelectorConfig()),
        vol.Required(
            CONF_NOTIFICATION_MODE, default=NOTIFICATION_MODE_TEMPLATE
        ): SelectSelector(
            SelectSelectorConfig(
                options=list(NOTIFICATION_MODES),
                translation_key="notification_mode",
            )
        ),
        vol.Optional(CONF_TEMPLATE_NAME): TextSelector(TextSelectorConfig()),
        vol.Required(
            CONF_TEMPLATE_LANGUAGE, default=DEFAULT_TEMPLATE_LANGUAGE
        ): TextSelector(TextSelectorConfig()),
    }
)


class KapsoWhatsAppConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle configuration for a Kapso WhatsApp sender."""

    VERSION = 1

    @classmethod
    @callback
    @override
    def async_get_supported_subentry_types(
        cls, config_entry: KapsoConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the recipient subentries supported by this integration."""
        return {SUBENTRY_TYPE_RECIPIENT: RecipientSubentryFlow}

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create a Kapso account entry."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            try:
                phone_number = await _validate_account(self.hass, user_input)
            except KapsoAuthenticationError:
                errors["base"] = "invalid_auth"
            except KapsoConnectionError:
                errors["base"] = "cannot_connect"
            except KapsoRequestError as err:
                errors["base"] = "invalid_phone_number"
                placeholders["error"] = str(err)
            except KapsoError as err:
                errors["base"] = "kapso_error"
                placeholders["error"] = str(err)
            else:
                await self.async_set_unique_id(phone_number.id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=_entry_title(phone_number),
                    data={
                        CONF_API_KEY: user_input[CONF_API_KEY],
                        CONF_PHONE_NUMBER_ID: phone_number.id,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                ACCOUNT_SCHEMA, user_input or {}
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace an expired or revoked Kapso API key."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        entry = self._get_reauth_entry()

        if user_input is not None:
            updated_data = {**entry.data, CONF_API_KEY: user_input[CONF_API_KEY]}
            try:
                phone_number = await _validate_account(self.hass, updated_data)
            except KapsoAuthenticationError:
                errors["base"] = "invalid_auth"
            except KapsoConnectionError:
                errors["base"] = "cannot_connect"
            except KapsoError as err:
                errors["base"] = "kapso_error"
                placeholders["error"] = str(err)
            else:
                return self.async_update_and_abort(
                    entry,
                    title=_entry_title(phone_number),
                    data_updates=updated_data,
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=REAUTH_SCHEMA,
            errors=errors,
            description_placeholders=placeholders,
        )


class RecipientSubentryFlow(ConfigSubentryFlow):
    """Create a recipient and its notify entity."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a WhatsApp recipient."""
        entry = self._get_entry()
        if entry.state is not ConfigEntryState.LOADED:
            return self.async_abort(
                reason="entry_not_loaded",
                description_placeholders={"entry_title": entry.title},
            )

        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}
        if user_input is not None:
            try:
                recipient = normalize_recipient(user_input[CONF_RECIPIENT])
            except ValueError as err:
                errors["base"] = "invalid_recipient"
                placeholders["error"] = str(err)
            else:
                template_name = user_input.get(CONF_TEMPLATE_NAME, "").strip()
                if (
                    user_input[CONF_NOTIFICATION_MODE] == NOTIFICATION_MODE_TEMPLATE
                    and not template_name
                ):
                    errors["base"] = "template_required"
                else:
                    unique_id = f"phone:{recipient}"
                    if any(
                        subentry.unique_id == unique_id
                        for subentry in entry.subentries.values()
                    ):
                        return self.async_abort(reason="already_configured")

                    return self.async_create_entry(
                        title=user_input[CONF_NAME].strip(),
                        unique_id=unique_id,
                        data={
                            CONF_RECIPIENT: recipient,
                            CONF_NOTIFICATION_MODE: user_input[CONF_NOTIFICATION_MODE],
                            CONF_TEMPLATE_NAME: template_name,
                            CONF_TEMPLATE_LANGUAGE: user_input[
                                CONF_TEMPLATE_LANGUAGE
                            ].strip(),
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                RECIPIENT_SCHEMA, user_input or {}
            ),
            errors=errors,
            description_placeholders=placeholders,
        )


async def _validate_account(
    hass: HomeAssistant, data: Mapping[str, Any]
) -> KapsoPhoneNumber:
    """Validate a Kapso API key and WhatsApp Business sender number."""
    client = KapsoClient(
        async_get_clientsession(hass),
        data[CONF_API_KEY],
        data[CONF_PHONE_NUMBER_ID],
    )
    return await client.async_get_phone_number()


def _entry_title(phone_number: KapsoPhoneNumber) -> str:
    """Build a useful account title from Kapso's phone metadata."""
    name = phone_number.verified_name or "Kapso WhatsApp"
    if phone_number.display_phone_number:
        return f"{name} ({phone_number.display_phone_number})"
    return name
