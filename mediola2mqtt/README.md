# mediola2mqtt - a mediola MQTT gateway

This is a fork from the archived repository <https://github.com/andyboeh/mediola2mqtt>.
I would like to thank the creator of the project for their work.

This utility is a simple python script to attach a few components of the
Mediola AIO gateway to HomeAssistant or other MQTT capable hosts.

## Supported gateways

* Mediola AIO gateway v4/v4+
  
Reported to work:

* Mediola AIO gateway v6

## Supported devices

Currently, the following devices are supported/tested:

* Intertechno push buttons
* Somfy RTS Blinds
* Elero Blinds

If you want another device supported by Mediola to be controllable through
this script, create an issue on github.

## Installation

If you run Home Assistant OS (HassOS), you can run it as an addon. Simply create
a new folder "mediola2mqtt" in your local "addons" folder and copy the contents
of the repository there. All configuration is performed within the add-on configuration.

If you do not run HassOS, the configuration is done in `mediola2mqtt.yaml`.

## Usage

Configure your devices in the file mediola2mqtt.yaml / add-on configuration - have
a look at mediola2mqtt.yaml.example for the syntax. If you have MQTT autodiscovery
enabled in your HomeAssistant platform, then the devices will appear automagically.

The devices need to be known to the Gateway in advance, you need IQONTROL or
AIO Creator Neo for the initial configuration. Some steps, like configuring
Elero blinds, can also be performed by running `mediolamanager.py`.

You can retrieve a list of all
known devices by calling `http://mediola.lan/command?XC_FNC=GetStates` in a
browser. Check for `type` and `adr` fields. Please make sure to define all addresses,
especially for Elero devices, in decimal notation, not Hex! 0F becomes 15 in the
configuration file!

## Blind positions

The Mediola gateway does not report a position, neither for Somfy RTS nor for
Elero blinds. The position can nevertheless be provided to HomeAssistant by
measuring the time a blind needs to travel. Add `travel_time_up` and
`travel_time_down` (in seconds, from fully closed to fully open and back) to a
blind and it is announced to HomeAssistant as a cover with position support:

```yaml
blinds:
  - type: RT
    adr: 5a25d5
    name: Living Room
    travel_time_up: 26
    travel_time_down: 24
```

If only one of the two values is given, it is used for both directions. Without
travel times, the blind behaves exactly as before (open/close/stop only).

How it works:

* Moving to an intermediate position starts the blind and stops it again after
  the calculated time.
* Fully opening or closing runs into the end stop, which also re-synchronizes
  the calculated position - so small deviations do not accumulate.
* For Elero blinds, the status reported by the gateway is used as well: the
  position is corrected whenever an end stop is reported, and blinds moved by
  a wall transmitter or remote are tracked, too.
* If the position is not known yet (first start, or after using one of the
  Elero preset positions), a move to an intermediate position first closes the
  blind completely to get a defined reference.
* The last known positions are stored (in `/data` in add-on mode, next to the
  configuration file otherwise) and restored on startup.

Since a Somfy RTS blind can also be operated by its remote without the gateway
noticing, the calculated position may drift. Fully opening or closing the blind
resets it.

## Elero intermediate and ventilation position

Elero motors support two additional preset positions that can be exposed as
HomeAssistant buttons by setting `intermediate_position: true` and/or
`ventilation_position: true` on an Elero (`ER`) blind.

## Status polling and availability

The state of all Elero blinds is queried from the gateway once at startup, so
HomeAssistant shows the correct state after a restart instead of waiting for
the next status broadcast. Setting `general.poll_interval` to a number of
seconds repeats this query periodically, which also recovers from lost UDP
broadcasts.

The bridge publishes `online`/`offline` on `<topic>/status` (with an MQTT last
will), so the devices are shown as unavailable in HomeAssistant while the
add-on is not running.

## Multiple Mediola Gateways

The add-on supports connecting to and managing several Gateways. However,
due to limitations in the docker architecture, this is only supported when running
standalone and not in add-on mode.

If you need to enable multiple devices, you need to add an ID to each Mediola
configured and assign the same ID to the buttons and blinds for this Mediola
interface. This is necessary for sending commands to the "correct" Mediola.

## How it works

The Mediola AIO Gateway supports a simple HTTP API for control and broadcasts
status changes via UDP on port 1902 (1901 for v6). The script listens on both
ports by default (configurable via `general.port`), interprets the status
changes and publishes them via MQTT.
This is useful for buttons/switches, but can also be used for the state
of a blind (only implemented for Elero).

Controlling a blind or other device is done via HTTP, by interpreting MQTT messages
and triggering the HTTP API.

## MQTT topics

| Topic | Direction | Description |
| --- | --- | --- |
| `<topic>/status` | out | `online` / `offline` |
| `<topic>/buttons/<mediola>/<type>_<adr>` | out | button press events |
| `<topic>/blinds/<mediola>/<type>_<adr>/state` | out | `open`, `closed`, `opening`, `closing`, `stopped` |
| `<topic>/blinds/<mediola>/<type>_<adr>/position` | out | `0` (closed) to `100` (open), only with travel times |
| `<topic>/blinds/<mediola>/<type>_<adr>/set` | in | `open`, `close`, `stop` |
| `<topic>/blinds/<mediola>/<type>_<adr>/set_position` | in | `0` to `100`, only with travel times |
| `<topic>/blinds/<mediola>/<type>_<adr>/intermediate` | in | Elero intermediate position |
| `<topic>/blinds/<mediola>/<type>_<adr>/ventilation` | in | Elero ventilation position |
