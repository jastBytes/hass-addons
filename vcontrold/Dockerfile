ARG BUILD_FROM=ghcr.io/hassio-addons/base:12.2.4
FROM ${BUILD_FROM}

RUN apk update && \
    apk add cmake make libxml2-dev linux-headers mosquitto-clients git jq iputils gcc musl-dev

RUN mkdir openv && cd openv && \
    git clone https://github.com/openv/vcontrold.git vcontrold-code && \
    cmake ./vcontrold-code -DVSIM=ON -DMANPAGES=OFF && \
    make && \
    make install

ADD config /etc/vcontrold/
COPY run.sh /
RUN chmod a+x /run.sh

EXPOSE 3002/udp
ENTRYPOINT ["sh","/run.sh"]
