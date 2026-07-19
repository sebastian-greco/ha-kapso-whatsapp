"""Constants for the Kapso WhatsApp integration."""

from typing import Final

DOMAIN: Final = "kapso_whatsapp"

DEFAULT_API_BASE_URL: Final = "https://api.kapso.ai/meta/whatsapp/v24.0"
DEFAULT_TEMPLATE_LANGUAGE: Final = "en_US"

CONF_PHONE_NUMBER_ID: Final = "phone_number_id"
CONF_RECIPIENT: Final = "recipient"
CONF_NOTIFICATION_MODE: Final = "notification_mode"
CONF_TEMPLATE_NAME: Final = "template_name"
CONF_TEMPLATE_LANGUAGE: Final = "template_language"

NOTIFICATION_MODE_TEXT: Final = "text"
NOTIFICATION_MODE_TEMPLATE: Final = "template"
NOTIFICATION_MODES: Final = (NOTIFICATION_MODE_TEXT, NOTIFICATION_MODE_TEMPLATE)

SUBENTRY_TYPE_RECIPIENT: Final = "recipient"

ATTR_TO: Final = "to"
ATTR_TEMPLATE_NAME: Final = "template_name"
ATTR_LANGUAGE: Final = "language"
ATTR_BODY_PARAMETERS: Final = "body_parameters"
ATTR_CODE: Final = "code"
ATTR_PREVIEW_URL: Final = "preview_url"

SERVICE_SEND_TEXT: Final = "send_text"
SERVICE_SEND_TEMPLATE: Final = "send_template"
SERVICE_SEND_AUTHENTICATION_CODE: Final = "send_authentication_code"
