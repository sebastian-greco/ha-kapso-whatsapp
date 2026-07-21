# Changelog

All notable changes are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.1] - 2026-07-21

### Fixed

- Reload the integration automatically after recipients are added, updated, or
  removed so individual entities and household group membership stay current.
- Use the stable shared device name `WAHA` so new entity IDs are generated as
  `notify.waha_<recipient>` and `notify.waha_<group>` instead of including the
  account name and WAHA version.
- Avoid duplicate config-entry reloads on Home Assistant 2026.6 and newer by
  routing entry changes through one update listener.

### Documentation

- Correct the notify entity examples and add a staged Companion App-to-WhatsApp
  migration guide, including actionable-notification and fallback guidance.

## [1.0.0] - 2026-07-21

### Added

- A WAHA-native HACS integration for free-form outbound WhatsApp messages.
- Automatic Supervisor discovery between the HAOS app and HACS integration.
- Recipient subentries that select existing Home Assistant Person entities and
  associate them with WhatsApp phone numbers.
- Native individual, Family, Adults, and Guests notify entities.
- A direct `waha_whatsapp.send_message` action for arbitrary phone numbers.
- Redacted diagnostics and manual support for externally hosted WAHA servers.

### Changed

- Replaced the Kapso Cloud API and template system with the self-hosted WAHA
  API and linked-device session.
- Renamed the integration domain from `kapso_whatsapp` to `waha_whatsapp`.
- Renamed and refocused the repository as Home Assistant WhatsApp.

### Removed

- Kapso credentials, approved templates, authentication templates, and the
  24-hour free-form messaging restriction.

### Migration

- This is an intentional breaking provider migration. Remove the Kapso
  integration before installing WAHA WhatsApp and re-add recipient mappings.
- The complete Kapso v0.2 state remains on the `legacy-kapso` branch and the
  original `v0.1.0` and `v0.2.0` tags remain unchanged.

[1.0.0]: https://github.com/sebastian-greco/home-assistant-whatsapp/releases/tag/v1.0.0
[1.0.1]: https://github.com/sebastian-greco/home-assistant-whatsapp/releases/tag/v1.0.1
