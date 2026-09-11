# Changelog

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
