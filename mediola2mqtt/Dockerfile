FROM ghcr.io/home-assistant/amd64-base:3.14

ENV LANG=C.UTF-8

RUN apk add --no-cache python3 py3-pip \
    && pip3 install --no-cache-dir \
        paho-mqtt==2.1.0 \
        requests==2.32.5 \
        PyYAML==6.0.3

COPY mediola2mqtt.py /
COPY run.sh /
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
