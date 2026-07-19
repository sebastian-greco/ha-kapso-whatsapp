"""Tests for the provider-independent Kapso API client."""

from typing import Any

import pytest

from ._loader import load_integration_module

api = load_integration_module("api")


class FakeResponse:
    """Minimal aiohttp response context manager."""

    def __init__(self, status: int, data: Any) -> None:
        self.status = status
        self._data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback) -> None:
        return None

    async def json(self, *, content_type=None):
        return self._data

    async def text(self) -> str:
        return str(self._data)


class FakeSession:
    """Capture requests and return queued responses."""

    def __init__(self, *responses: FakeResponse) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []

    def request(self, method: str, url: str, **kwargs):
        self.requests.append({"method": method, "url": url, **kwargs})
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_get_phone_number() -> None:
    """The account check uses the documented sender endpoint and fields."""
    session = FakeSession(
        FakeResponse(
            200,
            {
                "id": "12345",
                "verified_name": "Home",
                "display_phone_number": "+39 333 123 4567",
                "quality_rating": "GREEN",
                "account_mode": "LIVE",
                "messaging_limit_tier": "TIER_2K",
            },
        )
    )
    client = api.KapsoClient(session, "secret", "12345")

    phone = await client.async_get_phone_number()

    assert phone.id == "12345"
    assert phone.verified_name == "Home"
    assert session.requests[0]["url"].endswith("/12345")
    assert session.requests[0]["headers"]["X-API-Key"] == "secret"
    assert "messaging_limit_tier" in session.requests[0]["params"]["fields"]


@pytest.mark.asyncio
async def test_send_text_payload() -> None:
    """Free-form text uses Kapso's Meta-compatible payload."""
    session = FakeSession(
        FakeResponse(
            200,
            {
                "contacts": [{"wa_id": "393331234567"}],
                "messages": [{"id": "wamid.text"}],
            },
        )
    )
    client = api.KapsoClient(session, "secret", "12345")

    result = await client.async_send_text("393331234567", "Door open", preview_url=True)

    assert result.id == "wamid.text"
    assert session.requests[0]["json"] == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "393331234567",
        "type": "text",
        "text": {"body": "Door open", "preview_url": True},
    }


@pytest.mark.asyncio
async def test_send_template_payload() -> None:
    """Utility templates receive ordered positional body parameters."""
    session = FakeSession(FakeResponse(200, {"messages": [{"id": "wamid.template"}]}))
    client = api.KapsoClient(session, "secret", "12345")

    await client.async_send_template(
        "393331234567",
        "ha_notification",
        "en_US",
        body_parameters=["Garage door", "10 minutes"],
    )

    assert session.requests[0]["json"]["template"] == {
        "name": "ha_notification",
        "language": {"code": "en_US"},
        "components": [
            {
                "type": "body",
                "parameters": [
                    {"type": "text", "text": "Garage door"},
                    {"type": "text", "text": "10 minutes"},
                ],
            }
        ],
    }


@pytest.mark.asyncio
async def test_send_authentication_code_payload() -> None:
    """OTP templates put the code in the body and COPY_CODE button."""
    session = FakeSession(FakeResponse(200, {"messages": [{"id": "wamid.otp"}]}))
    client = api.KapsoClient(session, "secret", "12345")

    await client.async_send_authentication_code(
        "393331234567", "auth_copy_code", "en_US", "123456"
    )

    components = session.requests[0]["json"]["template"]["components"]
    assert components == [
        {
            "type": "body",
            "parameters": [{"type": "text", "text": "123456"}],
        },
        {
            "type": "button",
            "sub_type": "otp",
            "index": "0",
            "parameters": [{"type": "text", "text": "123456"}],
        },
    ]


@pytest.mark.asyncio
async def test_conflict_is_retried_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Kapso's one-message-in-flight conflict is retried once."""
    monkeypatch.setattr(api, "CONFLICT_RETRY_DELAY_SECONDS", 0)
    session = FakeSession(
        FakeResponse(409, {"error": "Another message is in-flight"}),
        FakeResponse(200, {"messages": [{"id": "wamid.retry"}]}),
    )
    client = api.KapsoClient(session, "secret", "12345")

    result = await client.async_send_text("393331234567", "Hello")

    assert result.id == "wamid.retry"
    assert len(session.requests) == 2


@pytest.mark.asyncio
async def test_authentication_error() -> None:
    """Authentication failures use a dedicated exception for HA reauth."""
    session = FakeSession(FakeResponse(401, {"error": {"message": "Bad key"}}))
    client = api.KapsoClient(session, "secret", "12345")

    with pytest.raises(api.KapsoAuthenticationError, match="Bad key"):
        await client.async_get_phone_number()
