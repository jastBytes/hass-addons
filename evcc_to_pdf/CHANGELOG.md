# Changelog

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
