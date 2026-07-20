# Kapso WhatsApp for Home Assistant

Send Home Assistant notifications through WhatsApp using the
[Kapso API](https://docs.kapso.ai/docs/whatsapp/send-messages/text).

Phase 1 is outbound-only and provides:

- A UI config flow for the Kapso API key and WhatsApp Business sender ID.
- Multiple recipient subentries, each represented by a native `notify` entity.
- Family, Adults, and Guests notify groups built from each contact's settings.
- Template-backed notifications for proactive Home Assistant alerts.
- Free-form text during an active WhatsApp 24-hour customer-service window.
- Actions for general templates and COPY_CODE authentication templates.
- Redacted diagnostics and one automatic retry for Kapso's temporary `409`
  message-ordering conflict.

## Requirements

- Home Assistant 2026.7 or newer.
- A Kapso project API key.
- A WhatsApp Business phone number connected to Kapso.
- For proactive notifications, an approved utility template. The recommended
  template uses the named parameters `subject` and `notification_details`.

The Kapso sandbox can send text but cannot send templates or target multiple
recipients. Use a production WhatsApp connection to test template-backed notify
entities.

## Installation with HACS

1. Open HACS and select the three-dot menu in the top-right corner.
2. Select **Custom repositories**.
3. Add `https://github.com/sebastian-greco/ha-kapso-whatsapp` with type
   **Integration**.
4. Find **Kapso WhatsApp**, select **Download**, and restart Home Assistant.
5. Go to **Settings > Devices & services > Add integration**, then select
   **Kapso WhatsApp**.

## Manual installation

Copy `custom_components/kapso_whatsapp` into the same path under your Home
Assistant configuration directory:

```text
/config/custom_components/kapso_whatsapp/
```

Restart Home Assistant, then add **Kapso WhatsApp** from
**Settings > Devices & services**.

## Versions and releases

This project uses semantic versioning. HACS installs versioned GitHub releases;
the integration version is available in
`custom_components/kapso_whatsapp/manifest.json`. See [CHANGELOG.md](CHANGELOG.md)
for release history.

## Account setup

1. In Kapso, create a project API key under **Integrations > API keys**.
2. Copy the Meta **WhatsApp Business phone number ID** for the connected sender.
   This is an ID such as `647015955153740`, not the visible telephone number.
3. In Home Assistant, go to **Settings > Devices & services > Add integration**.
4. Select **Kapso WhatsApp** and enter those two values.

The API key is stored in Home Assistant's config entry storage and is removed
from downloaded diagnostics.

## Add a recipient

Open the configured Kapso WhatsApp integration and choose
**Add WhatsApp recipient**.

- **Name** becomes the notify entity name.
- **Recipient** is a telephone number including country code.
- **Contact role** is either **Family member** or **Guest**.
- **Include in Adults group** independently adds the contact to Adults. An
  adult guest therefore belongs to both Guests and Adults.
- **Notification mode** controls what `notify.send_message` does:
  - **Approved utility template** is recommended for proactive alerts.
  - **Free-form text** works only while the recipient's 24-hour
    customer-service window is active.
- **Template parameter format** should be **Named** for the recommended
  template below. Existing recipients retain the legacy positional format
  until they are reconfigured.

### Create the recommended Kapso template

Create a WhatsApp template in Kapso with these settings:

- Name: `home_notification`
- Category: **Utility**
- Language: `en_US` (or the language configured for the recipient)
- Parameter format: **Named**
- Header type: **Text**
- Header text: `Home Assistant` (static text, with no parameter)
- Buttons: none for this first phase

Use this body exactly to start:

```text
A household status notification was generated.

Subject: {{subject}}

Details:
{{notification_details}}

This is an automated message from your Home Assistant system.
```

Suggested example values are `Electricity outage` for `subject` and
`Currently 3 grid-powered devices are offline, which may mean there is no
electricity in the house.` for `notification_details`.

The fixed wording is intentional: Meta rejects templates where variables make
up too much of the content. A header containing only `{{subject}}` plus a body
containing only `{{notification_details}}` can trigger error `2388293`.

After Meta approves it, configure the recipient with template name
`home_notification` and parameter format **Named**. To update an existing
recipient, open the Kapso integration, select the recipient, and choose
**Reconfigure**.

For backward compatibility, **Positional** format still accepts a template
with one body value:

```text
Home Assistant notification:

{{1}}
```

Meta must approve the template before it can be used.

## Native notification example

After adding a recipient, select the created entity in an automation:

```yaml
actions:
  - action: notify.send_message
    target:
      entity_id: notify.sebastian
    data:
      title: Garage warning
      message: The garage door has been open for 10 minutes.
```

New contacts use their contact name as the suggested entity ID, for example
`notify.sebastian` or `notify.lucila`. Home Assistant may retain an older ID or
add a suffix when an ID already exists, so confirm it in the entity picker.

The integration also creates these logical group entities:

| Entity | Recipients |
| --- | --- |
| `notify.family` | Contacts whose role is Family member |
| `notify.adults` | Contacts with Include in Adults group enabled |
| `notify.guests` | Contacts whose role is Guest |

Each group fans out as individual WhatsApp deliveries. It is not a WhatsApp
group chat, and each recipient consumes one message. Sending to a group with no
matching contacts is a successful no-op.

## Migrate an existing notification router

Your existing wrapper scripts can remain the public interface. In the central
router, map the current logical recipients to the new notify entities:

```yaml
sequence:
  - variables:
      whatsapp_targets:
        sebastian: notify.sebastian
        lucila: notify.lucila
        family: notify.family
        adults: notify.adults
        guests: notify.guests
      whatsapp_target: "{{ whatsapp_targets.get(person) }}"

  # Keep your existing priority formatting before this action. In the current
  # router, final_title already contains 🚨 for urgent or 💬 for low priority.
  - action: notify.send_message
    continue_on_error: true
    target:
      entity_id: "{{ whatsapp_target }}"
    data:
      title: "{{ final_title }}"
      message: "{{ message }}"
```

This preserves the existing `title` and `message` contract: the integration
maps them to `subject` and `notification_details`. Keep presence filtering in
the router. Continue sending notifications containing Companion App action
buttons to the Companion App as well; WhatsApp buttons and replies require the
future inbound-webhook phase.

## Send free-form text

Use this during an active 24-hour customer-service window:

```yaml
actions:
  - action: kapso_whatsapp.send_text
    data:
      config_entry_id: YOUR_CONFIG_ENTRY_ID
      to: "393331234567"
      message: The washing machine has finished.
      preview_url: false
```

The automation editor provides a config-entry picker, so the ID does not need
to be typed when creating the action in the UI.

## Send an approved template

For a named template, use `named_parameters`:

```yaml
actions:
  - action: kapso_whatsapp.send_template
    data:
      config_entry_id: YOUR_CONFIG_ENTRY_ID
      to: "393331234567"
      template_name: home_notification
      language: en_US
      named_parameters:
        subject: Garage warning
        notification_details: The garage door has been open for 10 minutes.
```

Positional `body_parameters` remain available for templates using `{{1}}`,
`{{2}}`, and so on:

```yaml
actions:
  - action: kapso_whatsapp.send_template
    data:
      config_entry_id: YOUR_CONFIG_ENTRY_ID
      to: "393331234567"
      template_name: appliance_finished
      language: en_US
      body_parameters:
        - Washing machine
        - "14:35"
```

## Send an authentication code

This action targets an approved `AUTHENTICATION` template using a COPY_CODE
button. Kapso requires the OTP in both the body and button parameters; the
integration constructs that payload automatically.

```yaml
actions:
  - action: kapso_whatsapp.send_authentication_code
    data:
      config_entry_id: YOUR_CONFIG_ENTRY_ID
      to: "393331234567"
      template_name: auth_copy_code
      language: en_US
      code: "123456"
```

Authentication templates have additional Meta account eligibility requirements.
See [Kapso's authentication-template documentation](https://docs.kapso.ai/docs/whatsapp/templates/authentication).

## Message accounting

Kapso's Free plan currently counts all inbound and outbound messages against its
monthly allowance. Meta may bill delivered template messages separately. The
integration does not currently track quota or determine whether a conversation
window is active.

## Current limitations

- Outbound text and templates only; media comes in a later phase.
- No incoming-message webhook or delivery/read-status events yet.
- The integration cannot query whether the recipient's 24-hour window is open.
- Notify entities support the recommended two named body parameters or the
  legacy single positional body parameter.
- General template actions support named or positional body parameters, but not
  template headers or buttons yet.
- Group entities fan out to individual contacts; they are not WhatsApp chats.

## Development

```bash
uv sync
uv run ruff check .
uv run python -m compileall -q custom_components tests
uv run pytest
```

The API client tests do not require a live Kapso account and never send messages.

## Attribution and license

The recipient-subentry and notify-entity structure is adapted from Home
Assistant Core's Telegram bot integration. Home Assistant Core and this project
are licensed under Apache License 2.0. See [NOTICE](NOTICE) and [LICENSE](LICENSE).
