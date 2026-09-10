# EVCC to PDF add-on

This add-on wraps [evcc-to-PDF](https://github.com/MaizeShark/evcc-to-PDF) to
generate a monthly PDF charging cost report from an [evcc](https://evcc.io)
instance and, optionally, email it.

evcc-to-PDF itself only ever processes a single month and exits - there is no
built-in scheduling. This add-on runs it once a month at the configured time
and keeps the container alive in between runs.

## Installation

Add <https://github.com/jastBytes/hass-addons> as an add-on repository to Home
Assistant (**Settings → Add-ons → Add-on store**, three-dot menu →
**Repositories**), then install *EVCC to PDF* from the store. The
[repository README](../README.md) describes the steps in detail.

## Configuration

```yaml
evcc:
  url: http://homeassistant.local:7070
  password: ""
sender:
  name: John Doe
  street: Sample Street 123
  city: 12345 Sample City
email:
  enabled: false
  smtp_server: ""
  smtp_port: 587
  sender_email: ""
  sender_password: ""
  recipient_email: ""
report:
  locale: de_DE.UTF-8
  pdf_columns: start_time,end_time,loadpoint,vehicle,energy,duration,price
  filter_vehicles: ""
  filter_loadpoints: ""
schedule:
  day_of_month: 1
  hour: 2
  run_on_start: false
```

### `evcc`

* `url` - Base URL of your evcc instance, e.g. `http://homeassistant.local:7070`.
* `password` - evcc UI password, if one is configured. Leave empty otherwise.

### `sender`

Name and address printed on the report as the sender/biller.

### `email`

Set `enabled: true` and fill in the SMTP settings to have the finished PDF
emailed to `recipient_email` after each run. When disabled, the PDF is only
written to disk.

### `report`

* `locale` - Controls both the report language/template (`de_DE.UTF-8` or any
  `en_*` locale) and number/date formatting. Falls back to `en_US.UTF-8` if
  the requested locale isn't available.
* `pdf_columns` - Comma-separated list of columns to include, e.g.
  `start_time,end_time,loadpoint,vehicle,energy,duration,price`.
* `filter_vehicles` / `filter_loadpoints` - Comma-separated allow-lists by
  name. Leave empty to include everything.

### `schedule`

* `day_of_month` (1-28) and `hour` (0-23) - When the report for the previous
  month is generated. Defaults to the 1st at 02:00, matching the cron example
  from the upstream project.
* `run_on_start` - Also generate a report immediately whenever the add-on
  starts (e.g. after an update or restart).

## Triggering a report on demand (e.g. on the last workday of the month)

The add-on's own `schedule` only understands a fixed day-of-month, and always
reports the *previous* month - it has no idea about weekends or holidays. If
you want the report to run on, say, the last workday of the month (which
Home Assistant can determine via the
[`workday`](https://www.home-assistant.io/integrations/workday/) integration),
drive it from a Home Assistant automation instead.

The add-on listens on its own stdin for trigger commands (this requires the
add-on's *Start on boot*/*Watchdog* page to show the "Terminal"-adjacent
**stdin** capability is enabled, which it is by default for this add-on).
Send one of the following as the `input` of the `hassio.addon_stdin` service:

| Input | Effect |
| --- | --- |
| `generate` | Report for the **current** month, up to today |
| `previous` | Report for the previous month (same as the monthly schedule) |
| `{"year": 2026, "month": 9}` | An explicit period |

Example automation, triggered on the last workday of the month at 18:00:

```yaml
automation:
  - alias: "evcc report on last workday of month"
    trigger:
      - platform: time
        at: "18:00:00"
    condition:
      # today is the last day of the month...
      - condition: template
        value_template: "{{ (now() + timedelta(days=1)).month != now().month }}"
      # ...and it's a workday (requires the workday integration, configured
      # with your country/holidays)
      - condition: state
        entity_id: binary_sensor.workday_sensor
        state: "on"
    action:
      - service: hassio.addon_stdin
        data:
          addon: evcc_to_pdf
          input: generate
```

If today isn't a workday (weekend or holiday), nothing fires and the
automation simply checks again the next day - so the report ends up being
generated on whichever day actually turns out to be the last workday. Find
the exact `addon:` value for your instance via the service call picker in
**Developer tools → Actions** (search for *Add-on: Send data to stdin*) and
selecting *EVCC to PDF* from its add-on dropdown - it may include a
repository-specific prefix in the entity/slug shown there.

## Output

Generated PDFs (`ChargingCostSummary_<year>-<month>.pdf`) are written to
`/share/evcc_to_pdf` on the host, reachable from outside the add-on via the
*Samba share* or *File editor* add-ons.

## Logs

Each report run, including any errors from evcc-to-PDF itself, is written to
the add-on log (**Log** tab).

## Changelog

See [CHANGELOG.md](./CHANGELOG.md) for release notes.
