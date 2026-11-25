#!/usr/bin/env python3
"""Apply local fixes to upstream evcc-to-PDF's generate_pdf_report.py.

Run once at image build time. Every replacement must match exactly once, so
the build fails loudly when bumping EVCC_TO_PDF_REF changes the upstream code
instead of silently shipping an unpatched script.
"""

import sys

PATCHES = [
    (
        # evcc reports session times with their UTC offset, so a month that
        # spans a DST change mixes +02:00 and +01:00 and pd.to_datetime()
        # raises "Mixed timezones detected". Parse as UTC and show the times
        # in the Home Assistant time zone (the Supervisor sets TZ).
        "start/end times across DST changes",
        """\
        if 'start_time' in df.columns:
            df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce')
        if 'end_time' in df.columns:
            df['end_time'] = pd.to_datetime(df['end_time'], errors='coerce')
""",
        """\
        tz = os.environ.get('TZ') or 'UTC'
        if 'start_time' in df.columns:
            df['start_time'] = pd.to_datetime(df['start_time'], errors='coerce', utc=True).dt.tz_convert(tz)
        if 'end_time' in df.columns:
            df['end_time'] = pd.to_datetime(df['end_time'], errors='coerce', utc=True).dt.tz_convert(tz)
""",
    ),
    (
        # Upstream labels end - start as "Charging Duration", but that is the
        # plug-in time (e.g. 147 h for 3.7 kWh) and it also dropped whole
        # days. Use evcc's actual charging time instead, which the sessions
        # API returns as chargeDuration in nanoseconds (null if unknown).
        "duration from evcc chargeDuration",
        """\
        # Duration computed from start/end timestamps.
        if 'start_time' in df.columns and 'end_time' in df.columns:
            td = df['end_time'] - df['start_time']
            df['duration'] = td.apply(
                lambda x: f"{x.components.hours}h {x.components.minutes}m" if pd.notnull(x) else "N/A"
            )
        else:
            df['duration'] = "N/A"
""",
        """\
        # Actual charging time as reported by evcc (nanoseconds).
        if 'chargeDuration' in raw.columns:
            td = pd.to_timedelta(pd.to_numeric(raw['chargeDuration'], errors='coerce'), unit='ns')
            df['duration'] = td.apply(
                lambda x: f"{int(x.total_seconds() // 3600)}h {int(x.total_seconds() % 3600 // 60):02d}m"
                if pd.notnull(x) else "N/A"
            )
        else:
            df['duration'] = "N/A"
""",
    ),
]


def main(path):
    with open(path, encoding="utf-8") as f:
        source = f.read()
    for name, old, new in PATCHES:
        count = source.count(old)
        if count != 1:
            sys.exit(f"patch '{name}': expected 1 match in {path}, found {count}")
        source = source.replace(old, new)
        print(f"patched: {name}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(source)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "generate_pdf_report.py")
