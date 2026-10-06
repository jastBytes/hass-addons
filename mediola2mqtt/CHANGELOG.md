# Changelog

## 0.5.2 - 2026-10-06

### Fixed

- UDP broadcasts from other devices on the gateway ports (e.g. SDDP
  announcements of Samsung TVs on port 1902) no longer flood the log and the
  MQTT topic in debug mode. They are ignored, and each sender is logged only
  once.
- The MQTT library's log is limited to warnings and errors, instead of a
  line for every single MQTT packet in debug mode. MQTT warnings and errors
  are now also logged without debug mode.

## 0.5.1 - 2026-10-03

### Changed

- If several commands for the same blind are waiting for a busy gateway,
  only the latest one is sent, e.g. a quick "open" followed by "close" no
  longer moves the blind up first. Stop commands are always sent.
- Blind positions are only written to disk when they actually changed, and
  at most every 5 seconds, instead of on every status report of the gateway.
  This reduces wear on SD cards when `poll_interval` is used.
- Received MQTT messages and subscriptions are only logged with
  `mqtt.debug` enabled.
- More accurate intermediate positions: the travel time is now measured
  from when a command is sent to the gateway instead of from its response,
  and the stop is sent right when the target is reached instead of on the
  next 200 ms tick. With a gateway taking 400 ms per command, a blind sent
  to 50% previously stopped at about 44%.
- If the stop for an intermediate position is delayed because the gateway
  is busy, the reported position now reflects where the blind actually
  stopped instead of the requested one.

### Fixed

- The add-on now receives the stop signal of the Supervisor, so it shuts
  down right away and stores the latest positions before exiting.

## 0.5.0 - 2026-10-01

### Changed

- Commands for many blinds at once (scenes, groups, automations) are
  forwarded to the gateway noticeably faster. Gateway requests no longer
  block MQTT message processing: each gateway now has its own command queue
  that sends commands back to back, reusing one HTTP connection instead of
  opening a new one for every command. The gateway still sends the radio
  telegrams one after another, so blinds keep starting slightly staggered.
- Automatic stop commands for intermediate positions are sent ahead of other
  queued commands, so blinds stop as close as possible to the requested
  position.

### Added

- With `mqtt.debug` enabled, the log shows how long the gateway took for
  each request and how long a command waited in the queue, which helps to
  tell gateway delays apart from add-on delays.

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
