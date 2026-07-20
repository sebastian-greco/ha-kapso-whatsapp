# Changelog

All notable changes are documented here. This project follows
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- An experimental HAOS app packaging WAHA 2026.7.1 with the browserless GOWS
  engine.
- An ingress-native WAHA sidebar control panel for health, QR linking, and
  session start, stop, and restart operations.
- Persistent WAHA sessions, cold-backup support, watchdog monitoring, and a
  GHCR image build workflow.

### Security

- The WAHA API port is disabled by default, media downloads are off in the
  initial notification-only phase, and sidebar controls require Home Assistant
  ingress.

## [0.2.0] - 2026-07-20

### Added

- Named template parameters for the generic template action and recipient
  notify entities.
- Family, Adults, and Guests fan-out notify entities derived from recipient
  settings.
- Family member or Guest contact roles plus an independent Adult checkbox.
- Recipient reconfiguration without deleting and re-adding the contact.
- A documented migration path for the existing household notification router.

### Changed

- New template-backed recipients default to the recommended `subject` and
  `notification_details` named parameters.
- New individual entities use the contact name as their suggested entity ID.
- Existing recipients remain on the legacy positional parameter format until
  reconfigured.

## [0.1.0] - 2026-07-19

### Added

- UI setup and reauthentication for Kapso API credentials.
- Recipient subentries with native Home Assistant notify entities.
- Proactive notifications through approved WhatsApp utility templates.
- Free-form text messages during an active 24-hour service window.
- Actions for general templates and COPY_CODE authentication templates.
- Redacted diagnostics, API error mapping, and conflict retry handling.
- HACS, Hassfest, lint, formatting, test, and release automation.

[0.2.0]: https://github.com/sebastian-greco/ha-kapso-whatsapp/releases/tag/v0.2.0
[0.1.0]: https://github.com/sebastian-greco/ha-kapso-whatsapp/releases/tag/v0.1.0
