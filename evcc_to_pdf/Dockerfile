# Two stages: everything only needed to assemble the app (git, the locales
# package, pip, test suites, unused font weights) stays in the build stage,
# the final image only gets the resulting files. Both stages use the same
# base image so the copied site-packages match the interpreter.
#
# Alpine would be smaller but does not work here: musl ignores LC_NUMERIC
# and has no localized month names, so German reports would show "1234.50"
# and "October" instead of "1234,50" and "Oktober".

# ---------------------------------------------------------------- build
FROM docker.io/library/python:3.11-slim-bookworm AS build

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        locales \
        fonts-inter \
    && rm -rf /var/lib/apt/lists/*

# Compile just the supported locales into /usr/lib/locale/locale-archive,
# which glibc reads at runtime without the locales package.
RUN sed -i -E 's/^# (de_DE\.UTF-8|en_US\.UTF-8|en_GB\.UTF-8|fr_FR\.UTF-8|es_ES\.UTF-8|it_IT\.UTF-8|nl_NL\.UTF-8) UTF-8/\1 UTF-8/' /etc/locale.gen \
    && locale-gen

# Only the Inter weights the report template uses (400/500/600/700).
RUN mkdir /fonts && cd /usr/share/fonts/opentype/inter \
    && cp Inter-Regular.otf Inter-Medium.otf Inter-SemiBold.otf Inter-Bold.otf /fonts/

# evcc-to-PDF has no tagged releases, so pin to a known-good commit instead of
# floating on main. Bump this when picking up upstream changes.
ARG EVCC_TO_PDF_REF=a061812324407dcb08e7155b6446d3e6dd539ac4

WORKDIR /app
RUN git clone https://github.com/MaizeShark/evcc-to-PDF.git . \
    && git checkout "${EVCC_TO_PDF_REF}" \
    && rm -rf .git tests test_*.py docker-compose.yml Dockerfile setup_cron.sh

# Local fixes to the upstream script (DST time zones, real charging time);
# the build fails if a patch no longer matches after bumping the ref.
COPY patch_upstream.py /tmp/patch_upstream.py
RUN python3 /tmp/patch_upstream.py generate_pdf_report.py

# Runtime dependencies only (upstream's requirements also list pytest).
# Bundled test suites and bytecode caches are dropped; Python recreates the
# caches on first run.
RUN grep -viE '^pytest' requirements.txt > /tmp/requirements.txt \
    && pip install --no-cache-dir --no-compile -r /tmp/requirements.txt \
    && cd /usr/local/lib/python3.11/site-packages \
    && find . -type d \( -name tests -o -name __pycache__ \) -prune -exec rm -rf {} +

# Own report layout (shared by both languages) replacing upstream's templates.
COPY templates/ /app/

# ---------------------------------------------------------------- runtime
FROM docker.io/library/python:3.11-slim-bookworm

ENV LANG=C.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
        fonts-dejavu-core \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /usr/lib/locale/locale-archive /usr/lib/locale/locale-archive
COPY --from=build /fonts/ /usr/share/fonts/opentype/inter/
COPY --from=build /usr/local/lib/python3.11/site-packages/ /usr/local/lib/python3.11/site-packages/
COPY --from=build /app/ /app/

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

WORKDIR /app
CMD [ "/run.sh" ]
