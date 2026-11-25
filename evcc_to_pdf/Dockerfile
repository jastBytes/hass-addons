FROM docker.io/library/python:3.11-slim-bookworm

ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        locales \
        fonts-dejavu-core \
        libpango-1.0-0 \
        libharfbuzz0b \
        libpangoft2-1.0-0 \
    && sed -i -E 's/^# (de_DE\.UTF-8|en_US\.UTF-8|en_GB\.UTF-8|fr_FR\.UTF-8|es_ES\.UTF-8|it_IT\.UTF-8|nl_NL\.UTF-8) UTF-8/\1 UTF-8/' /etc/locale.gen \
    && locale-gen \
    && rm -rf /var/lib/apt/lists/*

# evcc-to-PDF has no tagged releases, so pin to a known-good commit instead of
# floating on main. Bump this when picking up upstream changes.
ARG EVCC_TO_PDF_REF=a061812324407dcb08e7155b6446d3e6dd539ac4

WORKDIR /app
RUN git clone https://github.com/MaizeShark/evcc-to-PDF.git . \
    && git checkout "${EVCC_TO_PDF_REF}" \
    && rm -rf .git

# evcc reports session times with their UTC offset, so a month spanning a
# DST change mixes +02:00 and +01:00 and pd.to_datetime() raises "Mixed
# timezones detected". Parse as UTC and convert to the Home Assistant time
# zone (the Supervisor sets TZ). The grep fails the build if the patch no
# longer applies after bumping EVCC_TO_PDF_REF.
RUN sed -i -E "s/pd\.to_datetime\(df\['(start|end)_time'\], errors='coerce'\)/pd.to_datetime(df['\1_time'], errors='coerce', utc=True).dt.tz_convert(os.environ.get('TZ') or 'UTC')/" generate_pdf_report.py \
    && test "$(grep -c "utc=True).dt.tz_convert(os.environ.get('TZ') or 'UTC')" generate_pdf_report.py)" -eq 2

# Upstream formats the session duration from Timedelta.components.hours, which
# drops whole days, so a car plugged in for 36 h showed as "12h 0m". Add the
# days back in as hours.
RUN sed -i 's/{x\.components\.hours}h/{x.components.days * 24 + x.components.hours}h/' generate_pdf_report.py \
    && grep -q 'x.components.days \* 24 + x.components.hours' generate_pdf_report.py

RUN pip install --no-cache-dir -r requirements.txt

# The script writes PDFs to ./output relative to its working directory;
# point that at the Home Assistant "share" folder so reports are reachable
# from outside the add-on (e.g. via Samba or the File editor add-on).
# Note: the Supervisor bind-mounts the real /share over this path at
# container start, so /share/evcc_to_pdf itself must be (re-)created at
# runtime (see run.sh), not here at build time.
RUN rm -rf /app/output \
    && ln -s /share/evcc_to_pdf /app/output

COPY run.py /run.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh /run.py

CMD [ "/run.sh" ]
