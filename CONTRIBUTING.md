# Contributing

Thanks for considering a contribution to this add-on repository.

## Repository layout

Each top-level folder (`evcc_to_pdf/`, `mediola2mqtt/`) is a self-contained
Home Assistant add-on with its own `config.json`, `Dockerfile`, `build.yaml`
and `README.md`. There is no shared code between add-ons.

## Making a change

1. Fork the repository and create a branch off `main`.
2. Make your change inside the relevant add-on folder.
3. If the change is user-visible (new option, behavior change, bug fix),
   bump `version` in that add-on's `config.json` (semver:
   `major.minor.patch`) and add an entry to the top of its
   `CHANGELOG.md` describing it. Supervisor shows that changelog to users
   on update, so write it for them, not for other developers.
4. Update the add-on's `README.md` if you changed or added a configuration
   option.
5. Open a pull request against `main`.

## Continuous integration

Every push and pull request runs two GitHub Actions workflows:

* **Lint** ([`frenck/action-addon-linter`](https://github.com/frenck/action-addon-linter))
  checks each changed add-on's `config.json`/`build.yaml` against Home
  Assistant's add-on conventions.
* **Builder** builds the Docker image (amd64 only, matching what both
  add-ons declare) for any add-on whose `build.yaml`, `config.json`,
  `Dockerfile`, `rootfs`, or `mediola2mqtt.py` changed, as a build-only
  smoke test (`--test`, nothing is pushed) on pull requests.

Both need to pass before a pull request can be merged.

## Adding a new add-on

Use an existing add-on folder as a template. At minimum you need
`config.json`, `Dockerfile`, `build.yaml`, `README.md` and `CHANGELOG.md`.
Add a section for it to the root [README.md](./README.md) and an `icon.png`
(128x128) once you have one. `home-assistant/actions/helpers/find-addons`
(used by both workflows) discovers add-on folders automatically - no other
wiring is needed.

## Reporting issues

Please open a [GitHub issue](https://github.com/jastBytes/hass-addons/issues)
with add-on logs (**Settings → Add-ons → <add-on> → Log**) and your
configuration (with secrets like passwords redacted).
