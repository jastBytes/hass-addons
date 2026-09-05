# jastBytes Home Assistant add-on repository

Home Assistant add-ons maintained by jastBytes.

[![Open your Home Assistant instance and show the add add-on repository dialog with a specific repository URL pre-filled.](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https%3A%2F%2Fgithub.com%2FjastBytes%2Fhass-addons)

## Installation

The add-ons in this repository are installed by adding the repository to your
Home Assistant instance:

1. Use the button above, or add the repository by hand:
   1. Open **Settings → Add-ons → Add-on store** in Home Assistant.
   2. Open the three-dot menu in the top right corner and select **Repositories**.
   3. Paste `https://github.com/jastBytes/hass-addons`, select **Add** and close
      the dialog.
2. Reload the add-on store. The add-ons below now show up in a section named
   after this repository.
3. Select the add-on you want and choose **Install**. The first installation
   builds the container image and takes a few minutes.
4. Open the **Configuration** tab, enter your settings and select **Save**.
5. Return to the **Info** tab and select **Start**. **Watch the logs** on the
   **Log** tab to verify that everything connects.

Installing add-ons requires a Home Assistant installation that includes the
Supervisor (Home Assistant OS or Home Assistant Supervised). Home Assistant
Container and Home Assistant Core cannot install add-ons - see the
[mediola2mqtt README](./mediola2mqtt/README.md) for running it standalone.

The add-ons are built for `amd64` only and are therefore not offered on other
architectures.

## Add-ons

### [mediola2mqtt add-on](./mediola2mqtt)

![Supports amd64 Architecture][amd64-shield]

Connects a Mediola AIO Gateway to Home Assistant via MQTT. It exposes Somfy RTS
and Elero blinds as covers - including position control - and Intertechno push
buttons as device triggers.

An MQTT broker is required. If you do not run one yet, install the official
*Mosquitto broker* add-on and set up the MQTT integration before starting this
add-on.

Configuration options are documented in the
[add-on README](./mediola2mqtt/README.md).

[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
