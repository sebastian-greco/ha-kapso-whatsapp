"""Async client for the Kapso WhatsApp API."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession

from .const import DEFAULT_API_BASE_URL

REQUEST_TIMEOUT_SECONDS = 15
CONFLICT_RETRY_DELAY_SECONDS = 1


class KapsoError(Exception):
    """Base exception for Kapso API failures."""


class KapsoConnectionError(KapsoError):
    """Raised when Kapso cannot be reached."""


class KapsoAuthenticationError(KapsoError):
    """Raised when Kapso rejects the API key."""


class KapsoRequestError(KapsoError):
    """Raised when Kapso rejects a request."""

    def __init__(self, message: str, status: int) -> None:
        """Initialize the request error."""
        super().__init__(message)
        self.status = status


class KapsoConflictError(KapsoRequestError):
    """Raised when another message is in flight for the recipient."""


class KapsoRateLimitError(KapsoRequestError):
    """Raised when the Kapso or Meta rate limit is exceeded."""


class KapsoResponseError(KapsoError):
    """Raised when Kapso returns an unexpected response."""


@dataclass(frozen=True, slots=True)
class KapsoPhoneNumber:
    """Details for a connected WhatsApp Business phone number."""

    id: str
    verified_name: str | None
    display_phone_number: str | None
    quality_rating: str | None
    account_mode: str | None
    messaging_limit_tier: str | None


@dataclass(frozen=True, slots=True)
class KapsoMessage:
    """Result returned after Kapso accepts a message."""

    id: str
    recipient: str


class KapsoClient:
    """Small async client for the Kapso Meta-compatible API."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        phone_number_id: str,
        *,
        base_url: str = DEFAULT_API_BASE_URL,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._api_key = api_key
        self.phone_number_id = phone_number_id
        self._base_url = base_url.rstrip("/")

    async def async_get_phone_number(self) -> KapsoPhoneNumber:
        """Validate credentials and fetch the configured sender number."""
        data = await self._request(
            "GET",
            self.phone_number_id,
            params={
                "fields": (
                    "id,verified_name,display_phone_number,quality_rating,"
                    "account_mode,messaging_limit_tier"
                )
            },
        )
        phone_id = data.get("id")
        if not isinstance(phone_id, str):
            raise KapsoResponseError("Kapso did not return a phone number ID")

        return KapsoPhoneNumber(
            id=phone_id,
            verified_name=_optional_string(data.get("verified_name")),
            display_phone_number=_optional_string(data.get("display_phone_number")),
            quality_rating=_optional_string(data.get("quality_rating")),
            account_mode=_optional_string(data.get("account_mode")),
            messaging_limit_tier=_optional_string(data.get("messaging_limit_tier")),
        )

    async def async_send_text(
        self,
        recipient: str,
        message: str,
        *,
        preview_url: bool = False,
    ) -> KapsoMessage:
        """Send a free-form text message."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "text",
            "text": {"body": message, "preview_url": preview_url},
        }
        return await self._send_message(payload, recipient)

    async def async_send_template(
        self,
        recipient: str,
        template_name: str,
        language: str,
        *,
        body_parameters: list[str] | None = None,
        named_body_parameters: Mapping[str, str] | None = None,
    ) -> KapsoMessage:
        """Send an approved template with positional or named body parameters."""
        if body_parameters and named_body_parameters:
            raise ValueError(
                "Positional and named template parameters cannot be combined"
            )

        template: dict[str, Any] = {
            "name": template_name,
            "language": {"code": language},
        }
        if body_parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": parameter}
                        for parameter in body_parameters
                    ],
                }
            ]
        elif named_body_parameters:
            template["components"] = [
                {
                    "type": "body",
                    "parameters": [
                        {
                            "type": "text",
                            "parameter_name": name,
                            "text": value,
                        }
                        for name, value in named_body_parameters.items()
                    ],
                }
            ]

        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": template,
        }
        return await self._send_message(payload, recipient)

    async def async_send_authentication_code(
        self,
        recipient: str,
        template_name: str,
        language: str,
        code: str,
    ) -> KapsoMessage:
        """Send an approved COPY_CODE authentication template."""
        payload: dict[str, Any] = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": recipient,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": [
                    {
                        "type": "body",
                        "parameters": [{"type": "text", "text": code}],
                    },
                    {
                        "type": "button",
                        "sub_type": "otp",
                        "index": "0",
                        "parameters": [{"type": "text", "text": code}],
                    },
                ],
            },
        }
        return await self._send_message(payload, recipient)

    async def _send_message(
        self, payload: dict[str, Any], fallback_recipient: str
    ) -> KapsoMessage:
        """Send a message, retrying Kapso's transient in-flight conflict once."""
        for attempt in range(2):
            try:
                data = await self._request(
                    "POST", f"{self.phone_number_id}/messages", json=payload
                )
            except KapsoConflictError:
                if attempt:
                    raise
                await asyncio.sleep(CONFLICT_RETRY_DELAY_SECONDS)
            else:
                return _message_from_response(data, fallback_recipient)

        raise KapsoResponseError("Kapso did not return a message response")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform one authenticated API request."""
        url = f"{self._base_url}/{path.lstrip('/')}"
        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT_SECONDS):
                async with self._session.request(
                    method,
                    url,
                    headers=headers,
                    json=json,
                    params=params,
                ) as response:
                    try:
                        data = await response.json(content_type=None)
                    except TypeError, ValueError:
                        data = {"error": await response.text()}
                    status = response.status
        except TimeoutError as err:
            raise KapsoConnectionError("The request to Kapso timed out") from err
        except (ClientError, OSError) as err:
            raise KapsoConnectionError(f"Unable to connect to Kapso: {err}") from err

        if not isinstance(data, dict):
            raise KapsoResponseError("Kapso returned an invalid JSON response")

        if status < 400:
            return data

        message = _error_message(data, status)
        if status in (401, 403):
            raise KapsoAuthenticationError(message)
        if status == 409:
            raise KapsoConflictError(message, status)
        if status == 429:
            raise KapsoRateLimitError(message, status)
        raise KapsoRequestError(message, status)


def _message_from_response(
    data: dict[str, Any], fallback_recipient: str
) -> KapsoMessage:
    """Parse a successful message response."""
    messages = data.get("messages")
    if not isinstance(messages, list) or not messages:
        raise KapsoResponseError("Kapso did not return a message ID")
    first_message = messages[0]
    if not isinstance(first_message, dict) or not isinstance(
        first_message.get("id"), str
    ):
        raise KapsoResponseError("Kapso returned an invalid message ID")

    recipient = fallback_recipient
    contacts = data.get("contacts")
    if isinstance(contacts, list) and contacts and isinstance(contacts[0], dict):
        recipient = str(contacts[0].get("wa_id") or fallback_recipient)

    return KapsoMessage(id=first_message["id"], recipient=recipient)


def _error_message(data: dict[str, Any], status: int) -> str:
    """Extract a useful, non-secret error message."""
    error = data.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message:
            return message
    if isinstance(error, str) and error:
        return error
    message = data.get("message")
    if isinstance(message, str) and message:
        return message
    return f"Kapso request failed with HTTP {status}"


def _optional_string(value: Any) -> str | None:
    """Return a value only when it is a string."""
    return value if isinstance(value, str) else None
