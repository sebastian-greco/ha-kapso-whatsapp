# Migrate Home Assistant notifications to WAHA WhatsApp

This guide covers the send-only phase of WAHA WhatsApp. It keeps existing
automation call sites stable, introduces WhatsApp gradually, and preserves the
Home Assistant Companion App where WhatsApp cannot yet replace its behavior.

## Before changing automations

1. Confirm the WAHA app session reports `WORKING`.
2. Add each recipient under **Settings → Devices & services → WAHA WhatsApp**.
3. Confirm the expected notify entities exist under **Settings → Devices &
   services → Entities**. Typical IDs are:

   - `notify.waha_seba`
   - `notify.waha_lucila`

4. Send one direct test from **Developer Tools → Actions → YAML mode**:

   ```yaml
   action: notify.send_message
   target:
     entity_id: notify.waha_seba
   data:
     title: "WhatsApp test"
     message: "Home Assistant can send through WAHA."
   ```

Home Assistant keeps entity IDs in its entity registry. If an entity was
renamed previously or its preferred ID was already occupied, use the ID shown
by the entity picker instead of assuming the examples above.

## What maps cleanly

The native `notify.send_message` action accepts the two fields used by most
notification wrappers:

| Existing field | WAHA behavior |
| --- | --- |
| `title` | Rendered as a bold WhatsApp heading. |
| `message` | Rendered below the title as ordinary text. |
| logical recipient | Mapped to an individual contact notify entity. |

The integration does not infer recipient sets from Home Assistant People or
store roles, notification preferences, or memberships on Person entities.
Route to explicit individual targets in your central notification script.
Associated contacts expose `person_entity_id` on their individual notify
entity. The phone number is not exposed.

## What does not map yet

The outbound-only phase does not implement:

- notification buttons or replies;
- Companion App tags, replacement, clearing, persistence, or sticky behavior;
- Android notification channels, TTL, importance, or iOS interruption levels;
- delivery acknowledgement, retries, or automatic fallback;
- inbound commands or identity verification.

Keep the Companion App notification whenever `data.actions` is present. Keep
Alarmo and other safety-critical notifications on the Companion App as a
tested fallback even if they are also copied to WhatsApp. A mobile
`clear_notification` command is an app operation and must not be converted to
WhatsApp text.

## Recommended migration: preserve the central router

Do not replace every automation individually when existing automations already
call recipient wrapper scripts. Add WhatsApp behind the central notification
router so its callers continue to pass the same `person`, `title`, `message`,
`priority`, and `data` fields.

Add a target map and WAHA action after the router has constructed its final
title. The following block assumes the router already defines `person`,
`final_title`, and `message`:

```yaml
- variables:
    whatsapp_targets:
      sebastian: notify.waha_seba
      lucila: notify.waha_lucila
    whatsapp_target: "{{ whatsapp_targets.get(person) }}"

- if:
    - condition: template
      value_template: "{{ whatsapp_target is string }}"
  then:
    - action: notify.send_message
      continue_on_error: true
      target:
        entity_id: "{{ whatsapp_target }}"
      data:
        title: "{{ final_title }}"
        message: "{{ message }}"
```

`continue_on_error: true` prevents a temporary WAHA or WhatsApp failure from
stopping the remainder of a routine. It does not retry the message.

### Discover a contact from its Person association

To avoid maintaining a name-to-notify-entity map, a router that already
receives a Person entity ID can discover the associated individual WAHA notify
entity:

```yaml
- variables:
    whatsapp_target: >-
      {{ states.notify
         | selectattr('attributes.person_entity_id', 'eq', person_entity_id)
         | map(attribute='entity_id')
         | first
         | default(none) }}

- if:
    - condition: template
      value_template: "{{ whatsapp_target is string }}"
  then:
    - action: notify.send_message
      continue_on_error: true
      target:
        entity_id: "{{ whatsapp_target }}"
      data:
        title: "{{ final_title }}"
        message: "{{ message }}"
```

For a known notify entity, the same metadata is available directly through
`state_attr('notify.waha_seba', 'person_entity_id')`. The attribute is absent
when a contact has no Person association, so routers must handle no match.

Keep logical priority in the router even though WhatsApp has no equivalent to
mobile notification channels. The router can continue expressing urgency in
`final_title`, for example by adding `🚨` for urgent messages and `💬` for low
priority messages.

## Rollout phases

### 1. Test only

Send manually to each configured individual contact and confirm the expected
person receives it.

### 2. Dual delivery

Keep the existing Companion App action and add the WAHA action after it in the
central router. Run both channels for ordinary messages while checking message
formatting, recipient routing, and WAHA availability.

### 3. WhatsApp-first informational messages

After a stable trial, remove Companion App delivery only for ordinary
informational messages. Retain the existing wrapper script interfaces so the
choice can be reversed without editing every automation.

### 4. Keep actionable and critical fallback

Continue dual delivery for actionable, Alarmo, security, access, power outage,
and other safety-sensitive workflows. WhatsApp should not become their only
control or alert path until authenticated inbound actions, stale-action
protection, and fallback behavior have been implemented and tested.

## Troubleshooting

### A recipient exists but its notify entity does not

Version `1.0.1` and newer reload automatically after recipient changes. On
`1.0.0`, use the integration's three-dot menu and select **Reload**, then update
through HACS. If the problem remains on a newer version, inspect
**Settings → System → Logs** for `waha_whatsapp` errors.

### Sending fails

Verify that the WAHA session is `WORKING`, the HAOS app is running, and the
integration is loaded. Keep port 3000 private; the companion integration uses
Home Assistant's internal app network and does not require public exposure.

### The entity ID differs from this guide

Use the entity picker as the source of truth. Home Assistant preserves user
renames and may add a numeric suffix to avoid a collision. Changing an entity
ID later requires updating every automation, script, scene, and dashboard that
references it.

## Upgrading from household groups

Version `1.1.0` removes the former Family, Adults, and Guests configuration and
fan-out entities. During config-entry migration, the integration:

- preserves every recipient subentry, phone number, contact title, optional
  Person association, and individual notify entity;
- removes only the obsolete role/adult flags from integration-owned config
  data; and
- removes only the three integration-owned legacy group entities from the
  entity registry.

Update automations that referenced the removed group entities to target
individual contacts explicitly. A future generic “broadcast to all configured
contacts” would be a separate opt-in feature, not a household role or group.
