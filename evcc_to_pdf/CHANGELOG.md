# Changelog

## 1.2.0 - 2026-11-25

- New PDF layout: masthead with period and sender, key figures (charging
  sessions, energy, cost), a cleaner table with a single total row at the
  end, local date format, and a footer with page numbers on every page.
  Uses the Inter font. An empty month now says so instead of showing an
  empty table.
- The "Charging Duration" column now shows evcc's actual charging time
  (`chargeDuration`) instead of the time the car was plugged in, which could
  be days for a few kWh. Sessions without a charging time show `N/A`.
  Minutes are zero-padded (`2h 03m`).
- Install `libharfbuzz-subset0` so WeasyPrint uses HarfBuzz for font
  subsetting and no longer logs a warning about it.
- Move the local fixes to the upstream script into `patch_upstream.py`.

## 1.1.2 - 2026-11-25

- Fix `ValueError: Mixed timezones detected` for months that span a
  daylight saving time change (e.g. October 2026). Session times are now
  parsed as UTC and shown in the Home Assistant time zone.
- Fix session durations over 24 hours in the report. Whole days were
  dropped, so 36 hours showed as `12h 0m`.

## 1.1.1 - 2026-09-11

- Fix `FileExistsError: [Errno 17] File exists: './output'` on every report
  run. The Supervisor bind-mounts the real `/share` folder over the
  container's `/share` at start, which hid the `/share/evcc_to_pdf`
  directory created during the image build, leaving the `/app/output`
  symlink dangling. The directory is now (re-)created at container
  startup instead.

## 1.1.0 - 2026-09-10

- Add on-demand report generation via the add-on's stdin: send `generate`
  (current month), `previous`, or an explicit `{"year": ..., "month": ...}`
  through the `hassio.addon_stdin` service to trigger a report from a Home
  Assistant automation, e.g. on the last workday of the month.

## 1.0.0 - 2026-09-10

- Initial release. Wraps
  [evcc-to-PDF](https://github.com/MaizeShark/evcc-to-PDF) (pinned to a
  known-good commit) to generate a monthly PDF charging cost report from an
  evcc instance, with optional email delivery. Reports are written to
  `/share/evcc_to_pdf`.
- Fix a build failure on Supervisor caused by an unqualified `build_from`
  image reference, which made Supervisor silently fall back to the wrong
  base image.
