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
import time

OPTIONS_FILE = "/data/options.json"
APP_DIR = "/app"
SCRIPT = "generate_pdf_report.py"


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


def run_report(env):
    log("Generating charging report ...")
    result = subprocess.run(
        [sys.executable, SCRIPT],
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

    log(f"Scheduled to run monthly on day {day_of_month} at {hour:02d}:00")

    if run_on_start:
        run_report(build_env(options))

    while True:
        target = next_run(day_of_month, hour)
        delay = max((target - datetime.datetime.now()).total_seconds(), 1)
        log(f"Next report scheduled for {target.isoformat()} (in {int(delay)}s)")
        time.sleep(delay)
        run_report(build_env(load_options()))


if __name__ == "__main__":
    main()
