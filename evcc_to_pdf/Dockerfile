ARG BUILD_FROM
FROM $BUILD_FROM

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

RUN pip install --no-cache-dir -r requirements.txt

# The script writes PDFs to ./output relative to its working directory;
# point that at the Home Assistant "share" folder so reports are reachable
# from outside the add-on (e.g. via Samba or the File editor add-on).
RUN mkdir -p /share/evcc_to_pdf \
    && rm -rf /app/output \
    && ln -s /share/evcc_to_pdf /app/output

COPY run.py /run.py
COPY run.sh /run.sh
RUN chmod a+x /run.sh /run.py

CMD [ "/run.sh" ]
