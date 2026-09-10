# Changelog

## 0.4.0 - 2026-09-10

- Switch version numbering to semver (`major.minor.patch`), matching
  `evcc_to_pdf` and the rest of the ecosystem. No functional changes.

## 0.4 - 2026-09-04

### Added

- Optional blind position support (`travel_time_up`/`travel_time_down`) for
  Somfy RTS and Elero blinds, exposed as a cover with position and
  set-position control in Home Assistant.
- Intermediate and ventilation position buttons for Elero blinds
  (`intermediate_position`/`ventilation_position`).
- Startup and periodic (`general.poll_interval`) Elero state polling, so
  positions are correct after a restart instead of waiting for the next
  broadcast.
- MQTT availability reporting (`online`/`offline`) with a last-will message.
- Per-blind `device_class` and a configurable `name` for buttons.
- Listen on both 1902 (v4/v5 gateways) and 1901 (v6 gateways) by default.

### Fixed

- Support paho-mqtt 2.x, which requires an explicit callback API version.
- Send the password of the matching gateway instead of the last one
  configured.
- Parse command topics via a lookup table instead of splitting on `_`, which
  broke for topics or gateway IDs containing underscores.
- Add timeouts and error handling to gateway requests, so an unresponsive
  gateway no longer blocks the MQTT thread indefinitely.
- Cache gateway hostname resolution instead of resolving it on every packet.
- Stop forcing optimistic mode on Elero covers that report their own state.
- Use the configured button name instead of checking its type.

## 0.3 - 2024-02-04

- Initial Home Assistant add-on release, packaging the mediola2mqtt bridge
  (forked from the archived
  [andyboeh/mediola2mqtt](https://github.com/andyboeh/mediola2mqtt)).
