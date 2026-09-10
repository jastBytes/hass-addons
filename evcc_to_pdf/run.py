#!/usr/bin/env python3
"""Home Assistant add-on wrapper around evcc-to-PDF.

Reads the add-on options written by the Supervisor to /data/options.json,
maps them onto the environment variables generate_pdf_report.py expects,
and runs it once a month at the configured time. The upstream script
itself only ever processes a single (by default: the previous) month and
exits, so scheduling is handled here.
"""

import calendar
import datetime
import json
import os
import subprocess
import sys
import threading
import time

OPTIONS_FILE = "/data/options.json"
APP_DIR = "/app"
SCRIPT = "generate_pdf_report.py"

REPORT_LOCK = threading.Lock()


def log(message):
    print(f"[evcc_to_pdf] {message}", flush=True)


def load_options():
    with open(OPTIONS_FILE, "r") as fp:
        return json.load(fp)


def build_env(options):
    env = os.environ.copy()

    evcc = options.get("evcc", {})
    sender = options.get("sender", {})
    email = options.get("email", {})
    report = options.get("report", {})

    env["EVCC_URL"] = evcc.get("url", "")
    env["EVCC_PASSWORD"] = evcc.get("password", "")

    env["SENDER_NAME"] = sender.get("name", "")
    env["SENDER_STREET"] = sender.get("street", "")
    env["SENDER_CITY"] = sender.get("city", "")

    if email.get("enabled"):
        env["SMTP_SERVER"] = email.get("smtp_server", "")
        env["SMTP_PORT"] = str(email.get("smtp_port", 587))
        env["SENDER_EMAIL"] = email.get("sender_email", "")
        env["SENDER_PASSWORD"] = email.get("sender_password", "")
        env["RECIPIENT_EMAIL"] = email.get("recipient_email", "")

    locale = report.get("locale") or "de_DE.UTF-8"
    env["LOCALE"] = locale
    env["LANG"] = locale
    env["LC_ALL"] = locale

    if report.get("pdf_columns"):
        env["PDF_COLUMNS"] = report["pdf_columns"]
    if report.get("filter_vehicles"):
        env["FILTER_VEHICLES"] = report["filter_vehicles"]
    if report.get("filter_loadpoints"):
        env["FILTER_LOADPOINTS"] = report["filter_loadpoints"]

    return env


def run_report(env, year=None, month=None):
    cmd = [sys.executable, SCRIPT]
    period = "the previous month (script default)"
    if year is not None and month is not None:
        cmd += ["--year", str(year), "--month", str(month)]
        period = f"{month:02d}/{year}"

    log(f"Generating charging report for {period} ...")
    result = subprocess.run(
        cmd,
        cwd=APP_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for line in result.stdout.splitlines():
        log(line)
    if result.returncode != 0:
        log(f"Report generation failed with exit code {result.returncode}")
    else:
        log("Report generation finished successfully.")


def trigger_report(env, year=None, month=None):
    # Serialize against the scheduled run and other triggers so two
    # generations never write the same output file at once.
    with REPORT_LOCK:
        run_report(env, year=year, month=month)


def stdin_listener():
    """Allow an on-demand run via the add-on's stdin, e.g. from a Home
    Assistant automation using the hassio.addon_stdin service (requires
    "stdin": true in config.json). Accepts one command per line:

      generate               -> current month, to date
      previous                -> previous month (same as the monthly schedule)
      {"year": 2026, "month": 9} -> an explicit period
    """
    while True:
        raw_line = sys.stdin.readline()
        if not raw_line:
            # EOF: stdin isn't attached right now (e.g. no client has sent
            # anything yet, or a prior hassio.addon_stdin call's connection
            # was closed). Keep polling instead of exiting the thread, since
            # the container's stdin can still receive further writes later.
            time.sleep(1)
            continue

        line = raw_line.strip()
        if not line:
            continue

        log(f"Received stdin trigger: {line!r}")
        try:
            options = load_options()
        except Exception as e:
            log(f"Could not read options for triggered run: {e}")
            continue

        year = month = None
        payload = None
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            pass

        if isinstance(payload, dict):
            year = payload.get("year")
            month = payload.get("month")
        else:
            command = line.lower()
            if command in ("generate", "current", "now"):
                today = datetime.datetime.now()
                year, month = today.year, today.month
            elif command == "previous":
                year = month = None
            else:
                log(
                    f"Unknown stdin command {line!r}; ignoring. "
                    'Send "generate", "previous", or {"year": Y, "month": M}.'
                )
                continue

        threading.Thread(
            target=trigger_report, args=(build_env(options), year, month), daemon=True
        ).start()


def next_run(day_of_month, hour, now=None):
    now = now or datetime.datetime.now()

    def candidate(year, month):
        last_day = calendar.monthrange(year, month)[1]
        day = min(day_of_month, last_day)
        return datetime.datetime(year, month, day, hour, 0, 0)

    target = candidate(now.year, now.month)
    if target <= now:
        year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
        target = candidate(year, month)
    return target


def main():
    options = load_options()
    schedule = options.get("schedule", {})
    day_of_month = int(schedule.get("day_of_month", 1))
    hour = int(schedule.get("hour", 2))
    run_on_start = bool(schedule.get("run_on_start", False))

    log(f"Scheduled to run monthly on day {day_of_month} at {hour:02d}:00 (previous month's report)")
    log(
        "On-demand trigger: send 'generate' (current month), 'previous', or "
        '{"year": Y, "month": M} to this add-on\'s stdin, e.g. via the '
        "hassio.addon_stdin service from a Home Assistant automation."
    )

    threading.Thread(target=stdin_listener, daemon=True).start()

    if run_on_start:
        trigger_report(build_env(options))

    while True:
        target = next_run(day_of_month, hour)
        delay = max((target - datetime.datetime.now()).total_seconds(), 1)
        log(f"Next scheduled report at {target.isoformat()} (in {int(delay)}s)")
        time.sleep(delay)
        trigger_report(build_env(load_options()))


if __name__ == "__main__":
    main()
