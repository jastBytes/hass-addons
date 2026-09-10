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
  starts (e.g. after an update or restart). Useful to produce a report
  on-demand: enable this, save, restart the add-on, then disable it again.

## Output

Generated PDFs (`ChargingCostSummary_<year>-<month>.pdf`) are written to
`/share/evcc_to_pdf` on the host, reachable from outside the add-on via the
*Samba share* or *File editor* add-ons.

## Logs

Each report run, including any errors from evcc-to-PDF itself, is written to
the add-on log (**Log** tab).
